from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import (
    apostadores,
    apostadores_v2,
    cache,
    consultas,
    fallos,
    partidos,
    partidos_v2,
    predicciones,
    predicciones_v2,
)
from app.core.config import get_settings
from app.core.exceptions import ConflictoDeDatos, RecursoNoEncontrado, ReglaDeNegocioViolada
from app.core.fallos import InyeccionFallosMiddleware
from app.core.logging_config import configurar_logging
from app.core.middleware import (
    IdentificacionMiddleware,
    MetodoOverrideMiddleware,
    RegistroPeticionMiddleware,
    TraceIdMiddleware,
)
from app.core.saturacion import monitor
from app.core.tracing import configurar_tracing

settings = get_settings()
configurar_logging(settings.log_level, settings.app_id)


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    # El medidor corre siempre (despierta 10 veces por segundo, casi no cuesta)
    # para tener la métrica de retraso aunque la readiness todavía no la use
    monitor.iniciar()
    yield
    await monitor.detener()


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=ciclo_de_vida)
configurar_tracing(
    app,
    settings.grafana_otlp_endpoint,
    settings.grafana_otlp_user,
    settings.grafana_otlp_token,
    settings.otel_service_name,
)

app.add_middleware(MetodoOverrideMiddleware)
# El interruptor va por dentro del registro, para que los 500 inyectados
# tambien queden en el log, y solo existe si esta habilitado
if settings.fault_header_enabled:
    app.add_middleware(
        InyeccionFallosMiddleware,
        tasa_error=settings.fault_error_rate,
        latencia_ms=settings.fault_latency_ms,
    )
app.add_middleware(RegistroPeticionMiddleware, api=settings.app_id)
app.add_middleware(
    IdentificacionMiddleware, nombre=settings.app_id, version=settings.app_version
)
# Se agrega despues para quedar como la capa mas externa: el trace-id debe
# quedar fijado antes que cualquier otro middleware o ruta se ejecute.
app.add_middleware(TraceIdMiddleware)

app.include_router(apostadores.router)
app.include_router(partidos.router)
app.include_router(predicciones.router)
app.include_router(consultas.router)

# Alias /api/v1 de las mismas rutas de arriba (mismo router, sin logica
# duplicada) para cumplir la convencion de versionado acordada con el
# grupo, sin romper las rutas sin prefijo ya existentes.
app.include_router(apostadores.router, prefix="/api/v1")
app.include_router(partidos.router, prefix="/api/v1")
app.include_router(predicciones.router, prefix="/api/v1")
app.include_router(consultas.router, prefix="/api/v1")

app.include_router(apostadores_v2.router)
app.include_router(partidos_v2.router)
app.include_router(predicciones_v2.router)
app.include_router(cache.router)

# El endpoint de consumo de CPU solo existe con el interruptor de fallos
# encendido: apagado, la ruta responde 404 como si no estuviera en el código
if settings.fault_header_enabled:
    app.include_router(fallos.router)

# Metricas RED (tasa de peticiones, errores, latencia p50/p95) por ruta,
# expuestas en /metrics para Prometheus/Grafana.
Instrumentator().instrument(app).expose(app)


# Traduce las excepciones de dominio (levantadas en los servicios) a
# codigos HTTP. Asi los servicios no dependen de FastAPI ni conocen codigos
# HTTP — solo lanzan una excepcion con significado de negocio.
@app.exception_handler(RecursoNoEncontrado)
def manejar_no_encontrado(request: Request, exc: RecursoNoEncontrado) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictoDeDatos)
def manejar_conflicto(request: Request, exc: ConflictoDeDatos) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ReglaDeNegocioViolada)
def manejar_regla_negocio(request: Request, exc: ReglaDeNegocioViolada) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


# Sondas de Kubernetes en rutas distintas: liveness decide si se reinicia el
# contenedor y readiness si recibe trafico. Hoy responden igual (el proceso
# esta vivo y atiende); tenerlas separadas permite endurecer solo la de
# readiness, por ejemplo sacar del balanceo a un pod saturado, sin arriesgar
# reinicios innecesarios.
@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def readiness(response: Response) -> dict[str, str | float]:
    # Con umbral configurado, un pod saturado deja de ser "ready": sale del
    # balanceo y la otra réplica absorbe el tráfico mientras se recupera.
    # liveness no hace esta comprobación, para no reiniciar un pod que solo
    # está ocupado.
    lag = monitor.lag_ms
    if settings.readiness_lag_ms and lag > settings.readiness_lag_ms:
        response.status_code = 503
        return {"status": "saturado", "lag_ms": round(lag, 1)}
    return {"status": "ok"}
