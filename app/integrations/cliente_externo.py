import logging

import httpx

from app.core.trace import TRACE_ID_HEADER, trace_id_var

logger = logging.getLogger(__name__)


def obtener_primero(url_base: str, ruta: str) -> dict | None:
    """Llama en tiempo real a una API externa y devuelve el primer elemento
    de la lista que responda, propagando el trace-id de la peticion actual.

    Nunca lanza excepcion hacia arriba: si la URL no esta configurada, esa
    nube esta caida, tarda demasiado o responde algo invalido, devuelve
    None. Asi la caida de una nube externa no tumba esta API.
    """
    if not url_base:
        return None

    headers = {}
    trace_id = trace_id_var.get()
    if trace_id:
        headers[TRACE_ID_HEADER] = trace_id

    try:
        respuesta = httpx.get(f"{url_base}{ruta}", headers=headers, timeout=5.0)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Fallo al consultar %s%s: %s", url_base, ruta, exc)
        return None

    if isinstance(datos, list):
        return datos[0] if datos else None
    return datos
