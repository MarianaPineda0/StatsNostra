from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_partido_service
from app.schemas.partido import (
    PartidoActualizar,
    PartidoCrear,
    PartidoFinalizar,
    PartidoRespuesta,
)
from app.services.partido import PartidoService

# CRUD de Partido, mas el endpoint /finalizar que cierra el partido y
# dispara el calculo de puntos de todas sus predicciones (regla 7)
router = APIRouter(prefix="/partidos", tags=["partidos"])


@router.post("", response_model=PartidoRespuesta, status_code=status.HTTP_201_CREATED)
def crear_partido(
    datos: PartidoCrear, service: PartidoService = Depends(get_partido_service)
) -> PartidoRespuesta:
    return service.crear(datos)


@router.get("", response_model=list[PartidoRespuesta])
def listar_partidos(
    service: PartidoService = Depends(get_partido_service),
) -> list[PartidoRespuesta]:
    return service.listar()


@router.get("/{partido_id}", response_model=PartidoRespuesta)
def obtener_partido(
    partido_id: int, service: PartidoService = Depends(get_partido_service)
) -> PartidoRespuesta:
    return service.obtener(partido_id)


@router.put("/{partido_id}", response_model=PartidoRespuesta)
def actualizar_partido(
    partido_id: int,
    datos: PartidoActualizar,
    service: PartidoService = Depends(get_partido_service),
) -> PartidoRespuesta:
    return service.actualizar(partido_id, datos)


@router.delete("/{partido_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_partido(
    partido_id: int, service: PartidoService = Depends(get_partido_service)
) -> None:
    service.eliminar(partido_id)


@router.post("/{partido_id}/finalizar", response_model=PartidoRespuesta)
def finalizar_partido(
    partido_id: int,
    datos: PartidoFinalizar,
    service: PartidoService = Depends(get_partido_service),
) -> PartidoRespuesta:
    return service.finalizar(partido_id, datos)
