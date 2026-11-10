import logging
import os

from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def init_opentelemetry():
    """Configura para ONDE a telemetria vai (traces, metricas e logs).

    O endpoint vem de OTEL_EXPORTER_OTLP_ENDPOINT (ex.: http://lgtm:4318) e o
    nome do servico de OTEL_SERVICE_NAME. Com OTEL_SDK_DISABLED=true (testes/CI)
    nada e configurado e os instrumentos dos modulos viram no-op.
    """
    if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        logging.getLogger(__name__).info("OpenTelemetry desativado (OTEL_SDK_DISABLED=true)")
        return

    # Resource.create ja le OTEL_SERVICE_NAME e OTEL_RESOURCE_ATTRIBUTES
    resource = Resource.create({"service.version": "0.1.0"})

    # Traces -> Tempo
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(trace_provider)

    # Metricas -> Prometheus/Mimir
    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    # Logs -> Loki
    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(log_provider)

    # Formata o console com trace_id/span_id E instala o handler que envia os
    # logs ao Loki (usa o logger provider acima). Nao adicione outro
    # LoggingHandler manualmente: os logs chegariam duplicados no Loki.
    LoggingInstrumentor().instrument(set_logging_format=True, log_level=logging.INFO)
    logging.getLogger().setLevel(logging.INFO)