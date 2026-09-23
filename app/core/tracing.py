from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configurar_tracing(app: FastAPI, project_id: str) -> None:
    """Trazas distribuidas con OpenTelemetry, exportadas a Cloud Trace.

    Instrumenta las rutas de FastAPI y las llamadas salientes de httpx
    (hacia trading-journal y ecommerce) para que ambas queden dentro del
    mismo trace. Sin project_id no se activa nada.
    """
    if not project_id:
        return

    provider = TracerProvider()
    provider.add_span_processor(
        BatchSpanProcessor(CloudTraceSpanExporter(project_id=project_id))
    )
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
