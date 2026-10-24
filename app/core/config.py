from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracion de la app, leida de variables de entorno (o .env local).

    Los valores por defecto de abajo son solo para desarrollo local con
    Docker Compose; en Render se sobreescriben con las variables de entorno
    reales de cada servicio (ver docs/render.md).
    """

    app_name: str = "StatsNostra"
    # En el despliegue canary se sobreescribe con APP_VERSION (la version
    # del tag que se construyo) y TRACK, para saber que revision responde
    app_version: str = "0.1.0"
    track: Literal["stable", "canary"] = "stable"
    # Habilita la cabecera X-Fault para simular fallas. Solo se enciende en
    # la revision canary, nunca en la estable ni en produccion real
    fault_injection: bool = False

    # Identifica el ambiente activo para logs y comportamiento condicional
    entorno: str = "desarrollo"
    database_url: str = (
        "postgresql+psycopg://statsnostra_pruebas:pruebas_local@localhost:5432/statsnostra_pruebas"
    )
    log_level: str = "INFO"

    # URLs de las APIs externas del equipo, identificadas por el nombre
    # de su API, no de su autor. Vacias por defecto: si no estan
    # configuradas, el cliente externo simplemente no llama a esa nube en
    # vez de fallar.
    trading_journal_api_url: str = ""
    ecommerce_api_url: str = ""

    # Memorystore (Redis) para cachear las respuestas de las APIs externas.
    # Vacio por defecto: sin host configurado, el cache simplemente se
    # salta y cada llamada va directo a la API externa.
    redis_host: str = ""
    redis_port: int = 6379

    # Trazas y metricas via OTLP hacia Grafana Cloud (acordado con el
    # equipo). Vacio por defecto: sin endpoint, OpenTelemetry no se activa.
    grafana_otlp_endpoint: str = ""
    grafana_otlp_user: str = ""
    grafana_otlp_token: str = ""
    otel_service_name: str = "api-gcp"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    # Evita releer el entorno en cada solicitud
    return Settings()
