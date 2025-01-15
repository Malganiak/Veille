# main.py

import os
import json
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel
import pymysql
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

##############
# Connexion MySQL
##############
def get_mysql_connection():
    """
    Initialise la connexion MySQL.
    """
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

##############
# Modèles Pydantic
##############
class SourceItem(BaseModel):
    value: str

class KeywordItem(BaseModel):
    value: str

class Filters(BaseModel):
    exclude_ads: bool
    exclude_professional: bool
    target_press: bool
    time_unit: str
    time_value: int
    exclude_jobs: bool
    exclude_training: bool
class CacheItem(BaseModel):
    input_hash: str
    result_key: str
    data: str  # Le contenu JSON des résumés, par exemple

##############
# Endpoints : Sources
##############
@app.post("/sources")
async def save_sources(sources: List[str]):
    try:
        # Filtrer les URLs vides ou invalides
        valid_sources = [s.strip() for s in sources if s.strip()]
        
        # Connexion à MySQL
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                # Supprimer les anciennes sources
                cursor.execute("TRUNCATE TABLE sources")
                
                # Insérer les nouvelles sources
                if valid_sources:
                    sql = "INSERT INTO sources (url) VALUES (%s)"
                    cursor.executemany(sql, [(url,) for url in valid_sources])
            
            conn.commit()
            return {"message": "Sources sauvegardées avec succès", "count": len(valid_sources)}
            
        except Exception as e:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la sauvegarde en base de données: {str(e)}"
            )
        finally:
            conn.close()
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur serveur: {str(e)}"
        )
@app.get("/sources")
async def get_sources() -> List[str]:
    try:
        conn = get_mysql_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT url FROM sources")
                results = cursor.fetchall()
                return [row['url'] for row in results]
        finally:
            conn.close()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des sources: {str(e)}"
        )

##############
# Endpoints : Keywords
##############
@app.get("/keywords", response_model=List[str])
def get_keywords():
    """
    Récupère la liste de tous les mots-clés (valeurs) dans la table keywords.
    """
    conn = get_mysql_connection()
    results = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT value FROM keywords")
            rows = cursor.fetchall()
            results = [row["value"] for row in rows]
    finally:
        conn.close()
    return results

@app.post("/keywords")
def save_keywords(keywords: List[str]):
    """
    Écrase tous les mots-clés existants et insère la nouvelle liste.
    """
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE keywords")
            for k in keywords:
                cursor.execute("INSERT INTO keywords (value) VALUES (%s)", (k,))
        conn.commit()
    finally:
        conn.close()
    return {"message": "Keywords sauvegardés avec succès."}
##############
# Endpoints : Filters
##############
@app.get("/filters", response_model=Filters)
def get_filters():
    """
    Récupère l'objet filters (id=1).
    """
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM filters WHERE id=1")
            row = cursor.fetchone()
            if not row:
                # S'il n'existe pas encore, on le crée par défaut
                default_filters = {
                    "exclude_ads": False,
                    "exclude_professional": False,
                    "target_press": False,
                    "time_unit": "mois",
                    "time_value": 1,
                    "exclude_jobs": False,
                    "exclude_training": False
                }
                cursor.execute("""
                    INSERT INTO filters (id, exclude_ads, exclude_professional, target_press,
                                         time_unit, time_value, exclude_jobs, exclude_training)
                    VALUES (1, 0, 0, 0, 'mois', 1, 0, 0)
                """)
                conn.commit()
                return Filters(**default_filters)
            return Filters(
                exclude_ads=bool(row["exclude_ads"]),
                exclude_professional=bool(row["exclude_professional"]),
                target_press=bool(row["target_press"]),
                time_unit=row["time_unit"],
                time_value=row["time_value"],
                exclude_jobs=bool(row["exclude_jobs"]),
                exclude_training=bool(row["exclude_training"])
            )
    finally:
        conn.close()
@app.post("/filters")
def save_filters(filters: Filters):
    """
    Écrase les filtres (id=1).
    """
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                REPLACE INTO filters (id, exclude_ads, exclude_professional, target_press,
                                      time_unit, time_value, exclude_jobs, exclude_training)
                VALUES (1, %s, %s, %s, %s, %s, %s, %s)
            """, (
                int(filters.exclude_ads),
                int(filters.exclude_professional),
                int(filters.target_press),
                filters.time_unit,
                filters.time_value,
                int(filters.exclude_jobs),
                int(filters.exclude_training)
            ))
        conn.commit()
    finally:
        conn.close()
    return {"message": "Filters sauvegardés avec succès."}

##############
# Endpoints : Cache (résultats, résumés, etc.)
##############
@app.get("/cache")
def get_cache_item(input_hash: str, result_key: str):
    """
    Récupère un enregistrement de cache correspondant à (input_hash, result_key).
    """
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT data FROM cache WHERE input_hash=%s AND result_key=%s
            """, (input_hash, result_key))
            row = cursor.fetchone()
            if row:
                return {"data": row["data"]}
            else:
                raise HTTPException(status_code=404, detail="Pas de résultats en cache pour ces paramètres.")
    finally:
        conn.close()
@app.post("/cache")
def save_cache_item(item: CacheItem):
    """
    Sauvegarde ou met à jour un enregistrement de cache : (input_hash, result_key, data).
    """
    conn = get_mysql_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                REPLACE INTO cache (input_hash, result_key, data)
                VALUES (%s, %s, %s)
            """, (item.input_hash, item.result_key, item.data))
        conn.commit()
    finally:
        conn.close()
    return {"message": "Cache sauvegardé avec succès."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}