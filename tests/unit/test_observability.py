import re
from pathlib import Path

import pytest
import yaml

from src.modules.intent_classifier.observability import metrics, reference

pytestmark = pytest.mark.unit

DATA = Path(reference.REFERENCE_DIR).parent


@pytest.fixture(autouse=True)
def limpar_perfis():
    reference.clear()
    yield
    reference.clear()


# ----------------------------------------------------------------- metrics.py
@pytest.mark.parametrize("probs, esperado", [
    ({"a": 0.7, "b": 0.2, "c": 0.1}, (0.7, 0.5)),
    ({"a": 0.5, "b": 0.5}, (0.5, 0.0)),
    ({"a": 1.0}, (1.0, 1.0)),
    ({}, (0.0, 0.0)),
])
def test_confidence_and_margin(probs, esperado):
    confianca, margem = metrics.confidence_and_margin(probs)
    assert confianca == pytest.approx(esperado[0])
    assert margem == pytest.approx(esperado[1])


def test_count_words():
    assert metrics.count_words("não entendi nada") == 3
    assert metrics.count_words("  oi  ") == 1


# --------------------------------------------------------- dados de referencia
@pytest.mark.parametrize("dataset", ["confusion", "clair_intents"])
def test_referencia_e_balanceada_e_so_tem_texto(dataset):
    exemplos = reference.load_examples(DATA / "reference" / f"{dataset}_reference.yml")
    por_classe = {}
    for texto, rotulo in exemplos:
        assert isinstance(texto, str) and texto.strip()
        por_classe[rotulo] = por_classe.get(rotulo, 0) + 1
    assert len(set(por_classe.values())) == 1, f"desbalanceado: {por_classe}"


def _normaliza(texto):
    return re.sub(r"[^a-z0-9 ]", "", texto.lower().replace("claire", "clair")).split()


@pytest.mark.parametrize("dataset", ["confusion", "clair_intents"])
def test_referencia_nao_repete_exemplos_do_treino(dataset):
    """Se um exemplo da referencia estiver no treino, as metricas ficam otimistas."""
    treino = {tuple(_normaliza(t)) for t, _ in
              reference.load_examples(DATA / "train" / f"{dataset}_examples.yml")}
    repetidos = [t for t, _ in
                 reference.load_examples(DATA / "reference" / f"{dataset}_reference.yml")
                 if tuple(_normaliza(t)) in treino]
    assert repetidos == []


def test_load_examples_converte_yes_no_para_texto(tmp_path):
    arquivo = tmp_path / "x_reference.yml"
    arquivo.write_text("- intent: neutral\n  examples:\n    - Yes\n    - No\n")
    assert reference.load_examples(arquivo) == [("True", "neutral"), ("False", "neutral")]


def test_reference_files_acha_todos_os_conjuntos():
    nomes = [f.name for f in reference.reference_files()]
    assert nomes == ["clair_intents_reference.yml", "confusion_reference.yml"]


# ------------------------------------------------------------------- perfil
def test_summarize_calcula_acuracia_participacao_e_medias():
    textos = ["a b", "a b c d", "a"]
    rotulos = ["x", "y", "y"]
    predicoes = [("x", {"x": 0.8, "y": 0.2}),
                 ("x", {"x": 0.6, "y": 0.4}),
                 ("y", {"x": 0.3, "y": 0.7})]

    perfil = reference.summarize(textos, rotulos, predicoes, intents=["x", "y", "z"])

    assert perfil["n"] == 3
    assert perfil["accuracy"] == pytest.approx(2 / 3)
    assert perfil["samples"]["input_words"] == [2, 4, 1]
    assert perfil["class_share"] == pytest.approx({"x": 2 / 3, "y": 1 / 3, "z": 0.0})
    assert perfil["confidence_mean"]["_all"] == pytest.approx((0.8 + 0.6 + 0.7) / 3)
    assert perfil["confidence_mean"]["x"] == pytest.approx(0.7)
    assert "z" not in perfil["confidence_mean"]          # nunca prevista: sem media
    assert perfil["input_words_mean"]["x"] == pytest.approx(3.0)
    assert sum(perfil["input_words_buckets"].values()) == pytest.approx(1.0)
    assert perfil["input_words_buckets"]["1"] == pytest.approx(1 / 3)


class ClassificadorEmLote:
    codes = ["x", "y"]

    def predict(self, textos):
        return [("x", {"x": 0.9, "y": 0.1}) for _ in textos]


def test_load_and_register_usa_a_uniao_e_acuracia_so_nos_rotulos_do_modelo(tmp_path):
    (tmp_path / "a_reference.yml").write_text(
        "- intent: x\n  examples: [oi, ola]\n- intent: y\n  examples: [tchau, adeus]\n")
    (tmp_path / "b_reference.yml").write_text("- intent: ping\n  examples: [clair, alo]\n")

    perfil = reference.load_and_register("meu-clf", ClassificadorEmLote(), tmp_path)

    assert perfil["n"] == 6                                # uniao dos dois arquivos
    assert perfil["accuracy"] == pytest.approx(0.5)        # "ping" fica fora da acuracia
    assert reference._profiles["meu-clf"] is perfil


def test_load_and_register_sem_arquivo_nao_quebra(tmp_path):
    assert reference.load_and_register("sem-ref-clf", ClassificadorEmLote(), tmp_path) is None
    assert reference._profiles == {}


def test_gauge_callback_le_os_perfis():
    reference.register("m", {"accuracy": 0.9, "class_share": {"x": 0.25, "y": 0.75}})
    obs_acc = list(reference._observe("accuracy")(None))
    obs_share = list(reference._observe("class_share")(None))
    assert [(o.value, dict(o.attributes)) for o in obs_acc] == [(0.9, {"model": "m"})]
    assert {o.attributes["intent"]: o.value for o in obs_share} == {"x": 0.25, "y": 0.75}
