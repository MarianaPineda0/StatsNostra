from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_prediccion_service
from app.schemas.prediccion_v4 import (
    PrediccionV4Actualizar,
    PrediccionV4Crear,
    PrediccionV4Respuesta,
)
from app.services.prediccion import PrediccionService

# Entrega 4 (canary): lo nuevo de la v4 es el nivel de confianza de cada
# prediccion. Las reglas de negocio siguen en PrediccionService, las mismas
# de v1 y v2, para que la version nueva no se comporte distinto en lo demas.
router = APIRouter(prefix="/api/v4/predicciones", tags=["predicciones-v4"])


@router.post("", response_model=PrediccionV4Respuesta, status_code=status.HTTP_201_CREATED)
def crear_prediccion_v4(
    datos: PrediccionV4Crear, service: PrediccionService = Depends(get_prediccion_service)
) -> PrediccionV4Respuesta:
    return service.crear(datos, confianza=datos.confianza)


@router.get("", response_model=list[PrediccionV4Respuesta])
def listar_predicciones_v4(
    service: PrediccionService = Depends(get_prediccion_service),
) -> list[PrediccionV4Respuesta]:
    return service.listar()


@router.get("/{prediccion_id}", response_model=PrediccionV4Respuesta)
def obtener_prediccion_v4(
    prediccion_id: int, service: PrediccionService = Depends(get_prediccion_service)
) -> PrediccionV4Respuesta:
    return service.obtener(prediccion_id)


@router.put("/{prediccion_id}", response_model=PrediccionV4Respuesta)
@router.patch("/{prediccion_id}", response_model=PrediccionV4Respuesta)
def actualizar_prediccion_v4(
    prediccion_id: int,
    datos: PrediccionV4Actualizar,
    service: PrediccionService = Depends(get_prediccion_service),
) -> PrediccionV4Respuesta:
    return service.actualizar(prediccion_id, datos, confianza=datos.confianza)
