"""Deteccao de drift: producao (janela deslizante) x referencia.

Para cada modelo guardamos as ultimas N mensagens de producao (DRIFT_WINDOW_SIZE,
padrao 200) e comparamos com as predicoes do mesmo modelo nos dados de
referencia (reference.py):

  PSI (Population Stability Index), para
    - input_words       comprimento da mensagem          -> data drift
    - predicted_intent  classe prevista                  -> prediction drift
    - confidence        probabilidade da classe escolhida -> prediction drift

  KS (Kolmogorov-Smirnov, duas amostras), para as variaveis numericas
    - input_words, confidence
    estatistica D = maior distancia entre as duas distribuicoes acumuladas,
    e o p-valor (chance de ver um D desse tamanho se NAO houvesse drift).

Por que calcular aqui e nao no PromQL? O PSI precisa da fracao em cada faixa
e o Prometheus guarda faixas acumuladas; e o KS fica mais preciso com os
valores brutos do que com faixas. As funcoes psi() e ks_2samp() sao puras.

Regra de bolso do PSI: < 0,1 estavel; 0,1-0,25 mudanca moderada; > 0,25 mudanca
significativa. Com amostras pequenas (a referencia tem 45 e 105 exemplos) o PSI
oscila bastante: olhe a tendencia, nao um ponto isolado.
"""
import math
import os
import threading
from collections import deque

from opentelemetry.metrics import Observation

from src.modules.intent_classifier.observability import reference
from src.modules.intent_classifier.observability.metrics import (
    SCORE_BUCKETS, WORD_BUCKETS, meter)

WINDOW_SIZE = int(os.getenv("DRIFT_WINDOW_SIZE", "200"))
MIN_SAMPLES = int(os.getenv("DRIFT_MIN_SAMPLES", "30"))
EPS = 1e-4   # evita log(0) em faixas vazias


# ------------------------------------------------------------ funcoes puras
def bin_shares(values, bounds) -> list:
    """Fracao dos valores em cada faixa (v <= limite), com uma faixa final +Inf."""
    counts = [0] * (len(bounds) + 1)
    for v in values:
        i = next((k for k, b in enumerate(bounds) if v <= b), len(bounds))
        counts[i] += 1
    n = max(1, len(values))
    return [c / n for c in counts]


def category_shares(values, categories) -> list:
    n = max(1, len(values))
    return [sum(v == c for v in values) / n for c in categories]


def psi(expected, actual, eps: float = EPS) -> float:
    """PSI = soma (atual - esperado) * ln(atual / esperado), por faixa."""
    total = 0.0
    for e, a in zip(expected, actual):
        e, a = max(e, eps), max(a, eps)
        total += (a - e) * math.log(a / e)
    return total


def _kolmogorov_q(lam: float) -> float:
    """P(D > d) assintotico: 2 * soma (-1)^(k-1) exp(-2 k^2 lam^2)."""
    if lam < 1e-3:
        return 1.0
    total = 0.0
    for k in range(1, 101):
        term = 2 * (-1) ** (k - 1) * math.exp(-2 * k * k * lam * lam)
        total += term
        if abs(term) < 1e-10:
            break
    return min(1.0, max(0.0, total))


def ks_2samp(a, b) -> tuple:
    """KS de duas amostras: devolve (estatistica D, p-valor aproximado).

    Com valores discretos (contagem de palavras) ha empates e o p-valor fica
    conservador (maior do que deveria): na duvida, ele subestima o drift.
    """
    a, b = sorted(a), sorted(b)
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return 0.0, 1.0
    i = j = 0
    d = 0.0
    while i < n and j < m:
        x = min(a[i], b[j])
        while i < n and a[i] <= x:
            i += 1
        while j < m and b[j] <= x:
            j += 1
        d = max(d, abs(i / n - j / m))
    ne = n * m / (n + m)
    lam = (math.sqrt(ne) + 0.12 + 0.11 / math.sqrt(ne)) * d
    return d, _kolmogorov_q(lam)


def compare(ref: dict, prod: dict, categories) -> dict:
    """Compara amostras de referencia e de producao (listas por variavel)."""
    return {
        "psi": {
            "input_words": psi(bin_shares(ref["input_words"], WORD_BUCKETS),
                               bin_shares(prod["input_words"], WORD_BUCKETS)),
            "confidence": psi(bin_shares(ref["confidence"], SCORE_BUCKETS),
                              bin_shares(prod["confidence"], SCORE_BUCKETS)),
            "predicted_intent": psi(category_shares(ref["predicted_intent"], categories),
                                    category_shares(prod["predicted_intent"], categories)),
        },
        "ks": {
            "input_words": ks_2samp(ref["input_words"], prod["input_words"]),
            "confidence": ks_2samp(ref["confidence"], prod["confidence"]),
        },
    }


# ------------------------------------------------- janela de producao
_windows: dict = {}          # model -> deque[(n_words, intent, confidence)]
_lock = threading.Lock()     # o FastAPI atende requisicoes em varias threads


def observe(model_name: str, n_words: int, intent, confidence: float) -> None:
    with _lock:
        window = _windows.setdefault(model_name, deque(maxlen=WINDOW_SIZE))
        window.append((n_words, str(intent), confidence))


def clear() -> None:
    with _lock:
        _windows.clear()


def compute(model_name: str):
    """Drift atual do modelo, ou None se faltar referencia ou amostras."""
    profile = reference._profiles.get(model_name)
    with _lock:
        rows = list(_windows.get(model_name, ()))
    if not profile or "samples" not in profile or len(rows) < MIN_SAMPLES:
        return None
    prod = {"input_words": [r[0] for r in rows],
            "predicted_intent": [r[1] for r in rows],
            "confidence": [r[2] for r in rows]}
    categories = sorted(set(profile["class_share"]) | set(prod["predicted_intent"]))
    return compare(profile["samples"], prod, categories)


# ------------------------------------------------------------ gauges
def _window_size(_options):
    with _lock:
        sizes = {m: len(w) for m, w in _windows.items()}
    for model, size in sizes.items():
        yield Observation(size, {"model": model})


def _observe(kind, index=None):
    def callback(_options):
        for model in list(reference._profiles):
            result = compute(model)
            if result is None:
                continue
            for feature, value in result[kind].items():
                v = value if index is None else value[index]
                yield Observation(v, {"model": model, "feature": feature})
    return callback


meter.create_observable_gauge("drift_window_size", callbacks=[_window_size],
                              description="Production messages currently in the drift window")
meter.create_observable_gauge("drift_psi", callbacks=[_observe("psi")],
                              description="Population Stability Index, production window vs reference")
meter.create_observable_gauge("drift_ks_statistic", callbacks=[_observe("ks", 0)],
                              description="Kolmogorov-Smirnov D, production window vs reference")
meter.create_observable_gauge("drift_ks_pvalue", callbacks=[_observe("ks", 1)],
                              description="Kolmogorov-Smirnov p-value, production window vs reference")
