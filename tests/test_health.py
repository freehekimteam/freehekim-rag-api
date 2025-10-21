"""
Health endpoint tests for FreeHekim RAG API
"""
import sys
from pathlib import Path

# Add fastapi directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "fastapi"))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_health_endpoint_returns_200():
    """Test that /health endpoint returns 200 OK"""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_has_status():
    """Test that /health endpoint returns status field"""
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"


def test_health_endpoint_has_env():
    """Test that /health endpoint returns env field"""
    response = client.get("/health")
    data = response.json()
    assert "env" in data
    assert data["env"] in ["staging", "production", "development"]


def test_ready_endpoint_returns_valid_status():
    """Test that /ready endpoint returns 200 or 503 (depending on Qdrant availability)"""
    response = client.get("/ready")
    # 200 = Qdrant connected, 503 = Qdrant unavailable (both valid)
    assert response.status_code in [200, 503]


def test_ready_endpoint_has_ready_field():
    """Test that /ready endpoint returns ready field"""
    response = client.get("/ready")
    data = response.json()
    assert "ready" in data
    assert isinstance(data["ready"], bool)
