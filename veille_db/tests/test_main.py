import pytest
from fastapi.testclient import TestClient
from veille_db.app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_get_sources_empty():
    response = client.get("/sources")
    assert response.status_code == 200
    assert response.json() == []

def test_save_sources():
    sources = ["https://example.com", "https://test.com"]
    response = client.post("/sources", json=sources)
    assert response.status_code == 200
    assert response.json()["count"] == 2

def test_get_sources():
    sources = ["https://example.com", "https://test.com"]
    client.post("/sources", json=sources)
    response = client.get("/sources")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert "https://example.com" in response.json()
    assert "https://test.com" in response.json()
