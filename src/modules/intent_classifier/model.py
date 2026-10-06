from pydantic import BaseModel
from typing import Dict

class Predicao(BaseModel):
    probs: Dict[str, float]

class Dados(BaseModel):
    id: int
    nome: str
    text: str
    timestamp: int
    intent: str = None
