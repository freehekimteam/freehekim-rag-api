"""
RAG endpoint smoke tests for HakanCloud RAG API
"""
import sys
from pathlib import Path

# Add fastapi directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "fastapi"))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_rag_query_endpoint_exists():
    """Test that /rag/query endpoint exists"""
    response = client.post("/rag/query", json={"q": "test"})
    # Should not return 404
    assert response.status_code != 404


def test_rag_query_requires_question():
    """Test that /rag/query requires 'q' parameter"""
    response = client.post("/rag/query", json={})
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_rag_query_rejects_empty_question():
    """Test that /rag/query rejects empty question"""
    response = client.post("/rag/query", json={"q": ""})
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_metrics_endpoint_exists():
    """Test that /metrics endpoint exists (Prometheus)"""
    response = client.get("/metrics")
    assert response.status_code == 200
    # Prometheus metrics should be plain text
    assert "text/plain" in response.headers.get("content-type", "")
