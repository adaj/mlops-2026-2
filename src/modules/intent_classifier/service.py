from src.modules.intent_classifier.intent_classifier import IntentClassifier
import os

WANDB_MODELS = os.environ.get("WANDB_MODELS")
WANDB_PROJECT = os.environ.get("WANDB_PROJECT")

_models = {}

import logging

logger = logging.getLogger(__name__)


def load_models():
    url_models = [i.strip() for i in WANDB_MODELS.split(',')]
    if not url_models:
        raise RuntimeError("Sem WANDB_MODELS no .env.")

    for url in url_models:
        logger.info("Carregando modelo %s ...", url)
        model_name = url.split('/')[-1]
        _models[model_name] = IntentClassifier(load_model=url, wandb_project=WANDB_PROJECT)
    
    logger.info("Modelos carregados.")
    return

def clear_models():
    _models.clear()
    return


def predict_all(text: str):
    outputs = {}
    for model_name, clf in _models.items():
        intent, probs = clf.predict(text)
        outputs[model_name] = {'intent': intent,
                               'probs': probs}
    return outputs