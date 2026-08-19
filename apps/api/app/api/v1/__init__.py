from fastapi import APIRouter

from app.api.v1 import agents, benchmark, runs

api_router = APIRouter()
api_router.include_router(agents.router)
api_router.include_router(runs.router)
api_router.include_router(benchmark.router)
