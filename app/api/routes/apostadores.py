from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_apostador_service
from app.schemas.apostador import ApostadorActualizar, ApostadorCrear, ApostadorRespuesta
from app.services.apostador import ApostadorService

# CRUD de Apostador. Cada endpoint solo valida el request y delega en el
# servicio (app/services/apostador.py) — no hay logica de negocio aqui.
router = APIRouter(prefix="/apostadores", tags=["apostadores"])


@router.post("", response_model=ApostadorRespuesta, status_code=status.HTTP_201_CREATED)
def crear_apostador(
    datos: ApostadorCrear, service: ApostadorService = Depends(get_apostador_service)
) -> ApostadorRespuesta:
    return service.crear(datos)


@router.get("", response_model=list[ApostadorRespuesta])
def listar_apostadores(
    service: ApostadorService = Depends(get_apostador_service),
) -> list[ApostadorRespuesta]:
    return service.listar()


@router.get("/{apostador_id}", response_model=ApostadorRespuesta)
def obtener_apostador(
    apostador_id: int, service: ApostadorService = Depends(get_apostador_service)
) -> ApostadorRespuesta:
    return service.obtener(apostador_id)


@router.put("/{apostador_id}", response_model=ApostadorRespuesta)
def actualizar_apostador(
    apostador_id: int,
    datos: ApostadorActualizar,
    service: ApostadorService = Depends(get_apostador_service),
) -> ApostadorRespuesta:
    return service.actualizar(apostador_id, datos)


@router.delete("/{apostador_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_apostador(
    apostador_id: int, service: ApostadorService = Depends(get_apostador_service)
) -> None:
    service.eliminar(apostador_id)
