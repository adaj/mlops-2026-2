"""Perfil de cada modelo nos dados de REFERENCIA, para comparar com a producao.

Ideia: ao carregar um modelo, rodamos ele sobre os conjuntos de referencia
(data/reference/*_reference.yml: rotulados, balanceados e diferentes do treino)
e guardamos um resumo (o "perfil"): distribuicao das classes previstas,
confianca, margem e comprimento medios, acuracia.

Todas as mensagens passam por TODOS os modelos, entao o trafego esperado e o
mesmo para todos: o perfil de cada modelo usa a UNIAO dos conjuntos de
referencia. Ja a acuracia so considera os exemplos cujo rotulo o modelo conhece
(o confusion-clf nao tem como "acertar" um exemplo rotulado como ping). Esse perfil e exposto como
gauges reference_* no Prometheus. No Grafana, comparamos:

    producao (o que esta acontecendo agora)  x  referencia (o esperado)

summarize() e build_profile() sao funcoes puras (nao dependem da API nem do
OpenTelemetry), entao o mesmo calculo pode rodar depois no script de treino e
ser versionado junto com o modelo.
"""
import logging
from pathlib import Path

import yaml
from opentelemetry.metrics import Observation

from src.modules.intent_classifier.observability.metrics import (
    SCORE_BUCKETS, WORD_BUCKETS, confidence_and_margin, count_words, meter)

logger = logging.getLogger(__name__)

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "data" / "reference"
ALL = "_all"   # valor do rotulo intent para o agregado de todas as classes


# --------------------------------------------------------------------- dados
def reference_files(ref_dir: Path = None) -> list:
    """Todos os conjuntos de referencia (data/reference/*_reference.yml)."""
    return sorted(Path(ref_dir or REFERENCE_DIR).glob("*_reference.yml"))


def load_examples(path) -> list:
    """Le um YAML no formato do treino e devolve [(texto, rotulo), ...].

    str() em tudo: o YAML le exemplos como Yes/No como booleanos.
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return [(str(e), str(item["intent"])) for item in data for e in item["examples"]]


# ------------------------------------------------------------------- calculo
def _le(bound) -> str:
    return "%g" % bound


def _bucket_shares(values, bounds) -> dict:
    """Fracao dos valores em cada faixa (NAO cumulativo). Chave = limite superior."""
    counts = {_le(b): 0 for b in bounds}
    counts["+Inf"] = 0
    for v in values:
        key = next((_le(b) for b in bounds if v <= b), "+Inf")
        counts[key] += 1
    n = max(1, len(values))
    return {k: c / n for k, c in counts.items()}


def _mean(values) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize(texts, labels, predictions, intents=None) -> dict:
    """Resume as predicoes de um modelo sobre a referencia.

    predictions: lista de (intencao_prevista, probs) na mesma ordem de texts.
    intents: todas as classes do modelo (para que classes nunca previstas
             aparecam com participacao 0). A acuracia so conta os exemplos
             cujo rotulo esta entre essas classes.
    """
    rows = []
    for text, label, (pred, probs) in zip(texts, labels, predictions):
        conf, margin = confidence_and_margin(probs)
        rows.append({"label": str(label), "pred": str(pred), "conf": conf,
                     "margin": margin, "words": count_words(text)})
    n = len(rows)
    classes = sorted(set(map(str, intents or [])) | {r["pred"] for r in rows})

    def per_class(field):
        out = {ALL: _mean([r[field] for r in rows])}
        for c in classes:
            vals = [r[field] for r in rows if r["pred"] == c]
            if vals:
                out[c] = _mean(vals)
        return out

    return {
        "n": n,
        "accuracy": _mean([r["pred"] == r["label"] for r in rows
                           if not intents or r["label"] in classes]),
        "class_share": {c: sum(r["pred"] == c for r in rows) / max(1, n) for c in classes},
        "confidence_mean": per_class("conf"),
        "margin_mean": per_class("margin"),
        "input_words_mean": per_class("words"),
        "confidence_buckets": _bucket_shares([r["conf"] for r in rows], SCORE_BUCKETS),
        "input_words_buckets": _bucket_shares([r["words"] for r in rows], WORD_BUCKETS),
        # valores brutos: usados pelo drift.py (PSI e KS); nao viram metrica
        "samples": {"input_words": [r["words"] for r in rows],
                    "confidence": [r["conf"] for r in rows],
                    "predicted_intent": [r["pred"] for r in rows]},
    }


def build_profile(clf, examples) -> dict:
    """Roda o classificador em lote sobre os exemplos e devolve o perfil."""
    texts = [t for t, _ in examples]
    labels = [l for _, l in examples]
    predictions = clf.predict(texts)   # lista de (intencao, probs)
    return summarize(texts, labels, predictions, getattr(clf, "codes", None))


# ------------------------------------------------------- exposicao (gauges)
_profiles: dict = {}   # model_name -> perfil


def register(model_name: str, profile: dict) -> None:
    _profiles[model_name] = profile


def clear() -> None:
    _profiles.clear()


def load_and_register(model_name: str, clf, ref_dir: Path = None) -> dict | None:
    """Calcula e publica o perfil de referencia do modelo.

    Nunca derruba a API: sem arquivos de referencia, ou com erro no calculo,
    apenas registra um aviso e segue sem perfil.
    """
    files = reference_files(ref_dir)
    if not files:
        logger.warning("Sem dados de referencia em %s", ref_dir or REFERENCE_DIR)
        return None
    try:
        examples = [ex for f in files for ex in load_examples(f)]
        profile = build_profile(clf, examples)
    except Exception:
        logger.exception("Falha ao calcular o perfil de referencia de %s", model_name)
        return None
    register(model_name, profile)
    logger.info("Perfil de referencia de %s: %d exemplos, acuracia %.2f, confianca media %.2f",
                model_name, profile["n"], profile["accuracy"], profile["confidence_mean"][ALL])
    return profile


def _observe(field, label="intent"):
    """Callback de gauge: le o campo `field` de todos os perfis registrados."""
    def callback(_options):
        for model, prof in list(_profiles.items()):
            value = prof.get(field)
            if isinstance(value, dict):
                for key, v in value.items():
                    yield Observation(v, {"model": model, label: key})
            elif value is not None:
                yield Observation(value, {"model": model})
    return callback


# Gauges: valores "fotografados" no startup, sempre presentes no Prometheus
# (diferente dos contadores de producao, que lemos com increase()).
_GAUGES = [
    ("reference_examples", "n", "intent", "Number of labeled examples in the reference set"),
    ("reference_accuracy", "accuracy", "intent", "Accuracy of the model on the reference set"),
    ("reference_class_share", "class_share", "intent", "Share of each predicted intent on the reference set"),
    ("reference_confidence_mean", "confidence_mean", "intent", "Mean top-1 probability on the reference set"),
    ("reference_margin_mean", "margin_mean", "intent", "Mean top-1 minus top-2 probability on the reference set"),
    ("reference_input_words_mean", "input_words_mean", "intent", "Mean input length (words) on the reference set"),
    ("reference_confidence_bucket_share", "confidence_buckets", "le", "Share of reference predictions per confidence range"),
    ("reference_input_words_bucket_share", "input_words_buckets", "le", "Share of reference messages per length range"),
]
for _name, _field, _label, _desc in _GAUGES:
    meter.create_observable_gauge(_name, callbacks=[_observe(_field, _label)], description=_desc)
