# tests/test_api.py

import pytest
from fastapi.testclient import TestClient
from veille_db.app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_sources_workflow():
    # Test POST
    test_sources = ["https://example.com"]
    response = client.post("/sources", json=test_sources)
    assert response.status_code == 200

    # Test GET
    response = client.get("/sources")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_save_and_get_keywords(test_client):
    """Test la sauvegarde et récupération des mots-clés"""
    keywords = ["test1", "test2"]
    response = test_client.post("/keywords", json=keywords)
    assert response.status_code == 200
    
    response = test_client.get("/keywords")
    assert response.status_code == 200
    assert set(response.json()) == set(keywords)

def test_save_and_get_filters(test_client):
    """Test la sauvegarde et récupération des filtres"""
    filters = {
        "exclude_ads": True,
        "exclude_professional": False,
        "target_press": True,
        "time_unit": "mois",
        "time_value": 3,
        "exclude_jobs": True,
        "exclude_training": False
    }
    response = test_client.post("/filters", json=filters)
    assert response.status_code == 200
    
    response = test_client.get("/filters")
    assert response.status_code == 200
    assert response.json() == filters
