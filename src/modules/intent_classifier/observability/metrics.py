"""Metricas de producao do classificador de intencoes.

O service.py so chama as funcoes record_*; quais instrumentos existem, que
rotulos levam e em que buckets caem fica concentrado aqui.
"""
from opentelemetry import metrics, trace

# Instrumentos criados na importacao: sao "proxies" ate o init_opentelemetry()
# configurar o provider; depois passam a exportar.
tracer = trace.get_tracer("src.modules.intent_classifier")
meter = metrics.get_meter("src.modules.intent_classifier")

# --- Buckets ----------------------------------------------------------------
# Os buckets padrao do OpenTelemetry (0, 5, 10, 25, ..., 10000) foram pensados
# para milissegundos. Medindo em SEGUNDOS, toda inferencia caia no primeiro
# bucket e o p95 no Grafana saia sempre ~4,75 s.
LATENCY_BUCKETS_S = [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 10]
# Mensagens de chat sao quase sempre curtas, com uma cauda longa de textos maiores
WORD_BUCKETS = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
SCORE_BUCKETS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]

# --- Desempenho operacional ---------------------------------------------------
prediction_count = meter.create_counter(
    "prediction_count", description="Number of predictions made")
prediction_latency = meter.create_histogram(
    "prediction_latency_seconds", unit="s",
    description="Latency of model predictions in seconds",
    explicit_bucket_boundaries_advisory=LATENCY_BUCKETS_S)

# --- Dados de entrada -----------------------------------------------------------
# Registrado UMA vez por mensagem (independe de quantos modelos existem)
input_words = meter.create_histogram(
    "input_words", unit="{word}",
    description="Length of the input message in words (one record per message)",
    explicit_bucket_boundaries_advisory=WORD_BUCKETS)
# Registrado por (modelo, intencao prevista)
prediction_input_words = meter.create_histogram(
    "prediction_input_words", unit="{word}",
    description="Length of the input message in words, by model and predicted intent",
    explicit_bucket_boundaries_advisory=WORD_BUCKETS)

# --- Saida do modelo ------------------------------------------------------------
# Confianca = probabilidade da classe escolhida (a maior de todas)
prediction_confidence = meter.create_histogram(
    "prediction_confidence", unit="1",
    description="Probability of the predicted (top-1) intent",
    explicit_bucket_boundaries_advisory=SCORE_BUCKETS)
# Margem = top-1 menos top-2. Perto de 0: modelo dividido entre duas classes
prediction_margin = meter.create_histogram(
    "prediction_margin", unit="1",
    description="Difference between the top-1 and top-2 intent probabilities",
    explicit_bucket_boundaries_advisory=SCORE_BUCKETS)


def count_words(text: str) -> int:
    return len(str(text).split())


def confidence_and_margin(probs: dict) -> tuple:
    """Devolve (confianca, margem) a partir do dicionario de probabilidades."""
    top = sorted(probs.values(), reverse=True)
    if not top:
        return 0.0, 0.0
    second = top[1] if len(top) > 1 else 0.0
    return float(top[0]), float(top[0] - second)


def init_prediction_counter(model_name: str, intents) -> None:
    """Cria as series do contador em 0 para cada (modelo, intencao).

    Sem isso, a serie so nasce na primeira predicao, ja com o valor da rajada
    inteira, e o rate()/increase() do Prometheus ignora esse primeiro salto.
    """
    for intent in intents or []:
        prediction_count.add(0, {"model": model_name, "intent": str(intent)})


def record_input(text: str) -> int:
    """Registra o comprimento da mensagem e devolve o numero de palavras."""
    n_words = count_words(text)
    input_words.record(n_words)
    return n_words


def record_prediction(model_name: str, intent, probs: dict,
                      duration_s: float, n_words: int) -> float:
    """Registra tudo o que medimos sobre UMA predicao de UM modelo.

    Devolve a confianca, que o drift.py tambem usa."""
    labels = {"model": model_name, "intent": str(intent)}
    confidence, margin = confidence_and_margin(probs)
    prediction_latency.record(duration_s, {"model": model_name})
    prediction_count.add(1, labels)
    prediction_confidence.record(confidence, labels)
    prediction_margin.record(margin, labels)
    prediction_input_words.record(n_words, labels)
    return confidence
