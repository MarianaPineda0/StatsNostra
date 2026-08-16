class MetodoOverrideMiddleware:
    # Cloudflare (borde de Render) bloquea metodos HTTP no estandar como QUERY.
    # Permite simularlo via POST + header de override, solo en rutas /query,
    # sin modificar el registro real del verbo QUERY en los endpoints.
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
                scope = dict(scope)
                scope["method"] = "QUERY"

        await self.app(scope, receive, send)
