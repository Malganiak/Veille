import pytest
from fastapi.testclient import TestClient
from veille_db.app.main import app
import pymysql
import os

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """Configure les variables d'environnement pour les tests"""
    monkeypatch.setenv("MYSQL_HOST", "localhost")
    monkeypatch.setenv("MYSQL_USER", "root")
    monkeypatch.setenv("MYSQL_PASSWORD", "root")
    monkeypatch.setenv("MYSQL_DATABASE", "bd_veille")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/mydb")

@pytest.fixture(scope="function", autouse=True)
def reset_sources_table():
    # Charger les variables d'environnement
    from veille_db.app.main import get_mysql_connection
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            # Supprimer toutes les entrées de la table sources
            cursor.execute("DELETE FROM sources")
        conn.commit()
    finally:
        conn.close()
