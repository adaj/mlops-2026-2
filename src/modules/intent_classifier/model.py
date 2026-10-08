from pydantic import BaseModel, Field
from typing import Dict, Optional

from datetime import datetime, timezone 

def agora():
    return datetime.now(timezone.utc)


class ResultadoModelo(BaseModel):
    intent: str
    probs: Dict[str, float]


class Mensagem(BaseModel):
    id: Optional[str]
    nome: Optional[str] = Field(min_length=1)
    text: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=agora)

class PredicaoMensagem(BaseModel):
    id: Optional[str] = None
    mensagem: Mensagem
    predicao: Dict[str, ResultadoModelo]