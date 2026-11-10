"""Configuracao compartilhada dos testes.

Tudo aqui roda ANTES de qualquer import do projeto.
"""
import os
import sys
import types

import mongomock
import pytest
from fastapi.testclient import TestClient


# (a) Variaveis de ambiente falsas: o engine.py le MONGO_URL na importacao.
# WANDB_MODELS fica AUSENTE de proposito: cada teste define o que precisa.
os.environ["MONGO_URL"] = "mongodb://localhost:27017"
os.environ["WANDB_API_KEY"] = "fake"
os.environ["WANDB_PROJECT"] = "teste"
os.environ["OTEL_SDK_DISABLED"] = "true"   # sem exportar telemetria nos testes
os.environ.pop("WANDB_MODELS", None)


# (b) IntentClassifier falso. O de verdade importa TensorFlow, tensorflow_text
# e wandb: lento (dezenas de segundos), pesado e precisa de rede e conta no
# W&B. Nos testes queremos isolamento (testar so o NOSSO codigo) e velocidade,
# entao trocamos o modulo inteiro em sys.modules antes de importar o service.
class IntentClassifierFalso:
    def __init__(self, load_model=None, wandb_project=None):
        self.load_model = load_model
        self.wandb_project = wandb_project

    def predict(self, text):
        return "confusion", {"confusion": 0.9, "neutral_statement": 0.1}


_modulo_falso = types.ModuleType("src.modules.intent_classifier.intent_classifier")
_modulo_falso.IntentClassifier = IntentClassifierFalso
sys.modules["src.modules.intent_classifier.intent_classifier"] = _modulo_falso

# Imports do projeto SO depois das configuracoes acima.
from src.app import app  # noqa: E402
from src.modules.intent_classifier import controller, service  # noqa: E402


# (c) Fixtures
@pytest.fixture
def modelos_falsos():
    """Dois modelos falsos ja carregados em service._models."""
    service._models.clear()
    service._models["modelo_a"] = IntentClassifierFalso()
    service._models["modelo_b"] = IntentClassifierFalso()
    yield service._models
    service._models.clear()


@pytest.fixture
def colecao(monkeypatch):
    """Colecao do Mongo em memoria, no lugar da colecao real do controller."""
    colecao_falsa = mongomock.MongoClient().db.predictions
    monkeypatch.setattr(controller, "prediction_collection", colecao_falsa)
    return colecao_falsa


@pytest.fixture
def client(modelos_falsos, colecao):
    """Cliente HTTP do app real. Sem `with`: nao dispara o lifespan
    (que tentaria carregar modelos de verdade)."""
    return TestClient(app)
