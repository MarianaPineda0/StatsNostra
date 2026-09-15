from app.core.config import Settings
from app.integrations.cliente_externo import obtener_primero


def obtener_datos_externos(settings: Settings) -> dict:
    """Trae en tiempo real las 2 entidades fijas acordadas con el equipo:
    Trade (trading-journal) y Comercio (ecommerce). Reutilizado por los 3
    servicios v2 (apostador, partido, prediccion) para no repetir estas
    llamadas."""
    return {
        "trading_journal_trade": obtener_primero(
            settings.trading_journal_api_url, "/api/v1/trades"
        ),
        "ecommerce_comercio": obtener_primero(settings.ecommerce_api_url, "/api/v1/commerces"),
    }
