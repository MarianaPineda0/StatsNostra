from app.core.config import get_settings
from app.schemas.prediccion_v2 import PrediccionV2Respuesta
from app.services.integraciones_externas import obtener_datos_externos
from app.services.prediccion import PrediccionService


class PrediccionV2Service:
    """Junta la prediccion propia con datos en tiempo real de las APIs
    externas del equipo (Entrega 2). No duplica logica de negocio: la
    prediccion misma se resuelve reutilizando PrediccionService (v1)."""

    def __init__(self, prediccion_service: PrediccionService) -> None:
        self._prediccion_service = prediccion_service
        self._settings = get_settings()

    def obtener_agregada(self, prediccion_id: int) -> PrediccionV2Respuesta:
        prediccion = self._prediccion_service.obtener(prediccion_id)
        return PrediccionV2Respuesta(
            prediccion=prediccion, **obtener_datos_externos(self._settings)
        )
