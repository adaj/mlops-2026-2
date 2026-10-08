from fastapi import APIRouter

from src.modules.intent_classifier.model import Mensagem, ResultadoModelo
from src.modules.intent_classifier import service

router = APIRouter()

@router.post("/predictions")
def post_predictions(msg: Mensagem):
    output = service.predict_all(msg.text)
    return output

    

