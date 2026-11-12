import math
import random

import pytest

from src.modules.intent_classifier.observability import drift, reference

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def limpar():
    drift.clear(); reference.clear()
    yield
    drift.clear(); reference.clear()


# ----------------------------------------------------------------------- PSI
def test_psi_zero_quando_distribuicoes_iguais():
    assert drift.psi([0.2, 0.3, 0.5], [0.2, 0.3, 0.5]) == pytest.approx(0.0)


def test_psi_cresce_com_a_diferenca():
    base = [0.25, 0.25, 0.25, 0.25]
    pouco = drift.psi(base, [0.30, 0.25, 0.25, 0.20])
    muito = drift.psi(base, [0.70, 0.10, 0.10, 0.10])
    assert 0 < pouco < 0.1 < 0.25 < muito


def test_psi_valor_conhecido():
    # (0.5-0.25)*ln(0.5/0.25) + (0.5-0.75)*ln(0.5/0.75)
    esperado = 0.25 * math.log(2) - 0.25 * math.log(2 / 3)
    assert drift.psi([0.25, 0.75], [0.5, 0.5]) == pytest.approx(esperado)


def test_psi_faixa_vazia_nao_explode():
    assert math.isfinite(drift.psi([0.5, 0.5, 0.0], [0.0, 0.5, 0.5]))


def test_bin_shares_usa_limite_superior_inclusivo_e_mais_infinito():
    assert drift.bin_shares([1, 2, 3, 100], [1, 3]) == [0.25, 0.5, 0.25]


# ------------------------------------------------------------------------ KS
def test_ks_mesma_amostra():
    d, p = drift.ks_2samp([1, 2, 3, 4], [1, 2, 3, 4])
    assert d == 0 and p == pytest.approx(1.0)


def test_ks_amostras_separadas():
    d, p = drift.ks_2samp(list(range(50)), list(range(100, 150)))
    assert d == pytest.approx(1.0) and p < 1e-6


def test_ks_bate_com_valores_de_referencia_do_scipy():
    # scipy.stats.ks_2samp(a, b, method="asymp") -> D = 0.55, p = 0.0597
    a = [1, 2, 2, 3, 3, 3, 4, 4, 5, 6]
    b = [3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9]
    d, p = drift.ks_2samp(a, b)
    assert d == pytest.approx(0.55)
    assert p == pytest.approx(0.0597, abs=0.02)   # aproximacao assintotica diferente


def test_ks_detecta_deslocamento_e_nao_acusa_sem_drift():
    rng = random.Random(0)
    ref = [rng.gauss(0, 1) for _ in range(150)]
    assert drift.ks_2samp(ref, [rng.gauss(0, 1) for _ in range(200)])[1] > 0.05
    assert drift.ks_2samp(ref, [rng.gauss(1, 1) for _ in range(200)])[1] < 0.001


# ----------------------------------------------------- janela e comparacao
def _perfil(palavras, intents, confiancas):
    return {"class_share": {i: 0 for i in set(intents)},
            "samples": {"input_words": palavras, "predicted_intent": intents,
                        "confidence": confiancas}}


def test_compute_sem_amostras_suficientes_devolve_none(monkeypatch):
    monkeypatch.setattr(drift, "MIN_SAMPLES", 10)
    reference.register("m", _perfil([3] * 20, ["a"] * 20, [0.8] * 20))
    for _ in range(9):
        drift.observe("m", 3, "a", 0.8)
    assert drift.compute("m") is None


def test_compute_sem_drift_e_com_drift(monkeypatch):
    monkeypatch.setattr(drift, "MIN_SAMPLES", 10)
    rng = random.Random(1)
    ref_words = [rng.randint(2, 8) for _ in range(60)]
    ref_int = [rng.choice("ab") for _ in range(60)]
    ref_conf = [rng.uniform(0.6, 0.9) for _ in range(60)]
    reference.register("m", _perfil(ref_words, ref_int, ref_conf))

    for _ in range(100):   # producao parecida com a referencia
        drift.observe("m", rng.randint(2, 8), rng.choice("ab"), rng.uniform(0.6, 0.9))
    calmo = drift.compute("m")
    assert calmo["psi"]["input_words"] < 0.25
    assert calmo["ks"]["input_words"][1] > 0.01

    drift.clear()
    for _ in range(100):   # mensagens longas, so classe "a", confianca baixa
        drift.observe("m", rng.randint(20, 40), "a", rng.uniform(0.3, 0.5))
    agitado = drift.compute("m")
    assert agitado["psi"]["input_words"] > 0.25
    assert agitado["psi"]["predicted_intent"] > 0.1
    assert agitado["ks"]["confidence"][1] < 0.001


def test_janela_descarta_as_mais_antigas(monkeypatch):
    from collections import deque
    drift._windows["m"] = deque(maxlen=3)
    for n in [1, 2, 3, 4]:
        drift.observe("m", n, "a", 0.5)
    assert [r[0] for r in drift._windows["m"]] == [2, 3, 4]


def test_gauge_callback_publica_por_modelo_e_variavel(monkeypatch):
    monkeypatch.setattr(drift, "MIN_SAMPLES", 1)
    reference.register("m", _perfil([3, 4], ["a", "b"], [0.7, 0.8]))
    drift.observe("m", 3, "a", 0.7)
    obs = list(drift._observe("psi")(None))
    assert {o.attributes["feature"] for o in obs} == {"input_words", "confidence", "predicted_intent"}
    assert all(o.attributes["model"] == "m" for o in obs)
