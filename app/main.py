from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import apostadores, consultas, partidos, predicciones
from app.core.config import get_settings
from app.core.exceptions import ConflictoDeDatos, RecursoNoEncontrado, ReglaDeNegocioViolada
from app.core.middleware import MetodoOverrideMiddleware

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(MetodoOverrideMiddleware)

app.include_router(apostadores.router)
app.include_router(partidos.router)
app.include_router(predicciones.router)
app.include_router(consultas.router)


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
