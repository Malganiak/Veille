import pytest
from veille_db.app.utils import get_mongo_client, get_mysql_connection
from veille_db.app.main import app
from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as client:
        yield client

def test_database_connections():
    """Test des connexions aux bases de données"""
    # Test MongoDB
    mongo_client = get_mongo_client()
    assert mongo_client.server_info() is not None
    mongo_client.close()
    
    # Test MySQL
    mysql_conn = get_mysql_connection()
    with mysql_conn.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result is not None
    mysql_conn.close()

def test_api_health():
    """Test de santé de l'API"""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200

@pytest.mark.integration
def test_full_workflow(test_client):
    """Test d'intégration complet"""
    # Test sources
    sources = ["https://example.com"]
    response = test_client.post("/sources", json=sources)
    assert response.status_code == 200
    
    response = test_client.get("/sources")
    assert response.status_code == 200
    assert len(response.json()) > 0

    # Test keywords
    keywords = ["test1", "test2"]
    response = test_client.post("/keywords", json=keywords)
    assert response.status_code == 200

    # Test filters
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