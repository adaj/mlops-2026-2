import pytest

from src.modules.intent_classifier import service

pytestmark = pytest.mark.unit

URL_A = "equipe/projeto/modelo_a:v1"
URL_B = "equipe/projeto/modelo_b:latest"


@pytest.fixture(autouse=True)
def limpar_modelos():
    """Garante que um teste nunca enxerga modelos de outro."""
    service._models.clear()
    yield
    service._models.clear()


def test_predict_all_devolve_um_resultado_por_modelo(modelos_falsos):
    saida = service.predict_all("não entendi nada")

    assert set(saida) == {"modelo_a", "modelo_b"}
    for resultado in saida.values():
        assert resultado == {
            "intent": "confusion",
            "probs": {"confusion": 0.9, "neutral_statement": 0.1},
        }


def test_predict_all_sem_modelos_devolve_dicionario_vazio():
    assert service.predict_all("oi") == {}


def test_load_models_extrai_chave_da_url(monkeypatch):
    monkeypatch.setenv("WANDB_MODELS", URL_A)
    service.load_models()
    assert list(service._models) == ["modelo_a"]


def test_load_models_cria_um_classificador_por_url_e_remove_espacos(monkeypatch):
    monkeypatch.setenv("WANDB_MODELS", f" {URL_A} ,  {URL_B}")
    monkeypatch.setenv("WANDB_PROJECT", "meu-projeto")

    service.load_models()

    assert set(service._models) == {"modelo_a", "modelo_b"}
    assert service._models["modelo_a"].load_model == URL_A
    assert service._models["modelo_b"].load_model == URL_B
    assert service._models["modelo_a"].wandb_project == "meu-projeto"


def test_load_models_ignora_virgula_final(monkeypatch):
    monkeypatch.setenv("WANDB_MODELS", f"{URL_A},")
    service.load_models()
    assert list(service._models) == ["modelo_a"]


def test_load_models_respeita_variavel_alterada_depois_da_importacao(monkeypatch):
    monkeypatch.setenv("WANDB_MODELS", URL_A)
    service.load_models()
    service.clear_models()

    monkeypatch.setenv("WANDB_MODELS", URL_B)
    service.load_models()

    assert list(service._models) == ["modelo_b"]


def test_load_models_falha_quando_variavel_ausente(monkeypatch):
    monkeypatch.delenv("WANDB_MODELS", raising=False)
    with pytest.raises(RuntimeError):
        service.load_models()


@pytest.mark.parametrize("valor", ["", "   ", " , "])
def test_load_models_falha_quando_variavel_vazia(monkeypatch, valor):
    monkeypatch.setenv("WANDB_MODELS", valor)
    with pytest.raises(RuntimeError):
        service.load_models()


def test_clear_models_esvazia_o_dicionario(modelos_falsos):
    service.clear_models()
    assert service._models == {}

