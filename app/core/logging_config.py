import json
import logging
from datetime import UTC, datetime

from app.core.trace import trace_id_var


class FormateadorJSON(logging.Formatter):
    """Cada linea sale como JSON con el trace-id actual, para que Cloud
    Logging la parsee sola y se pueda filtrar por jsonPayload.trace_id.

    El mismo id sale tambien como `traceId` y se agrega `api`, que es el
    formato acordado con el grupo para cruzar los logs de las tres nubes. Se
    conserva `trace_id` porque los filtros y la documentacion de la v2 lo usan.
    """

    def __init__(self, api: str = "") -> None:
        super().__init__()
        self.api = api

    def format(self, record: logging.LogRecord) -> str:
        trace_id = trace_id_var.get() or None
        linea = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": trace_id,
            "traceId": trace_id,
            "api": self.api,
        }
        # Campos propios de un evento (logger.info(..., extra={"datos": {...}})),
        # al nivel raiz para poder consultarlos sin parsear el mensaje
        linea.update(getattr(record, "datos", None) or {})
        return json.dumps(linea)


def configurar_logging(nivel: str, api: str = "") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(FormateadorJSON(api))

    raiz = logging.getLogger()
    raiz.handlers = [handler]
    raiz.setLevel(nivel)

    # uvicorn maneja sus propios loggers (access/error) por fuera del root;
    # sin esto, las peticiones HTTP saldrian sin trace-id.
    for nombre in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(nombre)
        logger.handlers = [handler]
        logger.propagate = False
