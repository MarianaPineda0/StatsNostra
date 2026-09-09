from fastapi import APIRouter, Depends

from app.api.dependencies import get_partido_v2_service
from app.schemas.partido_v2 import PartidoV2Respuesta
from app.services.partido_v2 import PartidoV2Service

# Entrega 2: version agregada de Partido que incorpora, en tiempo real,
# datos de las APIs externas del equipo (trading-journal, ecommerce). No
# reemplaza ni modifica las rutas v1 de partidos.py.
router = APIRouter(prefix="/api/v2/partidos", tags=["partidos-v2"])


@router.get("/{partido_id}", response_model=PartidoV2Respuesta)
def obtener_partido_agregado(
    partido_id: int, service: PartidoV2Service = Depends(get_partido_v2_service)
) -> PartidoV2Respuesta:
    return service.obtener_agregado(partido_id)
