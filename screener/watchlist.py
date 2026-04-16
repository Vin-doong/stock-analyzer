"""관심종목 관리 (JSON 파일 기반)"""
import json
import os

WATCHLIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache_db", "watchlist.json")


def _load() -> list[dict]:
    if not os.path.exists(WATCHLIST_PATH):
        return []
    try:
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(items: list[dict]):
    os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def get_all() -> list[dict]:
    return _load()


def add(ticker: str, name: str, market: str):
    items = _load()
    if any(i["ticker"] == ticker for i in items):
        return
    items.append({"ticker": ticker, "name": name, "market": market})
    _save(items)


def remove(ticker: str):
    items = _load()
    items = [i for i in items if i["ticker"] != ticker]
    _save(items)


def exists(ticker: str) -> bool:
    return any(i["ticker"] == ticker for i in _load())
