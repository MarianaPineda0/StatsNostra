from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import (
    apostadores,
    apostadores_v2,
    cache,
    consultas,
    partidos,
    partidos_v2,
    predicciones,
    predicciones_v2,
)
from app.core.config import get_settings
from app.core.exceptions import ConflictoDeDatos, RecursoNoEncontrado, ReglaDeNegocioViolada
from app.core.logging_config import configurar_logging
from app.core.middleware import MetodoOverrideMiddleware, TraceIdMiddleware, VersionMiddleware
from app.core.tracing import configurar_tracing

settings = get_settings()
configurar_logging(settings.log_level)

app = FastAPI(title=settings.app_name, version=settings.app_version)
configurar_tracing(
    app,
    settings.grafana_otlp_endpoint,
    settings.grafana_otlp_user,
    settings.grafana_otlp_token,
    settings.otel_service_name,
)

app.add_middleware(MetodoOverrideMiddleware)
# Se agrega despues para quedar como la capa mas externa: el trace-id debe
# quedar fijado antes que cualquier otro middleware o ruta se ejecute.
app.add_middleware(TraceIdMiddleware)
# Va por fuera de todo para que ni un error del propio middleware de arriba
# deje una respuesta sin version ni track
app.add_middleware(VersionMiddleware, version=settings.app_version, track=settings.track)

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
    return {"status": "ok", "version": settings.app_version, "track": settings.track}
