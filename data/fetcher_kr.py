"""한국 주식 데이터 (FinanceDataReader + pykrx)"""
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from data import cache
from config import CACHE_TTL
import time


def get_stock_list(market: str = "KOSPI") -> pd.DataFrame:
    """KOSPI/KOSDAQ 종목 리스트 조회"""
    key = f"kr:stock_list:{market}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    df = fdr.StockListing(market)
    if df is not None and not df.empty:
        # 필요한 컬럼만 정리
        cols = {}
        if "Code" in df.columns:
            cols["Code"] = "ticker"
        elif "Symbol" in df.columns:
            cols["Symbol"] = "ticker"
        if "Name" in df.columns:
            cols["Name"] = "name"
        if "Market" in df.columns:
            cols["Market"] = "market"
        if "Sector" in df.columns:
            cols["Sector"] = "sector"
        if "Marcap" in df.columns:
            cols["Marcap"] = "market_cap"
        elif "MarketCap" in df.columns:
            cols["MarketCap"] = "market_cap"

        available = {k: v for k, v in cols.items() if k in df.columns}
        df = df[list(available.keys())].rename(columns=available)
        cache.set(key, df, CACHE_TTL["stock_list"])
    return df


def get_price_data(ticker: str, days: int = 365) -> pd.DataFrame:
    """종목 OHLCV 데이터 조회"""
    key = f"kr:price:{ticker}:{days}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    end = datetime.now()
    start = end - timedelta(days=days)
    try:
        df = fdr.DataReader(ticker, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        if df is not None and not df.empty:
            df.index.name = "Date"
            # 컬럼명 통일
            col_map = {}
            for col in df.columns:
                cl = col.lower()
                if cl == "open":
                    col_map[col] = "Open"
                elif cl == "high":
                    col_map[col] = "High"
                elif cl == "low":
                    col_map[col] = "Low"
                elif cl == "close":
                    col_map[col] = "Close"
                elif cl == "volume":
                    col_map[col] = "Volume"
            if col_map:
                df = df.rename(columns=col_map)
            cache.set(key, df, CACHE_TTL["daily"])
        return df
    except Exception as e:
        print(f"[KR] {ticker} 가격 데이터 조회 실패: {e}")
        return pd.DataFrame()


def _get_all_fundamentals() -> dict:
    """전체 시장 펀더멘털 데이터를 1회만 조회하여 캐시 (모든 종목)"""
    key = "kr:fundamental:ALL"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        from pykrx.stock import get_market_fundamental_by_ticker
        from pykrx.stock import get_market_cap_by_ticker

        fund_df = None
        cap_df = None
        used_date = None

        # 최근 영업일 최대 10일 시도 (실패 시 즉시 다음 날짜로)
        for i in range(10):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            try:
                fund_df = get_market_fundamental_by_ticker(date, market="ALL")
                if fund_df is not None and not fund_df.empty:
                    used_date = date
                    break
            except Exception:
                continue

        if fund_df is None or fund_df.empty:
            print("[KR] 펀더멘털 데이터 조회 실패 (pykrx API 문제)")
            cache.set(key, {}, 600)  # 10분간 빈 결과 캐시 (재시도 방지)
            return {}

        # 시가총액도 동일 날짜로 한 번만
        try:
            cap_df = get_market_cap_by_ticker(used_date, market="ALL")
        except Exception:
            cap_df = None

        result = {}
        for ticker in fund_df.index:
            row = fund_df.loc[ticker]
            item = {
                "per": float(row.get("PER", 0)) if row.get("PER", 0) != 0 else None,
                "pbr": float(row.get("PBR", 0)) if row.get("PBR", 0) != 0 else None,
                "eps": float(row.get("EPS", 0)) if row.get("EPS", 0) != 0 else None,
            }
            if cap_df is not None and ticker in cap_df.index:
                try:
                    item["market_cap"] = float(cap_df.loc[ticker, "시가총액"])
                except Exception:
                    pass
            result[ticker] = item

        cache.set(key, result, CACHE_TTL["fundamental"])
        print(f"[KR] 펀더멘털 {len(result)}개 종목 로드 완료 (기준: {used_date})")
        return result
    except Exception as e:
        print(f"[KR] 펀더멘털 전체 조회 실패: {e}")
        cache.set(key, {}, 600)
        return {}


def get_fundamental_data(ticker: str) -> dict:
    """종목 기본적 분석 데이터 (전체 캐시에서 조회)"""
    all_fund = _get_all_fundamentals()
    return all_fund.get(ticker, {})


def get_index_data(index_code: str = "KS11", days: int = 90) -> pd.DataFrame:
    """지수 데이터 (KS11=KOSPI, KQ11=KOSDAQ)"""
    key = f"kr:index:{index_code}:{days}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    end = datetime.now()
    start = end - timedelta(days=days)
    try:
        df = fdr.DataReader(index_code, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        if df is not None and not df.empty:
            cache.set(key, df, CACHE_TTL["daily"])
        return df
    except Exception as e:
        print(f"[KR] 지수 {index_code} 조회 실패: {e}")
        return pd.DataFrame()
