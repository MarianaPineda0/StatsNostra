import logging
import random

import httpx

from app.core.trace import TRACE_ID_HEADER, trace_id_var

logger = logging.getLogger(__name__)


def obtener_aleatorio(url_base: str, ruta: str) -> dict | None:
    """GET RANDOM: quien llama no elige un id, se devuelve un registro al
    azar de la lista. Propaga el trace-id actual. Si la URL no esta
    configurada, la nube esta caida o responde mal, devuelve None en vez
    de tumbar esta API.
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
        return random.choice(datos) if datos else None
    return datos
