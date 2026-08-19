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
