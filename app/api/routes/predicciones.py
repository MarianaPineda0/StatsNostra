from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_prediccion_service
from app.schemas.prediccion import PrediccionActualizar, PrediccionCrear, PrediccionRespuesta
from app.services.prediccion import PrediccionService

# CRUD de Prediccion. Las 5 reglas de negocio (apostador activo, partido no
# finalizado, sin duplicados, etc.) viven en PrediccionService, no aqui.
router = APIRouter(prefix="/predicciones", tags=["predicciones"])


@router.post("", response_model=PrediccionRespuesta, status_code=status.HTTP_201_CREATED)
def crear_prediccion(
    datos: PrediccionCrear, service: PrediccionService = Depends(get_prediccion_service)
) -> PrediccionRespuesta:
    return service.crear(datos)


@router.get("", response_model=list[PrediccionRespuesta])
def listar_predicciones(
    service: PrediccionService = Depends(get_prediccion_service),
) -> list[PrediccionRespuesta]:
    return service.listar()


@router.get("/{prediccion_id}", response_model=PrediccionRespuesta)
def obtener_prediccion(
    prediccion_id: int, service: PrediccionService = Depends(get_prediccion_service)
) -> PrediccionRespuesta:
    return service.obtener(prediccion_id)


@router.put("/{prediccion_id}", response_model=PrediccionRespuesta)
def actualizar_prediccion(
    prediccion_id: int,
    datos: PrediccionActualizar,
    service: PrediccionService = Depends(get_prediccion_service),
) -> PrediccionRespuesta:
    return service.actualizar(prediccion_id, datos)


@router.delete("/{prediccion_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_prediccion(
    prediccion_id: int, service: PrediccionService = Depends(get_prediccion_service)
) -> None:
    service.eliminar(prediccion_id)
