from fastapi import APIRouter, Depends

from app.api.dependencies import get_apostador_v2_service
from app.schemas.apostador_v2 import ApostadorV2Respuesta
from app.services.apostador_v2 import ApostadorV2Service

# Entrega 2: version agregada de Apostador que incorpora, en tiempo real,
# datos de las APIs externas del equipo (trading-journal, ecommerce). No
# reemplaza ni modifica las rutas v1 de apostadores.py.
router = APIRouter(prefix="/api/v2/apostadores", tags=["apostadores-v2"])


@router.get("/{apostador_id}", response_model=ApostadorV2Respuesta)
def obtener_apostador_agregado(
    apostador_id: int, service: ApostadorV2Service = Depends(get_apostador_v2_service)
) -> ApostadorV2Respuesta:
    return service.obtener_agregado(apostador_id)
