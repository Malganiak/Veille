# utils.py

from dataclasses import dataclass
import os
import json
import csv
import hashlib
import streamlit as st
import requests
from bs4 import BeautifulSoup
import lxml
from lxml import html as lxml_html
from typing import Optional, Any, Dict
import logging
import ollama
from dateutil import parser
from reportlab.lib import pagesizes
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from io import BytesIO
import re
import time
import random
from urllib.parse import urljoin
from datetime import datetime, timedelta
import pypdf
from docx import Document
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from bson import ObjectId
from dotenv import load_dotenv

# Ajouts pour MongoDB et MySQL
from pymongo import MongoClient
import pymysql

load_dotenv()

# Google API configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CSE_ID = os.getenv("CSE_ID")

###############################
# Fonctions MongoDB (inchangées)
###############################
def get_mongo_client():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    try:
        # Vérifier la connexion
        client.admin.command('ping')
        return client
    except Exception as e:
        print(f"Erreur de connexion MongoDB: {e}")
        return None

@dataclass
class Page:
    date: Optional[str]
    title: str
    link: str
    description: str
    content: str
    author: Optional[str]
    image_url: Optional[str]

def save_page_to_mongodb(page_data: Page):
    client = get_mongo_client()
    if not client:
        print("Impossible de se connecter à MongoDB")
        return False
        
    try:
        db = client["mydb"]
        collection = db["lab"]
        data_dict = {
            "date": page_data.date,
            "title": page_data.title,
            "link": page_data.link,
            "description": page_data.description,
            "content": page_data.content,
            "author": page_data.author,
            "image_url": page_data.image_url,
        }
        collection.update_one(
            {"link": page_data.link},
            {"$set": data_dict},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Erreur lors de la sauvegarde MongoDB: {e}")
        return False
    finally:
        client.close()

###############################
# Fonctions MySQL (Feedback) - inchangées
###############################
def get_mysql_connection():
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", 3306))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "bd_veille")

    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        db=database,
        port=port,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

def save_feedback_to_mysql(data):
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO feedback (
                    date, onglet, unite_temps,
                    titre_reponse, contenu_reponse,
                    reponse_urls, avis_utilisateur
                )
                VALUES (
                    %s, %s, %s,
                    %s, %s,
                    %s, %s
                )
            """
            cursor.execute(sql, (
                data["Date"],
                data["Onglet"],
                data["Unité de temps"],
                data["Titre réponse"],
                data["Contenu réponse"],
                data["Réponse URL(s)"],
                data["Avis utilisateur"]
            ))
        conn.commit()
    except Exception as e:
        print(f"Erreur lors de l'insertion du feedback: {e}")
    finally:
        conn.close()

###############################
# Fonctions Google Search (inchangées)
###############################
def google_search(query, num_results=10, languages=None, time_unit=None, time_value=None,
                  exclude_ads=False, exclude_professional=False, target_press=False,
                  exclude_jobs=False, exclude_training=False):
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={GOOGLE_API_KEY}&cx={CSE_ID}&num={num_results}"
    if languages:
        lang_param = " OR ".join([f"lang_{lang}" for lang in languages])
        url += f"&lr={lang_param}"
    if time_unit and time_value:
        time_value_days = time_value * 30 if time_unit == "mois" else time_value * 365
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=time_value_days)).strftime("%Y%m%d")
        url += f"&sort=date:r:{start_date}:{end_date}"
    # Filtres fictifs (à adapter en vrai projet)
    if exclude_ads:
        url += "&filter=0"
    if exclude_professional:
        url += "&filter=1"
    if target_press:
        url += "&filter=2"
    if exclude_jobs:
        url += "&filter=3"
    if exclude_training:
        url += "&filter=4"

    response = requests.get(url)
    data = response.json()
    urls = [item["link"] for item in data.get("items", [])]
    return urls

###############################
# Fonctions de scraping (inchangées)
###############################
def clean_date(date_string: str) -> Optional[str]:
    try:
        return date_string.strip()
    except AttributeError:
        return None

def get_first_valid_xpath(tree, xpaths):
    for path in xpaths:
        result = tree.xpath(path)
        if result:
            return result[0].strip() if isinstance(result[0], str) else result[0]
    return None

def get_first_valid_css(soup, css_selectors):
    for selector in css_selectors:
        result = soup.select_one(selector)
        if result:
            return result.get_text(strip=True) if result.get_text else result.get("content", "").strip()
    return None

def scrape_page(url: str) -> Optional[Page]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "fr-FR,fr;q=0.9",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logging.error(f"Erreur HTTP {response.status_code} pour {url}")
            return None

        soup = BeautifulSoup(response.content, "lxml")
        html_tree = lxml_html.fromstring(str(soup))

        xpaths = {
            "title": ["//h1/text()", "//meta[@property='og:title']/@content", "//title/text()"],
            "content": ["//article//p//text()", "//div[contains(@class, 'content')]//p//text()", "//p//text()"],
            "author": ["//meta[@name='author']/@content", "//span[contains(@class, 'author')]//text()"],
            "date": ["//time/@datetime", "//meta[@property='article:published_time']/@content"],
            "description": ["//meta[@name='description']/@content", "//meta[@property='og:description']/@content"],
            "image_url": [
                "//meta[@property='og:image']/@content",
                "//img[@class='featured-image']/@src",
                "//div[contains(@class, 'td-module-thumb')]//img/@src",
                "//img[contains(@class, 'entry-thumb')]/@src"
            ],
        }
        css_selectors = {
            "title": ["h1", "meta[property='og:title']", "title"],
            "content": ["article p", "div.content p", "p"],
            "author": ["meta[name='author']", "span.author"],
            "date": ["time", "meta[property='article:published_time']"],
            "description": ["meta[name='description']", "meta[property='og:description']"],
            "image_url": ["meta[property='og:image']", "img.featured-image", "div.td-module-thumb img", "img.entry-thumb"],
        }

        title = get_first_valid_xpath(html_tree, xpaths["title"]) or get_first_valid_css(soup, css_selectors["title"]) or "Titre non trouvé"
        content_elements = html_tree.xpath("|".join(xpaths["content"])) or soup.select("|".join(css_selectors["content"]))
        content = " ".join([c.strip() for c in content_elements if len(c.strip()) > 50]) or "Contenu non trouvé"
        author = get_first_valid_xpath(html_tree, xpaths["author"]) or get_first_valid_css(soup, css_selectors["author"]) or "Auteur non spécifié"
        date = get_first_valid_xpath(html_tree, xpaths["date"]) or get_first_valid_css(soup, css_selectors["date"])
        date = clean_date(date) if date else None
        description = get_first_valid_xpath(html_tree, xpaths["description"]) or get_first_valid_css(soup, css_selectors["description"]) or "Description non trouvée"
        image_url = get_first_valid_xpath(html_tree, xpaths["image_url"]) or get_first_valid_css(soup, css_selectors["image_url"]) or None
        if image_url and not image_url.startswith("http"):
            image_url = urljoin(url, image_url)

        return Page(
            date=date,
            title=title,
            link=url,
            description=description,
            content=content,
            author=author,
            image_url=image_url,
        )

    except Exception as e:
        logging.error(f"Erreur lors du scraping de {url} : {e}")
        return None

def is_valid_image_url(url):
    try:
        response = requests.head(url, allow_redirects=True)
        return response.status_code == 200 and response.headers.get("content-type", "").startswith("image/")
    except requests.RequestException:
        return False

###############################
# Fonctions de génération (inchangées, adaptation Ollama)
###############################
def generate_summary(article_text: str, system_prompt: str, user_prompt: str) -> str:
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = ollama.chat(
                model='llama3.2:3b', # Changez pour llama2 qui est plus stable
                messages=messages,
                api_base='http://ollama:11434'  # Spécifiez explicitement l'URL
            )
            return response['message']['content']
        except Exception as e:
            if attempt == max_retries - 1:
                return f"Erreur lors de l'appel à l'API après {max_retries} tentatives : {str(e)}"
            print(f"Tentative {attempt + 1} échouée : {e}")
            time.sleep(retry_delay)

def generate_answer(question: str, context: str) -> str:
    try:
        messages = [
            {
                "role": "system",
                "content": "Vous êtes un assistant expert en veille stratégique. Votre tâche est de répondre aux questions basées sur les articles fournis."
            },
            {
                "role": "user",
                "content": f"Question : {question}\nContexte : {context}"
            }
        ]
        response = ollama.chat(model='llama3.2:3b', messages=messages)
        return response['message']['content']
    except Exception as e:
        return f"Erreur lors de l'appel à l'API : {str(e)}"

###############################
# Fonctions de création de PDF (inchangées)
###############################
def create_file(summary, article_text, system_prompt, user_prompt, url, title):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], fontSize=18, alignment=1)
    subtitle_style = ParagraphStyle("SubtitleStyle", parent=styles["Heading2"], fontSize=14, alignment=1)
    normal_style = ParagraphStyle("NormalStyle", parent=styles["Normal"], fontSize=10, leading=12)
    body_style = ParagraphStyle("BodyStyle", parent=styles["Normal"], fontSize=10, leading=14)

    def format_text(text):
        return re.sub(r"(###|-)", r"<br/>", text)

    elements = []
    elements.append(Paragraph("<b>Synthèse d'articles</b>", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>URL :</b> <a href='{url}'>{url}</a>", normal_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Titre :</b> {title}", normal_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>System Prompt :</b>", subtitle_style))
    elements.append(Paragraph(format_text(system_prompt), body_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>User Prompt :</b>", subtitle_style))
    elements.append(Paragraph(format_text(user_prompt), body_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Synthèse :</b>", subtitle_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(format_text(summary), body_style))
    elements.append(Spacer(1, 12))
    doc.build(elements)

    buffer.seek(0)
    return buffer.getvalue()

###############################
# Fonctions de persistance : via API FastAPI
###############################
def get_hash(input_data):
    return hashlib.md5(input_data.encode("utf-8")).hexdigest()

########## Sources ##########
def load_default_sources():
    api_url = os.getenv("API_URL", "http://api:8000")
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            resp = requests.get(f"{api_url}/sources", timeout=5)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                print(f"Erreur finale après {max_retries} tentatives : {e}")
                return []
            print(f"Tentative {attempt + 1} échouée : {e}")
            time.sleep(retry_delay)

def save_default_sources(sources):
    try:
        # Filtrer les lignes vides
        clean_sources = [s.strip() for s in sources if s.strip()]
        
        resp = requests.post(
            "http://api:8000/sources", 
            json=clean_sources,
            timeout=10  # Ajouter un timeout
        )
        
        if resp.status_code != 200:
            error_detail = resp.json().get('detail', 'Erreur inconnue')
            raise Exception(f"Erreur API ({resp.status_code}): {error_detail}")
            
        resp.raise_for_status()
        return resp.json()
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Erreur de connexion à l'API: {str(e)}")
    except Exception as e:
        raise Exception(f"Erreur lors de la sauvegarde des sources: {str(e)}")

########## Keywords ##########
def load_default_keywords():
    try:
        resp = requests.get("http://api:8000/keywords")  # Modifié
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Erreur lors du chargement des keywords: {e}")
        return []

def save_default_keywords(keywords):
    try:
        resp = requests.post("http://api:8000/keywords", json=keywords)  # Modifié
        resp.raise_for_status()
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des keywords: {e}")

def load_filters():
    try:
        resp = requests.get("http://api:8000/filters")  # Modifié
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Erreur lors du chargement des filters: {e}")
        return {
            "exclude_ads": False,
            "exclude_professional": False,
            "target_press": False,
            "time_unit": "mois",
            "time_value": 1,
            "exclude_jobs": False,
            "exclude_training": False,
        }

def save_filters(filters):
    """
    Sauvegarde l'objet filters (id=1) via l'API (POST /filters).
    """
    try:
        resp = requests.post("http://127.0.0.1:8000/filters", json=filters)
        resp.raise_for_status()
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des filters: {e}")

########## Cache (results, summaries...) ##########
def check_and_load_results(input_data, result_key):
    """
    Vérifie en base (via l'API) si un cache existe pour (input_hash, result_key).
    Si oui, le charge dans st.session_state[result_key].
    Retourne True si on a trouvé, False sinon.
    """
    input_hash = get_hash(input_data)
    try:
        resp = requests.get("http://127.0.0.1:8000/cache", params={"input_hash": input_hash, "result_key": result_key})
        if resp.status_code == 200:
            data = resp.json()
            # data = {"data": "..."} => on doit le charger en JSON
            st.session_state[result_key] = json.loads(data["data"])
            return True
        else:
            return False
    except Exception as e:
        print(f"Erreur lors de la vérification/chargement du cache: {e}")
        return False

def save_results_to_file(input_data, result_key, data):
    """
    Sauvegarde un item de cache (JSON) via l'API (POST /cache).
    """
    input_hash = get_hash(input_data)
    try:
        # On convertit data en JSON
        data_json = json.dumps(data, ensure_ascii=False)
        payload = {
            "input_hash": input_hash,
            "result_key": result_key,
            "data": data_json
        }
        resp = requests.post("http://127.0.0.1:8000/cache", json=payload)
        resp.raise_for_status()
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du cache: {e}")
