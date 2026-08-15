from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "StatsNostra"
    app_version: str = "0.1.0"

    # Identifica el ambiente activo para logs y comportamiento condicional
    entorno: str = "desarrollo"
    database_url: str = (
        "postgresql+psycopg://statsnostra_pruebas:pruebas_local@localhost:5432/statsnostra_pruebas"
    )
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    # Evita releer el entorno en cada solicitud
    return Settings()
