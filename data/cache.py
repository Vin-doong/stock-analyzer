"""SQLite 기반 TTL 캐시"""
import sqlite3
import pickle
import time
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache_db", "stock_cache.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cache "
        "(key TEXT PRIMARY KEY, data BLOB, created_at REAL, ttl INTEGER)"
    )
    return conn


def get(key: str):
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT data, created_at, ttl FROM cache WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        data, created_at, ttl = row
        if time.time() - created_at > ttl:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
            return None
        return pickle.loads(data)
    finally:
        conn.close()


def set(key: str, data, ttl: int = 3600):
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, data, created_at, ttl) VALUES (?, ?, ?, ?)",
            (key, pickle.dumps(data), time.time(), ttl),
        )
        conn.commit()
    finally:
        conn.close()


def clear():
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM cache")
        conn.commit()
    finally:
        conn.close()
