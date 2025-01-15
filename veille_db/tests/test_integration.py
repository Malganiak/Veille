import pytest
from veille_db.app.utils import get_mongo_client, get_mysql_connection
from veille_db.app.main import app
from fastapi.testclient import TestClient

@pytest.fixture
def test_client():
    return TestClient(app)

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