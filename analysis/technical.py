"""기술적 지표 계산 (ta 라이브러리 활용)"""
import pandas as pd
import ta
import numpy as np


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """모든 기술적 지표를 DataFrame에 추가"""
    if df.empty or len(df) < 20:
        return df

    df = df.copy()

    # 이동평균선
    for w in [5, 10, 20, 60, 120]:
        if len(df) >= w:
            df[f"MA{w}"] = ta.trend.sma_indicator(df["Close"], window=w)
            df[f"EMA{w}"] = ta.trend.ema_indicator(df["Close"], window=w)

    # RSI
    df["RSI"] = ta.momentum.rsi(df["Close"], window=14)

    # MACD
    macd = ta.trend.MACD(df["Close"], window_slow=26, window_fast=12, window_sign=9)
    df["MACD"] = macd.macd()
    df["MACD_Signal"] = macd.macd_signal()
    df["MACD_Hist"] = macd.macd_diff()

    # 볼린저밴드
    bb = ta.volatility.BollingerBands(df["Close"], window=20, window_dev=2)
    df["BB_Upper"] = bb.bollinger_hband()
    df["BB_Middle"] = bb.bollinger_mavg()
    df["BB_Lower"] = bb.bollinger_lband()
    df["BB_PctB"] = bb.bollinger_pband()

    # 거래량 분석
    if "Volume" in df.columns:
        df["Volume_MA20"] = df["Volume"].rolling(window=20).mean()
        df["Volume_Ratio"] = df["Volume"] / df["Volume_MA20"].replace(0, np.nan)
        df["OBV"] = ta.volume.on_balance_volume(df["Close"], df["Volume"])

    # 스토캐스틱
    stoch = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"])
    df["Stoch_K"] = stoch.stoch()
    df["Stoch_D"] = stoch.stoch_signal()

    # ATR (변동성)
    df["ATR"] = ta.volatility.average_true_range(df["High"], df["Low"], df["Close"], window=14)

    # ADX (추세 강도)
    adx = ta.trend.ADXIndicator(df["High"], df["Low"], df["Close"], window=14)
    df["ADX"] = adx.adx()
    df["DI_Plus"] = adx.adx_pos()
    df["DI_Minus"] = adx.adx_neg()

    return df


def calc_rsi_score(rsi: float) -> float:
    """RSI 기반 점수 (0~100)"""
    if pd.isna(rsi):
        return 50
    if rsi < 20:
        return 95
    elif rsi < 30:
        return 85
    elif rsi < 40:
        return 70
    elif rsi < 60:
        return 50
    elif rsi < 70:
        return 30
    elif rsi < 80:
        return 15
    else:
        return 5


def calc_macd_score(hist: float, prev_hist: float) -> float:
    """MACD 히스토그램 기반 점수"""
    if pd.isna(hist) or pd.isna(prev_hist):
        return 50
    if hist > 0 and hist > prev_hist:
        return 90  # 양수 & 증가
    elif hist > 0 and hist <= prev_hist:
        return 65  # 양수 & 감소
    elif hist < 0 and hist > prev_hist:
        return 40  # 음수 & 증가 (반등 시그널)
    else:
        return 10  # 음수 & 감소


def calc_bollinger_score(pctb: float) -> float:
    """볼린저밴드 %B 기반 점수"""
    if pd.isna(pctb):
        return 50
    if pctb < 0:
        return 90  # 하단 이탈 (과매도)
    elif pctb < 0.2:
        return 80
    elif pctb < 0.4:
        return 65
    elif pctb < 0.6:
        return 50
    elif pctb < 0.8:
        return 35
    elif pctb < 1.0:
        return 20
    else:
        return 10  # 상단 이탈 (과매수)


def calc_volume_score(volume_ratio: float) -> float:
    """거래량 비율 기반 점수"""
    if pd.isna(volume_ratio):
        return 50
    if volume_ratio > 3.0:
        return 95
    elif volume_ratio > 2.0:
        return 80
    elif volume_ratio > 1.5:
        return 65
    elif volume_ratio > 1.0:
        return 50
    elif volume_ratio > 0.5:
        return 30
    else:
        return 15


