"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Fieldproxy AgentBench API",
    description=(
        "Regression-testing backend for field-service AI agents. "
        "Executes benchmark runs for real: the dispatch agent runs each "
        "scenario against seeded world data and every decision is checked "
        "by deterministic evaluation rules."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
