import logging

import httpx

logger = logging.getLogger(__name__)


def obtener_primero(url_base: str, ruta: str) -> dict | None:
    """Llama en tiempo real a una API externa y devuelve el primer elemento
    de la lista que responda.

    Nunca lanza excepcion hacia arriba: si la URL no esta configurada, esa
    nube esta caida, tarda demasiado o responde algo invalido, devuelve
    None. Asi la caida de una nube externa no tumba esta API.
    """
    if not url_base:
        return None

    try:
        respuesta = httpx.get(f"{url_base}{ruta}", timeout=5.0)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Fallo al consultar %s%s: %s", url_base, ruta, exc)
        return None

    if isinstance(datos, list):
        return datos[0] if datos else None
    return datos
