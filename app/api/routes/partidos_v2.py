from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_partido_service, get_partido_v2_service
from app.schemas.partido import (
    PartidoActualizar,
    PartidoCrear,
    PartidoFinalizar,
    PartidoRespuesta,
)
from app.schemas.partido_v2 import PartidoV2Respuesta
from app.services.partido import PartidoService
from app.services.partido_v2 import PartidoV2Service

# Entrega 2: misma API v1 de Partido, replicada bajo /api/v2 (misma logica,
# delegando al mismo PartidoService, sin duplicarla). El unico endpoint
# distinto es el GetById, que ademas agrega en tiempo real datos de las
# APIs externas del equipo (trading-journal, ecommerce). Ni el listado ni
# el resto del CRUD agregan nada externo.
router = APIRouter(prefix="/api/v2/partidos", tags=["partidos-v2"])


@router.post("", response_model=PartidoRespuesta, status_code=status.HTTP_201_CREATED)
def crear_partido_v2(
    datos: PartidoCrear, service: PartidoService = Depends(get_partido_service)
) -> PartidoRespuesta:
    return service.crear(datos)


@router.get("", response_model=list[PartidoRespuesta])
def listar_partidos_v2(
    service: PartidoService = Depends(get_partido_service),
) -> list[PartidoRespuesta]:
    return service.listar()


@router.get("/{partido_id}", response_model=PartidoV2Respuesta)
def obtener_partido_agregado(
    partido_id: int, service: PartidoV2Service = Depends(get_partido_v2_service)
) -> PartidoV2Respuesta:
    return service.obtener_agregado(partido_id)


@router.put("/{partido_id}", response_model=PartidoRespuesta)
@router.patch("/{partido_id}", response_model=PartidoRespuesta)
def actualizar_partido_v2(
    partido_id: int,
    datos: PartidoActualizar,
    service: PartidoService = Depends(get_partido_service),
) -> PartidoRespuesta:
    return service.actualizar(partido_id, datos)


@router.delete("/{partido_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_partido_v2(
    partido_id: int, service: PartidoService = Depends(get_partido_service)
) -> None:
    service.eliminar(partido_id)


@router.post("/{partido_id}/finalizar", response_model=PartidoRespuesta)
def finalizar_partido_v2(
    partido_id: int,
    datos: PartidoFinalizar,
    service: PartidoService = Depends(get_partido_service),
) -> PartidoRespuesta:
    return service.finalizar(partido_id, datos)
