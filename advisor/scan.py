"""전종목 스캔 (KOSPI + KOSDAQ).

1차 하드 필터 (가격/등락/거래대금/시총)는 FinanceDataReader StockListing으로
한 번에 적용한 뒤, 상위 N개에 대해서만 정밀 분석(BuyValidator + 점수화)을 수행한다.

사용법:
    python -m advisor scan                       # 스윙 스타일 기본, 정밀 10개
    python -m advisor scan --style day --top 5   # 단타 스타일, 상위 5개
    python -m advisor scan --no-precise          # 1차 필터만 (정밀 분석 생략)
    python -m advisor scan --include-held        # 보유 종목 포함
"""
from __future__ import annotations

from typing import Optional

from advisor.portfolio import get_rules, get_swing_holdings


def fetch_market_snapshot():
    """FDR로 KOSPI/KOSDAQ 전종목 스냅샷 DataFrame 반환."""
    import FinanceDataReader as fdr
    import pandas as pd

    kospi = fdr.StockListing("KOSPI")
    kosdaq = fdr.StockListing("KOSDAQ")
    df = pd.concat([kospi, kosdaq], ignore_index=True)
    return df


def apply_hard_filters(df, style: str = "swing"):
    """스타일별 룰의 하드 제약을 FDR 데이터에 적용."""
    rules = get_rules(style)
    lo, hi = rules.get("price_range", [3000, 50000])
    max_chg = rules.get("max_daily_change", 5)
    min_val = rules.get("min_trading_value", 3_000_000_000)
    min_cap = rules.get("min_market_cap", 0)

    mask = (
        (df["Close"] >= lo)
        & (df["Close"] <= hi)
        & (df["ChagesRatio"].abs() <= max_chg)
        & (df["Amount"] >= min_val)
    )
    if min_cap > 0:
        mask = mask & (df["Marcap"] >= min_cap)
    return df[mask].copy()


def score_candidate(ticker: str, name: str, style: str) -> dict:
    """단일 종목 정밀 점수화. fetch_stock_price + BuyValidator 조합."""
    from advisor.analysis import fetch_stock_price
    from advisor.rules import BuyValidator, calculate_score, score_to_action

    try:
        data = fetch_stock_price(ticker)
    except Exception as e:
        return {"ticker": ticker, "name": name, "error": str(e)}

    if not data:
        return {"ticker": ticker, "name": name, "error": "시세 조회 실패"}

    price = int(data.get("current", 0))
    if price <= 0:
        return {"ticker": ticker, "name": name, "error": "가격 0"}

    validator = BuyValidator(
        ticker=ticker,
        name=name,
        price=price,
        qty=1,  # 점수 계산엔 수량 의미 없음 (예수금 체크는 hard_block일 뿐)
        style=style,
        volume_ratio=data.get("volume_ratio"),
        daily_change_pct=data.get("day_change_pct"),
        rsi=data.get("rsi"),
        macd_hist=data.get("macd_hist"),
        above_ma20=data.get("above_ma20"),
        bb_pctb=data.get("bb_pctb"),
        adx=data.get("adx"),
        ret_60d=data.get("ret_60d"),
        ret_90d=data.get("ret_90d"),
        market_cap=data.get("market_cap"),
        trading_value=data.get("trading_value"),
    )
    checks = validator.validate_all()
    scored_checks = [c for c in checks if c.weight > 0]
    score, total = calculate_score(scored_checks)
    hard_block = any(c.hard_block for c in checks if c.weight > 0)

    # 상태 요약
    action, _ = score_to_action(score, total)
    # 실패한 가중치 체크 상위 3개 (score=0 & weight>0)
    fails = [c.name for c in scored_checks if c.score == 0][:3]

    return {
        "ticker": ticker,
        "name": name,
        "price": price,
        "chg_pct": data.get("day_change_pct"),
        "trading_value": data.get("trading_value"),
        "rsi": data.get("rsi"),
        "macd_hist": data.get("macd_hist"),
        "bb_pctb": data.get("bb_pctb"),
        "volume_ratio": data.get("volume_ratio"),
        "above_ma20": data.get("above_ma20"),
        "ret_60d": data.get("ret_60d"),
        "score": score,
        "total": total,
        "action": action,
        "hard_block": hard_block,
        "fails": fails,
    }


def scan_all(
    style: str = "swing",
    top_n: int = 10,
    precise: bool = True,
    include_held: bool = False,
) -> dict:
    """전종목 스캔 수행 후 결과 dict 반환."""
    df = fetch_market_snapshot()
    total_count = len(df)

    filtered = apply_hard_filters(df, style=style)

    # 보유 중 종목 제외
    if not include_held:
        held_tickers = {
            h["ticker"] for h in get_swing_holdings()
        }
        if held_tickers:
            filtered = filtered[~filtered["Code"].isin(held_tickers)]

    filtered = filtered.sort_values("Amount", ascending=False)
    filtered_count = len(filtered)

    top_df = filtered.head(top_n).copy()

    results = []
    if precise:
        # 정밀 분석 — 병렬 처리
        from concurrent.futures import ThreadPoolExecutor

        pairs = [(row["Code"], row["Name"]) for _, row in top_df.iterrows()]

        def _worker(p):
            code, name = p
            return score_candidate(code, name, style)

        with ThreadPoolExecutor(max_workers=5) as ex:
            results = list(ex.map(_worker, pairs))
        # 점수 내림차순 정렬 (에러난 건 뒤로)
        results.sort(
            key=lambda r: (-r.get("score", -1) if "error" not in r else 1e9,
                           r.get("hard_block", False)),
        )
    else:
        # 1차 필터만
        for _, row in top_df.iterrows():
            results.append(
                {
                    "ticker": row["Code"],
                    "name": row["Name"],
                    "price": int(row["Close"]),
                    "chg_pct": float(row["ChagesRatio"]),
                    "trading_value": int(row["Amount"]),
                    "market_cap": int(row["Marcap"]),
                }
            )

    return {
        "style": style,
        "total_market": total_count,
        "filter_passed": filtered_count,
        "top_n": top_n,
        "precise": precise,
        "results": results,
    }
