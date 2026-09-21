from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_prediccion_service, get_prediccion_v2_service
from app.schemas.prediccion import PrediccionActualizar, PrediccionCrear, PrediccionRespuesta
from app.schemas.prediccion_v2 import PrediccionV2Respuesta
from app.services.prediccion import PrediccionService
from app.services.prediccion_v2 import PrediccionV2Service

# Entrega 2: misma API v1 de Prediccion, replicada bajo /api/v2 (misma
# logica, delegando al mismo PrediccionService, sin duplicarla). El unico
# endpoint distinto es el GetById, que ademas agrega en tiempo real datos
# de las APIs externas del equipo (trading-journal, ecommerce). Ni el
# listado ni el resto del CRUD agregan nada externo.
router = APIRouter(prefix="/api/v2/predicciones", tags=["predicciones-v2"])


@router.post("", response_model=PrediccionRespuesta, status_code=status.HTTP_201_CREATED)
def crear_prediccion_v2(
    datos: PrediccionCrear, service: PrediccionService = Depends(get_prediccion_service)
) -> PrediccionRespuesta:
    return service.crear(datos)


@router.get("", response_model=list[PrediccionRespuesta])
def listar_predicciones_v2(
    service: PrediccionService = Depends(get_prediccion_service),
) -> list[PrediccionRespuesta]:
    return service.listar()


@router.get("/{prediccion_id}", response_model=PrediccionV2Respuesta)
def obtener_prediccion_agregada(
    prediccion_id: int, service: PrediccionV2Service = Depends(get_prediccion_v2_service)
) -> PrediccionV2Respuesta:
    return service.obtener_agregada(prediccion_id)


@router.put("/{prediccion_id}", response_model=PrediccionRespuesta)
@router.patch("/{prediccion_id}", response_model=PrediccionRespuesta)
def actualizar_prediccion_v2(
    prediccion_id: int,
    datos: PrediccionActualizar,
    service: PrediccionService = Depends(get_prediccion_service),
) -> PrediccionRespuesta:
    return service.actualizar(prediccion_id, datos)


@router.delete("/{prediccion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_prediccion_v2(
    prediccion_id: int, service: PrediccionService = Depends(get_prediccion_service)
) -> None:
    service.eliminar(prediccion_id)
