from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_apostador_service, get_apostador_v2_service
from app.schemas.apostador import ApostadorActualizar, ApostadorCrear, ApostadorRespuesta
from app.schemas.apostador_v2 import ApostadorV2Respuesta
from app.services.apostador import ApostadorService
from app.services.apostador_v2 import ApostadorV2Service

# Entrega 2: misma API v1 de Apostador, replicada bajo /api/v2 (misma
# logica, delegando al mismo ApostadorService, sin duplicarla). El unico
# endpoint distinto es el GetById, que ademas agrega en tiempo real datos
# de las APIs externas del equipo (trading-journal, ecommerce). Ni el
# listado ni el resto del CRUD agregan nada externo.
router = APIRouter(prefix="/api/v2/apostadores", tags=["apostadores-v2"])


@router.post("", response_model=ApostadorRespuesta, status_code=status.HTTP_201_CREATED)
def crear_apostador_v2(
    datos: ApostadorCrear, service: ApostadorService = Depends(get_apostador_service)
) -> ApostadorRespuesta:
    return service.crear(datos)


@router.get("", response_model=list[ApostadorRespuesta])
def listar_apostadores_v2(
    service: ApostadorService = Depends(get_apostador_service),
) -> list[ApostadorRespuesta]:
    return service.listar()


@router.get("/{apostador_id}", response_model=ApostadorV2Respuesta)
def obtener_apostador_agregado(
    apostador_id: int, service: ApostadorV2Service = Depends(get_apostador_v2_service)
) -> ApostadorV2Respuesta:
    return service.obtener_agregado(apostador_id)


@router.put("/{apostador_id}", response_model=ApostadorRespuesta)
@router.patch("/{apostador_id}", response_model=ApostadorRespuesta)
def actualizar_apostador_v2(
    apostador_id: int,
    datos: ApostadorActualizar,
    service: ApostadorService = Depends(get_apostador_service),
) -> ApostadorRespuesta:
    return service.actualizar(apostador_id, datos)


@router.delete("/{apostador_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_apostador_v2(
    apostador_id: int, service: ApostadorService = Depends(get_apostador_service)
) -> None:
    service.eliminar(apostador_id)
