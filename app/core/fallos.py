import asyncio
import logging
import random

from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

FAULT_HEADER = "X-Inject-Fault"
# Rutas que nunca reciben fallos: si el interruptor las afectara, Kubernetes
# reiniciaria o sacaria del balanceo al pod por culpa del experimento y no del
# sistema, y el resultado dejaria de medir el flujo real
RUTAS_EXENTAS = ("/health", "/metrics")


def fallos_pedidos(valor: str) -> set[str]:
    """Lee la cabecera `X-Inject-Fault`: "error", "latency" o "error,latency"."""
    partes = valor.replace(";", ",").split(",")
    return {parte.strip().lower() for parte in partes if parte.strip()}


class InyeccionFallosMiddleware:
    """Interruptor de fallos del grupo: errores 500 o latencia a pedido.

    Solo se registra con FAULT_HEADER_ENABLED=true (ver app/main.py). Con la
    cabecera `error` responde 500 en la fraccion FAULT_ERROR_RATE de las
    peticiones; con `latency` espera FAULT_LATENCY_MS antes de contestar.
    Apagarlo es poner la variable en false o dejar de mandar la cabecera.
    """

    def __init__(self, app, tasa_error: float = 1.0, latencia_ms: int = 0) -> None:
        self.app = app
        self.tasa_error = min(max(tasa_error, 0.0), 1.0)
        self.latencia_ms = max(latencia_ms, 0)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope["path"].startswith(RUTAS_EXENTAS):
            await self.app(scope, receive, send)
            return

        valor = dict(scope["headers"]).get(FAULT_HEADER.lower().encode(), b"").decode()
        pedidos = fallos_pedidos(valor)
        if "latency" in pedidos and self.latencia_ms:
            await asyncio.sleep(self.latencia_ms / 1000)
        if "error" in pedidos and random.random() < self.tasa_error:
            logger.warning(
                "fallo inyectado",
                extra={"datos": {"evento": "fallo_inyectado", "ruta": scope["path"]}},
            )
            respuesta = JSONResponse(status_code=500, content={"detail": "Fallo inyectado"})
            await respuesta(scope, receive, send)
            return

        await self.app(scope, receive, send)
