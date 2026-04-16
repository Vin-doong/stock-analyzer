"""시장 상황(시황) 판별 모듈

지수 데이터를 기반으로 현재 시장이 강세/중립/약세인지 판별하고,
약세장일 때 스크리닝 점수에 페널티를 부여합니다.
"""
import pandas as pd
from data import cache
from config import CACHE_TTL


def get_market_regime(market: str) -> dict:
    """시장 상황 판별

    Returns:
        {
            "regime": "강세" | "중립" | "약세",
            "score_adjustment": 0 ~ -15 (약세일수록 큰 감점),
            "details": { ... 판단 근거 },
        }
    """
    cache_key = f"regime:{market}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 시장별 지수 코드
    if market in ("KOSPI", "KOSDAQ"):
        index_code = "KS11" if market == "KOSPI" else "KQ11"
        from data.fetcher_kr import get_index_data
    else:
        index_code = "^GSPC" if market == "NYSE" else "^IXIC"
        from data.fetcher_us import get_index_data

    try:
        df = get_index_data(index_code, days=90)
        if df is None or df.empty or len(df) < 20:
            return {"regime": "중립", "score_adjustment": 0, "details": {"error": "지수 데이터 부족"}}
    except Exception:
        return {"regime": "중립", "score_adjustment": 0, "details": {"error": "지수 조회 실패"}}

    result = _analyze_regime(df)
    cache.set(cache_key, result, 3600)  # 1시간 캐시
    return result


def _analyze_regime(df: pd.DataFrame) -> dict:
    """지수 DataFrame으로 시장 상황 분석"""
    signals = 0  # 양수=강세, 음수=약세
    details = {}

    close = df["Close"]
    last_close = close.iloc[-1]

    # 1. 20일 이동평균 대비
    ma20 = close.rolling(20).mean().iloc[-1]
    if not pd.isna(ma20):
        pct_vs_ma20 = (last_close / ma20 - 1) * 100
        details["지수vs20일선"] = f"{pct_vs_ma20:+.1f}%"
        if pct_vs_ma20 > 2:
            signals += 1
        elif pct_vs_ma20 < -2:
            signals -= 1

    # 2. 60일 이동평균 대비
    if len(close) >= 60:
        ma60 = close.rolling(60).mean().iloc[-1]
        if not pd.isna(ma60):
            pct_vs_ma60 = (last_close / ma60 - 1) * 100
            details["지수vs60일선"] = f"{pct_vs_ma60:+.1f}%"
            if pct_vs_ma60 > 3:
                signals += 1
            elif pct_vs_ma60 < -3:
                signals -= 1

    # 3. 최근 20일 수익률
    if len(close) >= 21:
        ret_20d = (last_close / close.iloc[-21] - 1) * 100
        details["20일수익률"] = f"{ret_20d:+.1f}%"
        if ret_20d > 3:
            signals += 1
        elif ret_20d < -5:
            signals -= 2  # 급락은 더 강하게 반영
        elif ret_20d < -3:
            signals -= 1

    # 4. 고점 대비 하락폭 (최근 60일 고점 기준)
    if len(close) >= 60:
        peak = close.tail(60).max()
        drawdown = (last_close / peak - 1) * 100
        details["60일고점대비"] = f"{drawdown:+.1f}%"
        if drawdown < -10:
            signals -= 2  # 10% 이상 하락 = 강한 약세
        elif drawdown < -5:
            signals -= 1

    # 5. MA20 기울기 (추세 방향)
    if len(close) >= 25:
        ma20_series = close.rolling(20).mean()
        ma20_now = ma20_series.iloc[-1]
        ma20_5ago = ma20_series.iloc[-6]
        if not pd.isna(ma20_now) and not pd.isna(ma20_5ago) and ma20_5ago != 0:
            slope = (ma20_now - ma20_5ago) / ma20_5ago * 100
            details["20일선기울기"] = f"{slope:+.2f}%"
            if slope > 0.5:
                signals += 1
            elif slope < -0.5:
                signals -= 1

    # 판정
    if signals >= 2:
        regime = "강세"
        adjustment = 0
    elif signals <= -2:
        regime = "약세"
        adjustment = max(-15, signals * 3)  # 약세 정도에 비례 (최대 -15점)
    else:
        regime = "중립"
        adjustment = 0

    details["종합신호"] = signals
    details["점수보정"] = adjustment

    return {
        "regime": regime,
        "score_adjustment": adjustment,
        "details": details,
    }
