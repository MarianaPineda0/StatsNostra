import base64

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configurar_tracing(
    app: FastAPI, endpoint: str, usuario: str, token: str, nombre_servicio: str
) -> None:
    """Trazas y metricas via OpenTelemetry, exportadas por OTLP a Grafana
    Cloud -- mismo mecanismo que trading-journal y ecommerce, para verse
    juntos en un solo tablero. Instrumenta las rutas de FastAPI y las
    llamadas salientes de httpx. Sin endpoint no se activa nada.
    """
    if not endpoint:
        return

    credenciales = base64.b64encode(f"{usuario}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {credenciales}"}
    recurso = Resource.create({"service.name": nombre_servicio})

    proveedor_trazas = TracerProvider(resource=recurso)
    proveedor_trazas.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces", headers=headers))
    )
    trace.set_tracer_provider(proveedor_trazas)

    lector_metricas = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics", headers=headers),
        export_interval_millis=30000,
    )
    metrics.set_meter_provider(
        MeterProvider(resource=recurso, metric_readers=[lector_metricas])
    )

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
