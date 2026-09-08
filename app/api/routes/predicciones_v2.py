from fastapi import APIRouter, Depends

from app.api.dependencies import get_prediccion_v2_service
from app.schemas.prediccion_v2 import PrediccionV2Respuesta
from app.services.prediccion_v2 import PrediccionV2Service

# Entrega 2: version agregada de Prediccion que incorpora, en tiempo real,
# datos de las APIs externas del equipo (trading-journal, ecommerce). No
# reemplaza ni modifica las rutas v1 de predicciones.py.
router = APIRouter(prefix="/api/v2/predicciones", tags=["predicciones-v2"])


@router.get("/{prediccion_id}", response_model=PrediccionV2Respuesta)
def obtener_prediccion_agregada(
    prediccion_id: int, service: PrediccionV2Service = Depends(get_prediccion_v2_service)
) -> PrediccionV2Respuesta:
    return service.obtener_agregada(prediccion_id)
