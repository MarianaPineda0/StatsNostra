from app.core.config import get_settings
from app.integrations.cliente_externo import obtener_primero
from app.schemas.prediccion_v2 import PrediccionV2Respuesta
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

        trading_journal_url = self._settings.trading_journal_api_url
        ecommerce_url = self._settings.ecommerce_api_url

        return PrediccionV2Respuesta(
            prediccion=prediccion,
            trading_journal_trade=obtener_primero(trading_journal_url, "/api/v1/trades"),
            trading_journal_strategy=obtener_primero(
                trading_journal_url, "/api/v1/strategies"
            ),
            ecommerce_cliente=obtener_primero(ecommerce_url, "/api/v1/clients"),
            ecommerce_comercio=obtener_primero(ecommerce_url, "/api/v1/commerces"),
        )
