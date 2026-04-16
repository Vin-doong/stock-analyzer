"""전역 설정값"""
import os
from enum import Enum

# 투자 스타일
class TradingStyle(str, Enum):
    DAY = "단타"
    SWING = "스윙"
    LONG = "중장기"

# 시장
class Market(str, Enum):
    KOSPI = "KOSPI"
    KOSDAQ = "KOSDAQ"
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"

# 캐시 TTL (초)
CACHE_TTL = {
    "intraday": 300,       # 5분
    "daily": 3600,         # 1시간
    "fundamental": 86400,  # 24시간
    "stock_list": 86400,   # 24시간
    "ai_analysis": 1800,   # 30분
}

# 스타일별 점수 가중치
SCORING_WEIGHTS = {
    TradingStyle.DAY: {
        "rsi": 0.20, "macd": 0.15, "bollinger": 0.20,
        "volume": 0.25, "ma_trend": 0.10, "per_pbr": 0.0,
        "roe_growth": 0.0, "revenue": 0.0, "momentum": 0.10,
    },
    TradingStyle.SWING: {
        "rsi": 0.15, "macd": 0.20, "bollinger": 0.15,
        "volume": 0.10, "ma_trend": 0.20, "per_pbr": 0.05,
        "roe_growth": 0.10, "revenue": 0.05, "momentum": 0.0,
    },
    TradingStyle.LONG: {
        "rsi": 0.05, "macd": 0.10, "bollinger": 0.05,
        "volume": 0.05, "ma_trend": 0.15, "per_pbr": 0.20,
        "roe_growth": 0.25, "revenue": 0.15, "momentum": 0.0,
    },
}

# 신호 임계값
SIGNAL_THRESHOLDS = {
    "strong_buy": 80,
    "buy": 65,
    "hold_low": 40,
    "sell": 25,
    "strong_sell": 15,
}

# AI Provider 설정 ("claude" 또는 "openai")
AI_PROVIDER = os.environ.get("AI_PROVIDER", "claude")

# Claude API 설정
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_RESPONSE = 1024

# OpenAI API 설정
OPENAI_MODEL = "gpt-4o"
OPENAI_MAX_RESPONSE = 1024

# 스크리닝 설정
SCREEN_SIZES = {
    "빠른 스캔 (50개)": 50,
    "일반 스캔 (100개)": 100,
    "정밀 스캔 (200개)": 200,
    "전체 스캔 (500개)": 500,
}
DEFAULT_SCREEN_SIZE = 100
DEFAULT_TOP_N = 20
SCAN_MAX_WORKERS = 8  # 동시 분석 스레드 수 (높을수록 빠르지만 API 부하 증가)
