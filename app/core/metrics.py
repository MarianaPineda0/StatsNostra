from opentelemetry import metrics

# Via OTel (no prometheus_client): asi viajan por el mismo exportador OTLP
# que ya empuja trazas y metricas HTTP a Grafana Cloud, sin depender de que
# algo scrapee /metrics dentro del cluster.
_meter = metrics.get_meter("statsnostra")

cache_aciertos = _meter.create_counter(
    "statsnostra_cache_aciertos", description="Aciertos de la cache distribuida"
)
cache_fallos = _meter.create_counter(
    "statsnostra_cache_fallos", description="Fallos de la cache distribuida"
)
