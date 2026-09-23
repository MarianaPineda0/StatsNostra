import json

from app.core.config import Settings
from app.core.metrics import cache_aciertos, cache_fallos
from app.integrations.cache import guardar_en_cache, obtener_del_cache
from app.integrations.cliente_externo import obtener_aleatorio


def _con_cache(settings: Settings, clave: str, url_base: str, ruta: str) -> dict | None:
    en_cache = obtener_del_cache(settings, clave)
    if en_cache is not None:
        cache_aciertos.inc()
        return json.loads(en_cache)

    cache_fallos.inc()
    dato = obtener_aleatorio(url_base, ruta)
    if dato is not None:
        guardar_en_cache(settings, clave, json.dumps(dato))
    return dato


def obtener_datos_externos(settings: Settings) -> dict:
    """Trae las 2 entidades fijas acordadas con el equipo: Trade
    (trading-journal) y Comercio (ecommerce). Pasa primero por Redis
    (cache.py, TTL de 30s); si no esta o expiro, llama a la API externa
    (GET RANDOM) y guarda el resultado. Reutilizado por los 3 servicios v2
    (apostador, partido, prediccion) para no repetir estas llamadas."""
    return {
        "trading_journal_trade": _con_cache(
            settings,
            "trading_journal:trade",
            settings.trading_journal_api_url,
            "/api/v1/trades",
        ),
        "ecommerce_comercio": _con_cache(
            settings, "ecommerce:comercio", settings.ecommerce_api_url, "/api/v1/commerce"
        ),
    }
