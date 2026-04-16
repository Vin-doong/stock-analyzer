"""종목 점수 기반 순위 매기기"""
import pandas as pd
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import TradingStyle, SCAN_MAX_WORKERS
from analysis.scoring import score_stock, _get_signal
from analysis.technical import get_technical_summary

logger = logging.getLogger(__name__)


def _presort_stocks(stock_df: pd.DataFrame, style: TradingStyle, scan_size: int) -> pd.DataFrame:
    """스캔 전 시총/거래량 기반 사전 정렬

    - 단타: 거래량 우선 (유동성이 핵심)
    - 스윙: 시총 상위 (중대형주 중심)
    - 중장기: 시총 상위 (대형주 우선)

    시총/거래량 데이터가 없으면 원본 순서 유지
    """
    df = stock_df.copy()

    if style == TradingStyle.DAY:
        # 단타: 거래량 데이터가 있으면 거래량 내림차순
        if "volume" in df.columns:
            df = df.sort_values("volume", ascending=False, na_position="last")
        elif "market_cap" in df.columns:
            df = df.sort_values("market_cap", ascending=False, na_position="last")
    else:
        # 스윙/중장기: 시총 내림차순 (대형주 우선)
        if "market_cap" in df.columns:
            df = df.sort_values("market_cap", ascending=False, na_position="last")

    return df.head(scan_size)


def _score_single(ticker: str, name: str, market: str, style: TradingStyle) -> dict | None:
    """단일 종목 점수 산출"""
    try:
        if market in ("KOSPI", "KOSDAQ"):
            from data.fetcher_kr import get_price_data, get_fundamental_data
        else:
            from data.fetcher_us import get_price_data, get_fundamental_data

        df = get_price_data(ticker)
        if df is None or df.empty or len(df) < 30:
            return None

        fund = get_fundamental_data(ticker)
        result = score_stock(ticker, name, df, style, fund)

        # 기술적 요약도 포함
        from analysis.technical import add_all_indicators
        df_ind = add_all_indicators(df)
        tech = get_technical_summary(df_ind)

        return {
            "ticker": ticker,
            "name": name,
            "score": result.composite_score,
            "signal": result.signal,
            "confidence": result.confidence,
            "category_scores": result.category_scores,
            "rsi": tech.get("rsi"),
            "volume_ratio": tech.get("volume_ratio"),
            "change_pct": tech.get("change_pct"),
            "close": tech.get("close"),
        }
    except Exception as e:
        logger.warning(f"[Ranker] {ticker} 점수 산출 실패: {e}")
        return None


def screen_and_rank(
    market: str,
    style: TradingStyle,
    stock_df: pd.DataFrame,
    top_n: int = 20,
    max_workers: int | None = None,
    max_scan: int | None = None,
) -> list[dict]:
    """종목 스크리닝 및 순위 매기기"""
    if stock_df.empty:
        return []

    from config import DEFAULT_SCREEN_SIZE
    scan_size = min(len(stock_df), max_scan or DEFAULT_SCREEN_SIZE)
    workers = max_workers or SCAN_MAX_WORKERS

    # 시총/거래량 기반 사전 정렬 후 상위 N개 선택
    sorted_df = _presort_stocks(stock_df, style, scan_size)
    tickers = sorted_df.to_dict("records")

    logger.info(f"[Ranker] {market} {style.value} 스캔 시작: {len(tickers)}개 종목, {workers} workers")
    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for row in tickers:
            ticker = row.get("ticker", "")
            name = row.get("name", ticker)
            if not ticker:
                continue
            future = executor.submit(_score_single, ticker, name, market, style)
            futures[future] = ticker

        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)

    logger.info(f"[Ranker] 스캔 완료: {len(results)}/{len(tickers)}개 성공")

    # 시황 보정 적용
    try:
        from analysis.market_regime import get_market_regime
        regime = get_market_regime(market)
        adjustment = regime.get("score_adjustment", 0)
        regime_label = regime.get("regime", "중립")

        logger.info(f"[Ranker] 시황: {regime_label}, 점수 보정: {adjustment}")

        if adjustment != 0:
            for r in results:
                r["score"] = max(0, min(100, r["score"] + adjustment))
                r["signal"] = _get_signal(r["score"])
                r["regime_adjustment"] = adjustment

        for r in results:
            r["market_regime"] = regime_label
    except Exception as e:
        logger.error(f"[Ranker] 시황 보정 실패: {e}")

    # 점수 내림차순 정렬
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]
