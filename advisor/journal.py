"""매매 일지 - 감정 관리 + 학습 누적"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

JOURNAL_PATH = Path(__file__).parent / "journal.json"


def _load() -> list:
    if not JOURNAL_PATH.exists():
        return []
    try:
        with open(JOURNAL_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(entries: list):
    JOURNAL_PATH.parent.mkdir(exist_ok=True)
    with open(JOURNAL_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def log_trade(action: str, ticker: str, name: str, qty: int, price: int,
              reason: str, emotion: Optional[str] = None,
              notes: Optional[str] = None):
    """매매 기록

    Args:
        action: "buy" | "sell" | "stop_loss" | "target_hit"
        ticker: 종목 코드
        name: 종목명
        qty: 수량
        price: 가격
        reason: 매매 이유 (필수)
        emotion: 감정 상태 (optional: "calm", "fomo", "fear", "greed", "revenge")
        notes: 추가 메모
    """
    entries = _load()
    entry = {
        "id": len(entries) + 1,
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "ticker": ticker,
        "name": name,
        "qty": qty,
        "price": price,
        "total": qty * price,
        "reason": reason,
        "emotion": emotion,
        "notes": notes,
    }
    entries.append(entry)
    _save(entries)
    return entry


def get_all() -> list:
    return _load()


def get_by_ticker(ticker: str) -> list:
    return [e for e in _load() if e["ticker"] == ticker]


def get_recent(n: int = 10) -> list:
    entries = _load()
    return sorted(entries, key=lambda x: x["timestamp"], reverse=True)[:n]


def analyze_patterns() -> dict:
    """매매 패턴 분석 - 감정 매매 경향 파악"""
    entries = _load()
    if not entries:
        return {"total": 0}

    total = len(entries)
    by_action = {}
    by_emotion = {}

    for e in entries:
        by_action[e["action"]] = by_action.get(e["action"], 0) + 1
        if e.get("emotion"):
            by_emotion[e["emotion"]] = by_emotion.get(e["emotion"], 0) + 1

    # 감정 매매 비율
    emotional = sum(
        count for emotion, count in by_emotion.items()
        if emotion in ("fomo", "fear", "greed", "revenge")
    )
    calm = by_emotion.get("calm", 0)

    return {
        "total_trades": total,
        "by_action": by_action,
        "by_emotion": by_emotion,
        "emotional_trades": emotional,
        "calm_trades": calm,
        "emotional_ratio": emotional / total * 100 if total > 0 else 0,
    }
