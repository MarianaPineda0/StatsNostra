import base64
import logging

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.trace import trace_id_var


class _FiltroTraceIdNegocio(logging.Filter):
    """Copia el trace-id de negocio (X-Trace-Id, ver app/core/trace.py) como
    atributo del log de OTel. Es distinto del trace-id nativo de OTel (el de
    los spans en Tempo): este es el id de correlacion que propagan las 3
    nubes via header, y es el que hay que poder filtrar tambien en Loki.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id_negocio = trace_id_var.get() or None
        return True


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

    proveedor_logs = LoggerProvider(resource=recurso)
    exportador_logs = OTLPLogExporter(endpoint=f"{endpoint}/v1/logs", headers=headers)
    proveedor_logs.add_log_record_processor(BatchLogRecordProcessor(exportador_logs))
    set_logger_provider(proveedor_logs)

    manejador_logs = LoggingHandler(level=logging.NOTSET, logger_provider=proveedor_logs)
    manejador_logs.addFilter(_FiltroTraceIdNegocio())
    # Se agrega (no se reemplaza) el handler que ya puso configurar_logging:
    # el JSON por stdout sigue igual para Cloud Logging, esto solo suma el
    # envio a Grafana Loki. uvicorn.access/error tienen su propio handler
    # por fuera del root (ver logging_config.py), hay que agregarselo aparte.
    for nombre in ("", "uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(nombre).addHandler(manejador_logs)

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