def calc_ma_trend_score(df: pd.DataFrame) -> float:
    """이동평균 추세 점수 (배열 상태 반영)"""
    if df.empty or len(df) < 60:
        return 50

    last = df.iloc[-1]
    close = last["Close"]
    score = 50

    # 주요 MA 위/아래 여부
    for ma_col, weight in [("MA5", 5), ("MA20", 10), ("MA60", 15)]:
        if ma_col in df.columns and not pd.isna(last.get(ma_col)):
            if close > last[ma_col]:
                score += weight
            else:
                score -= weight

    # 골든크로스/데드크로스 확인 (MA5 vs MA20)
    if "MA5" in df.columns and "MA20" in df.columns and len(df) >= 3:
        recent = df.tail(3)
        if (recent["MA5"].iloc[-1] > recent["MA20"].iloc[-1] and
                recent["MA5"].iloc[-2] <= recent["MA20"].iloc[-2]):
            score += 15  # 골든크로스
        elif (recent["MA5"].iloc[-1] < recent["MA20"].iloc[-1] and
                recent["MA5"].iloc[-2] >= recent["MA20"].iloc[-2]):
            score -= 15  # 데드크로스

    # 이동평균 배열 분석 (정배열/역배열)
    ma_cols = ["MA5", "MA20", "MA60"]
    ma_vals = []
    for col in ma_cols:
        if col in df.columns and not pd.isna(last.get(col)):
            ma_vals.append(last[col])

    if len(ma_vals) == 3:
        if ma_vals[0] > ma_vals[1] > ma_vals[2]:
            score += 10  # 정배열 (상승 추세)
        elif ma_vals[0] < ma_vals[1] < ma_vals[2]:
            score -= 15  # 역배열 (하락 추세) - 더 강하게 감점

    # MA20 기울기 (최근 5일)
    if "MA20" in df.columns and len(df) >= 25:
        ma20_now = df["MA20"].iloc[-1]
        ma20_5ago = df["MA20"].iloc[-6]
        if not pd.isna(ma20_now) and not pd.isna(ma20_5ago) and ma20_5ago != 0:
            slope = (ma20_now - ma20_5ago) / ma20_5ago * 100
            if slope < -1.0:
                score -= 10  # 20일선 하락 중 → 추가 감점

    return max(0, min(100, score))


def is_downtrend(df: pd.DataFrame) -> bool:
    """현재 하락 추세 여부 판별 (다른 지표의 매수 신호 보정용)"""
    if df.empty or len(df) < 60:
        return False

    last = df.iloc[-1]
    signals = 0

    # 역배열 체크
    ma_cols = ["MA5", "MA20", "MA60"]
    ma_vals = []
    for col in ma_cols:
        if col in df.columns and not pd.isna(last.get(col)):
            ma_vals.append(last[col])
    if len(ma_vals) == 3 and ma_vals[0] < ma_vals[1] < ma_vals[2]:
        signals += 1

    # 가격이 60일선 아래
    if "MA60" in df.columns and not pd.isna(last.get("MA60")):
        if last["Close"] < last["MA60"]:
            signals += 1

    # MA20 하락 기울기
    if "MA20" in df.columns and len(df) >= 25:
        ma20_now = df["MA20"].iloc[-1]
        ma20_5ago = df["MA20"].iloc[-6]
        if not pd.isna(ma20_now) and not pd.isna(ma20_5ago) and ma20_5ago != 0:
            if (ma20_now - ma20_5ago) / ma20_5ago * 100 < -1.0:
                signals += 1

    return signals >= 2  # 3개 중 2개 이상이면 하락 추세


def calc_momentum_score(df: pd.DataFrame, days: int = 5) -> float:
    """모멘텀 점수 (N일 수익률)"""
    if df.empty or len(df) < days + 1:
        return 50

    ret = (df["Close"].iloc[-1] / df["Close"].iloc[-days - 1] - 1) * 100

    if ret > 5:
        return 90
    elif ret > 3:
        return 75
    elif ret > 1:
        return 60
    elif ret > -1:
        return 50
    elif ret > -3:
        return 40
    elif ret > -5:
        return 25
    else:
        return 10


def get_technical_summary(df: pd.DataFrame) -> dict:
    """기술적 지표 요약"""
    if df.empty:
        return {}

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last

    summary = {
        "close": last["Close"],
        "change_pct": (last["Close"] / prev["Close"] - 1) * 100 if prev["Close"] != 0 else 0,
    }

    for col in ["RSI", "MACD", "MACD_Signal", "MACD_Hist", "BB_PctB",
                 "Volume_Ratio", "ADX", "Stoch_K", "Stoch_D", "ATR"]:
        if col in df.columns:
            val = last.get(col)
            summary[col.lower()] = float(val) if not pd.isna(val) else None

    for ma in ["MA5", "MA20", "MA60", "MA120"]:
        if ma in df.columns and not pd.isna(last.get(ma)):
            summary[ma.lower()] = float(last[ma])
            summary[f"{ma.lower()}_above"] = last["Close"] > last[ma]

    return summary
