"""Test setup: run the whole stack against SQLite."""

import os
import pathlib

# Must be set before any app import reads settings.
TEST_DB = pathlib.Path(__file__).parent / "test_agentbench.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

import pytest
from fastapi.testclient import TestClient

import app.models
from app.database import Base, SessionLocal, engine
from app.main import app
from scripts import seed


@pytest.fixture(scope="session", autouse=True)
def _database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed.seed_world(db)
    seed.seed_test_cases(db)
    seed.seed_agent_versions(db)
    db.close()
    yield


@pytest.fixture()
def client():
    return TestClient(app)
