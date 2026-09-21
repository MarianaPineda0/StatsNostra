from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracion de la app, leida de variables de entorno (o .env local).

    Los valores por defecto de abajo son solo para desarrollo local con
    Docker Compose; en Render se sobreescriben con las variables de entorno
    reales de cada servicio (ver docs/render.md).
    """

    app_name: str = "StatsNostra"
    app_version: str = "0.1.0"

    # Identifica el ambiente activo para logs y comportamiento condicional
    entorno: str = "desarrollo"
    database_url: str = (
        "postgresql+psycopg://statsnostra_pruebas:pruebas_local@localhost:5432/statsnostra_pruebas"
    )
    log_level: str = "INFO"

    # URLs de las APIs de los compañeros de grupo (Entrega 2, api/v2),
    # identificadas por el nombre de su API, no de su autor. Vacias por
    # defecto: si no estan configuradas, el cliente externo simplemente no
    # llama a esa nube en vez de fallar.
    trading_journal_api_url: str = ""
    ecommerce_api_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    # Evita releer el entorno en cada solicitud
    return Settings()
