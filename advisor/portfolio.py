"""포트폴리오 상태 관리 - state.json 기반"""
import json
import os
from datetime import datetime, date
from pathlib import Path

STATE_PATH = Path(__file__).parent / "state.json"


DEFAULT_STATE = {
    "meta": {
        "version": 1,
        "last_updated": None,
    },
    "swing": {
        "account": "",
        "cash": 0,
        "holdings": [],
    },
    "isa": {
        "account": "",
        "note": "",
        "holdings": [],
    },
    "us_stocks": {
        "account": "",
        "note": "",
        "holdings": [],
        "usd_balance": 0,
        "krw_balance": 0,
        "total_value_krw": 0,
        "total_pnl_krw": 0,
        "total_pnl_pct": 0,
        "last_updated": None,
    },
    "rules": {
        "swing": {
            "price_range": [15000, 50000],
            "min_volume_ratio": 0.5,
            "max_daily_change": 5,
            "require_macd_positive": True,
            "require_above_ma20": True,
            "rsi_range": [40, 70],
            "max_positions": 2,
            "max_position_pct": 60,
            "stop_loss_pct": -4,
            "targets_pct": [5, 10, 15],
            "max_holding_days": 14,
            "alert_holding_days": 7,
        },
    },
}


def load_state() -> dict:
    """state.json 로드. 없으면 DEFAULT로 생성."""
    if not STATE_PATH.exists():
        save_state(DEFAULT_STATE)
        return DEFAULT_STATE
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Warning] state.json 로드 실패, 기본값 사용: {e}")
        return DEFAULT_STATE


def save_state(state: dict):
    """state.json 저장"""
    state.setdefault("meta", {})
    state["meta"]["last_updated"] = datetime.now().isoformat()
    STATE_PATH.parent.mkdir(exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_swing_holdings(include_closed: bool = False) -> list:
    """스윙 보유 종목 리스트. qty 0 또는 status='closed' 종목은 기본 제외."""
    holdings = load_state().get("swing", {}).get("holdings", [])
    if include_closed:
        return holdings
    return [
        h for h in holdings
        if h.get("qty", 0) > 0 and h.get("status") != "closed"
    ]


def get_swing_cash() -> int:
    """스윙 예수금"""
    return load_state().get("swing", {}).get("cash", 0)


def get_rules() -> dict:
    """스윙 규칙"""
    return load_state().get("rules", {}).get("swing", {})


def update_swing_cash(new_cash: int):
    state = load_state()
    state["swing"]["cash"] = new_cash
    save_state(state)


def add_swing_holding(holding: dict):
    state = load_state()
    state["swing"]["holdings"].append(holding)
    save_state(state)


def remove_swing_holding(ticker: str):
    state = load_state()
    state["swing"]["holdings"] = [
        h for h in state["swing"]["holdings"] if h["ticker"] != ticker
    ]
    save_state(state)


def update_swing_holding(ticker: str, updates: dict):
    state = load_state()
    for h in state["swing"]["holdings"]:
        if h["ticker"] == ticker:
            h.update(updates)
            break
    save_state(state)


def days_held(entry_date: str) -> int:
    """진입일 기준 경과 거래일 수 (영업일 기준 근사)"""
    try:
        entry = datetime.strptime(entry_date, "%Y-%m-%d").date()
        today = date.today()
        delta = (today - entry).days
        # 주말 제외 근사 (정확하진 않음)
        weekends = (delta // 7) * 2
        return max(0, delta - weekends)
    except Exception:
        return 0
