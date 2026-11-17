import asyncio
import logging
import random

from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

FAULT_HEADER = "X-Fault"
# Tope de la latencia pedida: evita que una cabecera mal escrita deje una
# peticion colgada minutos
LATENCIA_MAXIMA_MS = 5000


def interpretar(valor: str) -> tuple[float, int]:
    """Lee la cabecera `X-Fault`: "error=0.3;latency=250" -> (0.3, 250).

    error es la fraccion de peticiones que fallan con 500 (0 a 1) y latency
    los milisegundos que se demora la respuesta. Lo que no se entiende se
    ignora, para que un valor raro no tumbe el servicio por su cuenta.
    """
    tasa, latencia = 0.0, 0
    for parte in valor.split(";"):
        nombre, _, numero = parte.partition("=")
        try:
            numero = float(numero)
        except ValueError:
            continue
        if nombre.strip() == "error":
            tasa = min(max(numero, 0.0), 1.0)
        elif nombre.strip() == "latency":
            latencia = int(min(max(numero, 0), LATENCIA_MAXIMA_MS))
    return tasa, latencia


class InyeccionFallosMiddleware:
    """Simula una regresion en el canary: errores 500 o latencia a pedido.

    Solo se registra cuando FAULT_INJECTION=true (ver app/main.py) y esa
    variable solo se pone en la revision canary. La version estable no trae
    este codigo, y /health y /metrics quedan fuera para no confundir las
    revisiones de salud de la plataforma con una falla real.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return

        valor = dict(scope["headers"]).get(FAULT_HEADER.lower().encode(), b"").decode()
        if valor:
            tasa, latencia = interpretar(valor)
            if latencia:
                await asyncio.sleep(latencia / 1000)
            if tasa and random.random() < tasa:
                logger.warning(
                    "fallo inyectado",
                    extra={"datos": {"evento": "fallo_inyectado", "ruta": scope["path"]}},
                )
                respuesta = JSONResponse(
                    status_code=500, content={"detail": "Fallo inyectado"}
                )
                await respuesta(scope, receive, send)
                return

        await self.app(scope, receive, send)
