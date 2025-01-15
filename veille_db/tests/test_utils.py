# tests/test_utils.py

import pytest
from veille_db.app.utils import scrape_page, get_mysql_connection, get_mongo_client, save_page_to_mongodb, Page

def test_scrape_page():
    """Test basique de scrape_page"""
    url = "https://www.example.com"
    result = scrape_page(url)
    assert result is None or hasattr(result, 'title')

@pytest.mark.integration
def test_mysql_connection():
    """Test de connexion MySQL"""
    conn = get_mysql_connection()
    assert conn is not None
    conn.close()

@pytest.mark.integration
def test_mongo_connection():
    """Test de connexion MongoDB"""
    client = get_mongo_client()
    assert client is not None
    client.close()

def test_get_mongo_client():
    client = get_mongo_client()
    assert client is not None
    assert client.server_info()  # Vérifie la connexion

def test_save_page_to_mongodb():
    page = Page(title="Test Page", link="https://test.com", content="Test Content", date="2023-10-01")
    result = save_page_to_mongodb(page)
    assert result is True  # Supposant que la fonction retourne True en cas de succès
