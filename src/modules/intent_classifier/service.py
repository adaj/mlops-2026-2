from src.modules.intent_classifier.intent_classifier import IntentClassifier
import os

import time
from opentelemetry import metrics, trace


# Instrumentos do modulo (proxies ate o init_opentelemetry configurar o provider)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Create metrics
prediction_count = meter.create_counter(
    "prediction_count", description="Number of predictions made")
prediction_latency = meter.create_histogram(
    "prediction_latency_seconds", unit="s",
    description="Latency of model predictions in seconds")


_models = {}

def load_models():
    # lidas aqui (e nao na importacao) para respeitar o ambiente atual
    wandb_models = os.environ.get('WANDB_MODELS', '')
    wandb_project = os.environ.get('WANDB_PROJECT')

    url_models = [url.strip() for url in wandb_models.split(',') if url.strip()]
    if not url_models:
        raise RuntimeError('Sem modelos: defina WANDB_MODELS com uma ou mais URLs separadas por virgula.')

    for url in url_models:
        model_name = url.split('/')[-1].split(':')[0]
        _models[model_name] = IntentClassifier(load_model=url, 
                                               wandb_project=wandb_project)
    return

def clear_models():
    _models.clear()


def predict_all(text: str):
    outputs = {}
    for model_name, clf in _models.items():
        # OpenTelemetry trace
        with tracer.start_as_current_span("model.predict",
                                          attributes={"model": model_name}):
            start = time.perf_counter()
            # predict text
            intent, probs = clf.predict(text)
            duration = time.perf_counter() - start
        
        # Record metrics
        prediction_latency.record(duration, {"model": model_name})
        prediction_count.add(1, {"model": model_name, "intent": intent})

        # Output for the user
        outputs[model_name] = {'intent': intent, 'probs': probs}
    return outputs