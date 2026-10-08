from fastapi import APIRouter

from src.modules.intent_classifier import service
from src.modules.intent_classifier.model import Mensagem, PredicaoMensagem


router = APIRouter(prefix="/intent-classifier", 
                   tags=["intent-classifier"])

@router.post("/predictions", response_model=PredicaoMensagem)
def create_prediction(msg: Mensagem):
    resultados = service.predict_all(msg.text)
    return PredicaoMensagem(mensagem=msg, resultados=resultados)