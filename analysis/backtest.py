"""간단한 백테스팅 엔진"""
import pandas as pd
import numpy as np
from analysis.technical import add_all_indicators


def backtest_strategy(
    df: pd.DataFrame,
    strategy_fn,
    initial_capital: float = 10_000_000,
    commission_pct: float = 0.015,  # 0.015% 수수료
    tax_pct: float = 0.23,  # 한국 매도세 0.23%
) -> dict:
    """전략 백테스팅 실행"""
    df = add_all_indicators(df.copy())
    if df.empty or len(df) < 30:
        return {"error": "데이터 부족"}

    capital = initial_capital
    shares = 0
    position = None  # "long" or None
    trades = []
    equity_curve = []

    for i in range(20, len(df)):
        row = df.iloc[i]
        signal = strategy_fn(df, i)
        price = row["Close"]

        if signal == "buy" and position is None:
            shares = int(capital / (price * (1 + commission_pct / 100)))
            if shares > 0:
                cost = shares * price * (1 + commission_pct / 100)
                capital -= cost
                position = "long"
                trades.append({"type": "buy", "price": price, "shares": shares,
                               "date": df.index[i]})

        elif signal == "sell" and position == "long":
            proceeds = shares * price * (1 - commission_pct / 100 - tax_pct / 100)
            # 직전 매수 거래 찾기
            last_buy = next((t for t in reversed(trades) if t["type"] == "buy"), None)
            buy_price = last_buy["price"] if last_buy else price
            capital += proceeds
            trades.append({"type": "sell", "price": price, "shares": shares,
                           "date": df.index[i],
                           "pnl": proceeds - buy_price * shares})
            shares = 0
            position = None

        # 평가액
        total_value = capital + (shares * price if position else 0)
        equity_curve.append({"date": df.index[i], "value": total_value})

    # 미청산 포지션 정리
    if position == "long" and shares > 0:
        final_price = df["Close"].iloc[-1]
        proceeds = shares * final_price * (1 - commission_pct / 100 - tax_pct / 100)
        capital += proceeds

    final_value = capital
    equity_df = pd.DataFrame(equity_curve).set_index("date") if equity_curve else pd.DataFrame()

    # 성과 지표
    total_return = (final_value / initial_capital - 1) * 100
    winning_trades = [t for t in trades if t["type"] == "sell" and t.get("pnl", 0) > 0]
    losing_trades = [t for t in trades if t["type"] == "sell" and t.get("pnl", 0) <= 0]
    sell_trades = [t for t in trades if t["type"] == "sell"]

    max_drawdown = 0
    if not equity_df.empty:
        peak = equity_df["value"].expanding().max()
        drawdown = (equity_df["value"] - peak) / peak * 100
        max_drawdown = drawdown.min()

    return {
        "initial_capital": initial_capital,
        "final_value": round(final_value),
        "total_return": round(total_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "trade_count": len(sell_trades),
        "win_rate": round(len(winning_trades) / len(sell_trades) * 100, 1) if sell_trades else 0,
        "avg_profit": round(np.mean([t["pnl"] for t in winning_trades])) if winning_trades else 0,
        "avg_loss": round(np.mean([t["pnl"] for t in losing_trades])) if losing_trades else 0,
        "equity_curve": equity_df,
        "trades": trades,
    }


# 내장 전략들
def golden_cross_strategy(df: pd.DataFrame, i: int) -> str:
    """골든크로스/데드크로스 전략"""
    if "MA5" not in df.columns or "MA20" not in df.columns:
        return "hold"
    if i < 1:
        return "hold"

    curr_ma5 = df["MA5"].iloc[i]
    curr_ma20 = df["MA20"].iloc[i]
    prev_ma5 = df["MA5"].iloc[i - 1]
    prev_ma20 = df["MA20"].iloc[i - 1]

    if pd.isna(curr_ma5) or pd.isna(curr_ma20):
        return "hold"

    if curr_ma5 > curr_ma20 and prev_ma5 <= prev_ma20:
        return "buy"
    elif curr_ma5 < curr_ma20 and prev_ma5 >= prev_ma20:
        return "sell"
    return "hold"


def rsi_reversal_strategy(df: pd.DataFrame, i: int) -> str:
    """RSI 반전 전략"""
    if "RSI" not in df.columns or i < 1:
        return "hold"

    rsi = df["RSI"].iloc[i]
    prev_rsi = df["RSI"].iloc[i - 1]

    if pd.isna(rsi):
        return "hold"

    if rsi > 30 and prev_rsi <= 30:
        return "buy"
    elif rsi < 70 and prev_rsi >= 70:
        return "sell"
    return "hold"


def bollinger_bounce_strategy(df: pd.DataFrame, i: int) -> str:
    """볼린저밴드 바운스 전략"""
    if "BB_PctB" not in df.columns or i < 1:
        return "hold"

    pctb = df["BB_PctB"].iloc[i]
    prev_pctb = df["BB_PctB"].iloc[i - 1]

    if pd.isna(pctb):
        return "hold"

    if pctb > 0.05 and prev_pctb <= 0.05:
        return "buy"
    elif pctb < 0.95 and prev_pctb >= 0.95:
        return "sell"
    return "hold"


def macd_crossover_strategy(df: pd.DataFrame, i: int) -> str:
    """MACD 크로스오버 전략"""
    if "MACD" not in df.columns or "MACD_Signal" not in df.columns or i < 1:
        return "hold"

    macd = df["MACD"].iloc[i]
    signal = df["MACD_Signal"].iloc[i]
    prev_macd = df["MACD"].iloc[i - 1]
    prev_signal = df["MACD_Signal"].iloc[i - 1]

    if pd.isna(macd) or pd.isna(signal):
        return "hold"

    if macd > signal and prev_macd <= prev_signal:
        return "buy"
    elif macd < signal and prev_macd >= prev_signal:
        return "sell"
    return "hold"


STRATEGIES = {
    "골든크로스": golden_cross_strategy,
    "RSI 반전": rsi_reversal_strategy,
    "볼린저 바운스": bollinger_bounce_strategy,
    "MACD 크로스오버": macd_crossover_strategy,
}
