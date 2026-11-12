from src.modules.intent_classifier.intent_classifier import IntentClassifier
import os

import time
from opentelemetry import metrics, trace


# Instrumentos do modulo (proxies ate o init_opentelemetry configurar o provider)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# --- Desempenho operacional -------------------------------------------------

# Os buckets padrao do OpenTelemetry (0, 5, 10, 25, ..., 10000) foram pensados
# para milissegundos. Como medimos em SEGUNDOS, toda inferencia (~0,05-0,5 s)
# caia no primeiro bucket (0-5 s) e o p95 no Grafana saia sempre ~4,75 s.
# Por isso declaramos buckets na escala de segundos.
LATENCY_BUCKETS_S = [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 10]

prediction_count = meter.create_counter(
    "prediction_count", description="Number of predictions made")
prediction_latency = meter.create_histogram(
    "prediction_latency_seconds", unit="s",
    description="Latency of model predictions in seconds",
    explicit_bucket_boundaries_advisory=LATENCY_BUCKETS_S)

# --- Dados de entrada -------------------------------------------------------

# Comprimento em palavras. Buckets crescentes porque mensagens de chat sao
# quase sempre curtas, com uma cauda longa de textos maiores.
WORD_BUCKETS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]

# Registrado UMA vez por mensagem (independe de quantos modelos existem)
input_words = meter.create_histogram(
    "input_words", unit="{word}",
    description="Length of the input message in words (one record per message)",
    explicit_bucket_boundaries_advisory=WORD_BUCKETS)

# Registrado uma vez por (modelo, intencao prevista): permite comparar o
# comprimento medio das mensagens que cada classe recebe
prediction_input_words = meter.create_histogram(
    "prediction_input_words", unit="{word}",
    description="Length of the input message in words, by model and predicted intent",
    explicit_bucket_boundaries_advisory=WORD_BUCKETS)

# --- Saida do modelo --------------------------------------------------------

SCORE_BUCKETS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]

# Confianca = probabilidade da classe escolhida (a maior de todas)
prediction_confidence = meter.create_histogram(
    "prediction_confidence", unit="1",
    description="Probability of the predicted (top-1) intent",
    explicit_bucket_boundaries_advisory=SCORE_BUCKETS)

# Margem = top-1 menos top-2. Perto de 0: o modelo ficou "em duvida" entre
# duas classes, mesmo que a confianca absoluta pareca razoavel
prediction_margin = meter.create_histogram(
    "prediction_margin", unit="1",
    description="Difference between the top-1 and top-2 intent probabilities",
    explicit_bucket_boundaries_advisory=SCORE_BUCKETS)


def confidence_and_margin(probs: dict) -> tuple:
    """Devolve (confianca, margem) a partir do dicionario de probabilidades."""
    top = sorted(probs.values(), reverse=True)
    if not top:
        return 0.0, 0.0
    second = top[1] if len(top) > 1 else 0.0
    return float(top[0]), float(top[0] - second)


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
        clf = IntentClassifier(load_model=url, wandb_project=wandb_project)
        _models[model_name] = clf

        # Inicializa o contador em 0 para cada (modelo, intencao). Sem isso, a
        # serie so nasce na primeira predicao, ja com o valor da rajada inteira,
        # e o rate()/increase() do Prometheus ignora esse primeiro salto.
        for intent in getattr(clf, 'codes', None) or []:
            prediction_count.add(0, {"model": model_name, "intent": str(intent)})
    return

def clear_models():
    _models.clear()


def predict_all(text: str):
    outputs = {}
    n_words = len(text.split())
    input_words.record(n_words)

    for model_name, clf in _models.items():
        # OpenTelemetry trace
        with tracer.start_as_current_span("model.predict",
                                          attributes={"model": model_name}):
            start = time.perf_counter()
            # predict text
            intent, probs = clf.predict(text)
            duration = time.perf_counter() - start

        # Record metrics
        labels = {"model": model_name, "intent": str(intent)}
        confidence, margin = confidence_and_margin(probs)
        prediction_latency.record(duration, {"model": model_name})
        prediction_count.add(1, labels)
        prediction_confidence.record(confidence, labels)
        prediction_margin.record(margin, labels)
        prediction_input_words.record(n_words, labels)

        # Output for the user
        outputs[model_name] = {'intent': intent, 'probs': probs}
    return outputs
