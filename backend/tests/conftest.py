import os

os.environ["DATABASE_URL"] = "sqlite:///./test_sentinelai.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-only"

import pytest
from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client: yield test_client


@pytest.fixture
def auth_headers(client):
    response = client.post("/api/v1/auth/register", json={"username":"operator", "email":"operator@example.com", "password":"safe-password-123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
