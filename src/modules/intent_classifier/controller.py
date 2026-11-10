import logging

from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv

load_dotenv()

from src.modules.intent_classifier.model import Mensagem, ResultadoModelo, PredicaoMensagem
from src.modules.intent_classifier import service

from src.shared.database.engine import prediction_collection

# Vai para o console e para o Loki, com o trace_id da requisicao em andamento
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post('/predictions')
def post_predictions(msg: Mensagem):
    logger.info("Predicao solicitada (%d caracteres)", len(msg.text))

    outputs = service.predict_all(msg.text)

    # uma linha por modelo: facilita filtrar no Loki por modelo ou intencao
    for model_name, pred in outputs.items():
        logger.info("Predicao concluida: model=%s intent=%s", model_name, pred['intent'])

    outputs['message'] = msg.model_dump()          # a mensagem entra ANTES de gravar
    try:
        prediction_collection.insert_one(outputs)  # grava predicoes + mensagem
    except Exception:
        logger.exception("Falha ao gravar a predicao no MongoDB")
        raise
    outputs.pop('_id', None)                       # o insert_one adiciona _id (ObjectId)
    return outputs

@router.get('/predictions')
def get_predictions(limit: int = 20):
    cursor = (prediction_collection
              .find({}, {'_id': 0})                # _id fora, ObjectId nao vira JSON
              .sort('message.timestamp', -1)       # mais recentes primeiro
              .limit(limit))
    results = list(cursor)                         # cursor -> lista de itens no banco
    logger.info("Consulta de predicoes: limit=%d, retornadas=%d", limit, len(results))
    return results