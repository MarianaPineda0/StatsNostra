import uuid

from app.core.trace import TRACE_ID_HEADER, trace_id_var


class TraceIdMiddleware:
    """Propaga un identificador de correlacion (trace-id) por peticion.

    Si la peticion ya trae el header (por ejemplo, del orquestador del
    equipo), se reutiliza. Si no, se genera un UUID nuevo, para que esta
    API siga funcionando de forma individual como exige la rubrica. El
    valor queda disponible durante toda la peticion via `trace_id_var`
    (app/core/trace.py) y se devuelve tambien en la respuesta.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        entrante = headers.get(TRACE_ID_HEADER.lower().encode(), b"").decode()
        trace_id = entrante or str(uuid.uuid4())
        token = trace_id_var.set(trace_id)

        async def send_con_trace_id(message):
            if message["type"] == "http.response.start":
                message["headers"].append((TRACE_ID_HEADER.encode(), trace_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_con_trace_id)
        finally:
            trace_id_var.reset(token)


class MetodoOverrideMiddleware:
    """Permite invocar el verbo QUERY via POST cuando la red lo bloquea.

    Cloudflare (el borde de Render) rechaza cualquier metodo HTTP fuera del
    conjunto estandar (verificado con evidencia real: ver docs/pruebas.md),
    asi que una peticion QUERY genuina nunca llega a esta app cuando pasa
    por Render. Como workaround estandar, este middleware detecta un POST
    con el header `X-HTTP-Method-Override: QUERY` en rutas /query/* y
    reescribe el metodo ANTES de que Starlette haga el enrutamiento — el
    endpoint sigue registrado unicamente como QUERY (app/api/routes/consultas.py),
    esto no le agrega una ruta POST paralela ni afloja ninguna validacion.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if (
            scope["type"] == "http"
            and scope["method"] == "POST"
            and scope["path"].startswith("/query")
        ):
            headers = dict(scope["headers"])
            override = headers.get(b"x-http-method-override", b"").decode().upper()
            if override == "QUERY":
                # Se copia el scope (no se muta el original) para no alterar
                # lo que ASGI/Starlette pueda seguir usando aguas arriba
                scope = dict(scope)
                scope["method"] = "QUERY"

        await self.app(scope, receive, send)
