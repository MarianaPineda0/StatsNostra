from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import apostadores, consultas, partidos, predicciones
from app.core.config import get_settings
from app.core.exceptions import ConflictoDeDatos, RecursoNoEncontrado, ReglaDeNegocioViolada

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.include_router(apostadores.router)
app.include_router(partidos.router)
app.include_router(predicciones.router)
app.include_router(consultas.router)


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


# Endpoint temporal para verificar que Render deja pasar el metodo QUERY.
# Se elimina una vez confirmado el resultado.
@app.api_route("/diagnostico-query", methods=["QUERY"], tags=["diagnostico"])
def diagnostico_query() -> dict[str, str]:
    return {"metodo": "QUERY", "resultado": "ok"}
