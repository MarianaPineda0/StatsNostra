from app.core.config import Settings
from app.integrations.cliente_externo import obtener_primero


def obtener_datos_externos(settings: Settings) -> dict:
    """Trae en tiempo real las 4 entidades de las APIs externas del equipo
    (trading-journal y ecommerce). Reutilizado por los 3 servicios v2
    (apostador, partido, prediccion) para no repetir estas llamadas."""
    trading_journal_url = settings.trading_journal_api_url
    ecommerce_url = settings.ecommerce_api_url

    return {
        "trading_journal_trade": obtener_primero(trading_journal_url, "/api/v1/trades"),
        "trading_journal_strategy": obtener_primero(trading_journal_url, "/api/v1/strategies"),
        "ecommerce_cliente": obtener_primero(ecommerce_url, "/api/v1/clients"),
        "ecommerce_comercio": obtener_primero(ecommerce_url, "/api/v1/commerces"),
    }
