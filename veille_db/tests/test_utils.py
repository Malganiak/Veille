# tests/test_utils.py

import pytest
from veille_db.app.utils import scrape_page, google_search, get_mysql_connection, get_mongo_client

def test_scrape_page():
    """
    Teste la fonction scrape_page avec une URL déjà utilisée dans app.py
    (exemple : bearingpoint.com).
    """
    url = (
        "https://www.bearingpoint.com/fr-fr/publications-evenements/"
        "blogs/marketing-vente/exp%C3%A9rience-client-comment-ia-g%C3%A9n%C3%A9rative-va-renforcer-emotion/"
    )
    result = scrape_page(url)

    # On s'attend à ce que result ne soit pas None
    assert result is not None, "scrape_page doit retourner un objet Page, pas None."
    assert result.title is not None, "Le titre ne doit pas être None."
    assert len(result.content) > 50, "Le contenu de l'article doit faire plus de 50 caractères."

def test_google_search():
    """
    Teste la fonction google_search pour vérifier que le retour contient bien des liens.
    On limite num_results à 2 pour éviter de trop appeler l'API.
    """
    query = "expérience client"
    results = google_search(query, num_results=2)
    assert isinstance(results, list), "La fonction doit retourner une liste d'URLs."
    assert len(results) > 0, "On s'attend à avoir au moins 1 résultat."
    for url in results:
        assert url.startswith("http"), f"L'URL doit commencer par 'http', or: {url}"

def test_mysql_connection():
    conn = get_mysql_connection()
    assert conn is not None
    conn.close()

def test_mongo_connection():
    client = get_mongo_client()
    assert client is not None
    client.close()
