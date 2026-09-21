import logging

import redis

from app.core.config import Settings

logger = logging.getLogger(__name__)

TTL_SEGUNDOS = 30

_cliente: redis.Redis | None = None
_cliente_host: str | None = None


def _obtener_cliente(settings: Settings) -> redis.Redis | None:
    global _cliente, _cliente_host
    if not settings.redis_host:
        return None
    if _cliente is None or _cliente_host != settings.redis_host:
        _cliente = redis.Redis(
            host=settings.redis_host, port=settings.redis_port, decode_responses=True
        )
        _cliente_host = settings.redis_host
    return _cliente


def obtener_del_cache(settings: Settings, clave: str) -> str | None:
    cliente = _obtener_cliente(settings)
    if cliente is None:
        return None
    try:
        return cliente.get(clave)
    except redis.RedisError as exc:
        logger.warning("Redis no disponible al leer %s: %s", clave, exc)
        return None


def guardar_en_cache(settings: Settings, clave: str, valor: str) -> None:
    cliente = _obtener_cliente(settings)
    if cliente is None:
        return
    try:
        cliente.set(clave, valor, ex=TTL_SEGUNDOS)
    except redis.RedisError as exc:
        logger.warning("Redis no disponible al guardar %s: %s", clave, exc)
