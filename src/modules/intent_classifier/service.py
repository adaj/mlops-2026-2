from src.modules.intent_classifier.intent_classifier import IntentClassifier
from src.modules.intent_classifier.observability import metrics as obs
from src.modules.intent_classifier.observability import reference, drift
import os
import time


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

        # Observabilidade: series do contador em 0 e perfil nos dados de referencia
        obs.init_prediction_counter(model_name, getattr(clf, 'codes', None))
        reference.load_and_register(model_name, clf)
    return

def clear_models():
    _models.clear()
    reference.clear()
    drift.clear()


def predict_all(text: str):
    outputs = {}
    n_words = obs.record_input(text)

    for model_name, clf in _models.items():
        # um span por modelo: no Tempo aparece dentro do trace do POST /predictions
        with obs.tracer.start_as_current_span("model.predict",
                                              attributes={"model": model_name}):
            start = time.perf_counter()
            intent, probs = clf.predict(text)
            duration = time.perf_counter() - start

        confidence = obs.record_prediction(model_name, intent, probs, duration, n_words)
        drift.observe(model_name, n_words, intent, confidence)
        outputs[model_name] = {'intent': intent, 'probs': probs}
    return outputs
