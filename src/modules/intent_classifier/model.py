from datetime import datetime, timezone
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


def agora() -> datetime:
    return datetime.now(timezone.utc)


class Mensagem(BaseModel):
    """O que entra na API: o texto e os metadados que o painel vai usar."""
    text: str = Field(min_length=1)
    nome: Optional[str] = None
    message_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=agora)

    model_config = ConfigDict(
        json_schema_extra={"examples": [{
            "text": "Não entendi como resolver esse exercício",
            "nome": "Maria",
            "message_id": "msg-001",
            "timestamp": "2026-10-08T14:30:00Z",
        }]}
    )


class ResultadoModelo(BaseModel):
    """O resultado de UM modelo para a mensagem."""
    top_intent: str
    probs: Dict[str, float]


class PredicaoMensagem(BaseModel):
    """A predição de uma mensagem, com o resultado de cada modelo carregado.
    É o que a API devolve e o que fica guardado no Mongo."""
    id: Optional[str] = None
    mensagem: Mensagem
    resultados: Dict[str, ResultadoModelo]
    created_at: datetime = Field(default_factory=agora)