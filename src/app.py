from fastapi import FastAPI
from pydantic import BaseModel

from src.shared.database.engine import Banco

from src.modules.intent_classifier.controller import router as intent_classifier_router 

app = FastAPI()

app.include_router(intent_classifier_router)





