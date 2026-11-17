from pydantic import Field

from app.schemas.prediccion import PrediccionActualizar, PrediccionCrear, PrediccionRespuesta

# Que tan segura esta la persona de su pronostico, de 1 (poco) a 5 (mucho).
# Es opcional: quien no la manda sigue funcionando igual que en v1 y v2.
CONFIANZA = Field(default=None, ge=1, le=5, description="Nivel de confianza, de 1 a 5")


class PrediccionV4Crear(PrediccionCrear):
    confianza: int | None = CONFIANZA


class PrediccionV4Actualizar(PrediccionActualizar):
    confianza: int | None = CONFIANZA


class PrediccionV4Respuesta(PrediccionRespuesta):
    confianza: int | None
