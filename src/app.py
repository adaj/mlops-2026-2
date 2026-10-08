from fastapi import FastAPI
from pydantic import BaseModel
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import uvicorn

load_dotenv()

from src.modules.intent_classifier.controller import router as intent_classifier_router
from src.modules.intent_classifier import service as intent_classifier_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Codigos que precisam ser executados no start da API
    intent_classifier_service.load_models()
    yield
    # Codigos que precisam ser executaods no close da API
    intent_classifier_service.clear_models()


app = FastAPI(
    title="API do Intent Classifier",
    description="(...)",
    version="0.1.0",
    docs_url='/docs',
    lifespan=lifespan
)


app.include_router(intent_classifier_router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}


