"""스타일별 종합 점수 엔진"""
import pandas as pd
from datetime import datetime
from config import TradingStyle, SCORING_WEIGHTS, SIGNAL_THRESHOLDS
from data.models import ScoreResult
from analysis.technical import (
    add_all_indicators, calc_rsi_score, calc_macd_score,
    calc_bollinger_score, calc_volume_score, calc_ma_trend_score,
    calc_momentum_score, get_technical_summary, is_downtrend,
)
from analysis.fundamental import get_fundamental_scores


def _get_signal(score: float) -> str:
    if score >= SIGNAL_THRESHOLDS["strong_buy"]:
        return "강력매수"
    elif score >= SIGNAL_THRESHOLDS["buy"]:
        return "매수"
    elif score >= SIGNAL_THRESHOLDS["hold_low"]:
        return "관망"
    elif score >= SIGNAL_THRESHOLDS["sell"]:
        return "매도"
    else:
        return "강력매도"


def score_stock(
    ticker: str,
    name: str,
    df: pd.DataFrame,
    style: TradingStyle,
    fundamental: dict | None = None,
) -> ScoreResult:
    """종목 종합 점수 산출"""
    weights = SCORING_WEIGHTS[style]

    # 기술적 지표 계산
    df = add_all_indicators(df)
    if df.empty:
        return ScoreResult(
            ticker=ticker, name=name, style=style.value,
            composite_score=0, category_scores={}, signal="데이터없음", confidence=0,
        )

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last

    # 각 지표별 점수
    category_scores = {
        "rsi": calc_rsi_score(last.get("RSI")),
        "macd": calc_macd_score(last.get("MACD_Hist"), prev.get("MACD_Hist")),
        "bollinger": calc_bollinger_score(last.get("BB_PctB")),
        "volume": calc_volume_score(last.get("Volume_Ratio")),
        "ma_trend": calc_ma_trend_score(df),
        "momentum": calc_momentum_score(df),
    }

    # 재무 점수 (있는 경우)
    if fundamental:
        fund_scores = get_fundamental_scores(fundamental)
        category_scores["per_pbr"] = fund_scores.get("per_pbr", 50)
        category_scores["roe_growth"] = fund_scores.get("roe_growth", 50)
        category_scores["revenue"] = fund_scores.get("revenue", 50)
    else:
        category_scores["per_pbr"] = 50
        category_scores["roe_growth"] = 50
        category_scores["revenue"] = 50

    # 하락 추세 보정: RSI/볼린저의 과매도 신호가 반등이 아닌 추세 하락일 수 있음
    if is_downtrend(df):
        # RSI 과매도 점수를 중립 방향으로 보정 (높은 점수 → 깎기)
        if category_scores["rsi"] > 70:
            category_scores["rsi"] = max(50, category_scores["rsi"] - 20)
        # 볼린저 하단 이탈 점수도 보정
        if category_scores["bollinger"] > 70:
            category_scores["bollinger"] = max(50, category_scores["bollinger"] - 20)

    # 가중 점수 계산
    composite = 0
    total_weight = 0
    for key, weight in weights.items():
        if weight > 0 and key in category_scores:
            composite += category_scores[key] * weight
            total_weight += weight

    composite = composite / total_weight if total_weight > 0 else 50

    # 신뢰도 (데이터 완전성 기반)
    available = sum(1 for k, w in weights.items() if w > 0 and k in category_scores
                    and category_scores[k] != 50)
    total = sum(1 for k, w in weights.items() if w > 0)
    confidence = (available / total * 100) if total > 0 else 0

    return ScoreResult(
        ticker=ticker,
        name=name,
        style=style.value,
        composite_score=round(composite, 1),
        category_scores={k: round(v, 1) for k, v in category_scores.items()},
        signal=_get_signal(composite),
        confidence=round(confidence, 1),
    )
