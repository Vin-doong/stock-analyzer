"""미국 주식 데이터 (yfinance)"""
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from data import cache
from config import CACHE_TTL


def _wiki_read_html(url):
    """Wikipedia 페이지에서 테이블 파싱 (User-Agent 필요)"""
    import urllib.request
    from io import StringIO
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StockAnalyzer/1.0"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8")
    return pd.read_html(StringIO(html))


def _fetch_sp500_tickers() -> pd.DataFrame:
    """Wikipedia에서 S&P 500 전체 종목 리스트 가져오기 (~500개)"""
    try:
        tables = _wiki_read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        df = tables[0]
        result = pd.DataFrame({
            "ticker": df["Symbol"].str.replace(".", "-", regex=False),
            "name": df["Security"],
            "sector": df.get("GICS Sector", ""),
            "market": "NYSE",
        })
        return result
    except Exception as e:
        print(f"[US] S&P 500 리스트 조회 실패: {e}")
        return pd.DataFrame()


def _fetch_nasdaq100_tickers() -> pd.DataFrame:
    """Wikipedia에서 NASDAQ 100 전체 종목 리스트 가져오기 (~100개)"""
    try:
        tables = _wiki_read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
        for table in tables:
            if "Ticker" in table.columns or "Symbol" in table.columns:
                ticker_col = "Ticker" if "Ticker" in table.columns else "Symbol"
                name_col = "Company" if "Company" in table.columns else table.columns[0]
                result = pd.DataFrame({
                    "ticker": table[ticker_col].str.replace(".", "-", regex=False),
                    "name": table[name_col],
                    "market": "NASDAQ",
                })
                return result
        return pd.DataFrame()
    except Exception as e:
        print(f"[US] NASDAQ 100 리스트 조회 실패: {e}")
        return pd.DataFrame()


# Wikipedia 실패 시 사용할 폴백 리스트
_FALLBACK_SP500 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "UNH", "JNJ", "V", "XOM", "JPM", "PG", "MA", "HD", "CVX", "MRK",
    "ABBV", "LLY", "PEP", "KO", "COST", "AVGO", "WMT", "MCD", "CSCO",
    "ACN", "TMO", "ABT", "DHR", "CRM", "NKE", "NEE", "LIN", "TXN",
    "PM", "UPS", "MS", "RTX", "LOW", "INTC", "AMD", "QCOM", "ISRG",
    "AMAT", "BKNG", "ADP", "MDLZ",
]
_FALLBACK_NASDAQ = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO",
    "PEP", "COST", "CSCO", "ADBE", "TXN", "CMCSA", "NFLX", "INTC",
    "AMD", "QCOM", "INTU", "AMAT", "ISRG", "BKNG", "ADP", "MDLZ",
    "REGN", "VRTX", "ADI", "GILD", "LRCX", "MRVL", "PANW", "SNPS",
    "KLAC", "CDNS", "FTNT", "CRWD", "DDOG", "ZS", "MNST", "MELI",
    "WDAY", "TEAM", "ABNB", "COIN", "PLTR", "ARM", "SMCI", "MSTR",
    "SOFI", "HOOD",
]


def get_stock_list(market: str = "NYSE") -> pd.DataFrame:
    """미국 종목 리스트 (S&P 500 전체 / NASDAQ 100 전체)"""
    key = f"us:stock_list:{market}:v2"
    cached = cache.get(key)
    if cached is not None:
        return cached

    if market == "NYSE":
        df = _fetch_sp500_tickers()
        fallback = _FALLBACK_SP500
    else:
        df = _fetch_nasdaq100_tickers()
        fallback = _FALLBACK_NASDAQ

    # Wikipedia 실패 시 폴백
    if df is None or df.empty:
        rows = [{"ticker": t, "name": t, "market": market} for t in fallback]
        df = pd.DataFrame(rows)

    cache.set(key, df, CACHE_TTL["stock_list"])
    return df


def get_price_data(ticker: str, days: int = 365) -> pd.DataFrame:
    """종목 OHLCV 데이터"""
    key = f"us:price:{ticker}:{days}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        period_map = {30: "1mo", 90: "3mo", 180: "6mo", 365: "1y", 730: "2y"}
        period = "1y"
        for d, p in sorted(period_map.items()):
            if days <= d:
                period = p
                break

        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df is not None and not df.empty:
            df.index.name = "Date"
            # 불필요 컬럼 제거
            for col in ["Dividends", "Stock Splits", "Capital Gains"]:
                if col in df.columns:
                    df = df.drop(columns=[col])
            cache.set(key, df, CACHE_TTL["daily"])
        return df
    except Exception as e:
        print(f"[US] {ticker} 가격 데이터 조회 실패: {e}")
        return pd.DataFrame()


def get_fundamental_data(ticker: str) -> dict:
    """종목 펀더멘털 데이터"""
    key = f"us:fundamental:{ticker}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        result = {
            "per": info.get("trailingPE"),
            "forward_per": info.get("forwardPE"),
            "pbr": info.get("priceToBook"),
            "roe": info.get("returnOnEquity"),
            "eps": info.get("trailingEps"),
            "revenue": info.get("totalRevenue"),
            "revenue_growth": info.get("revenueGrowth"),
            "operating_margin": info.get("operatingMargins"),
            "market_cap": info.get("marketCap"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "name": info.get("shortName", ticker),
        }
        cache.set(key, result, CACHE_TTL["fundamental"])
        return result
    except Exception as e:
        print(f"[US] {ticker} 펀더멘털 조회 실패: {e}")
        return {}


def get_index_data(index_code: str = "^GSPC", days: int = 90) -> pd.DataFrame:
    """지수 데이터 (^GSPC=S&P500, ^IXIC=NASDAQ)"""
    key = f"us:index:{index_code}:{days}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    try:
        period_map = {30: "1mo", 90: "3mo", 180: "6mo", 365: "1y"}
        period = "3mo"
        for d, p in sorted(period_map.items()):
            if days <= d:
                period = p
                break

        df = yf.Ticker(index_code).history(period=period)
        if df is not None and not df.empty:
            cache.set(key, df, CACHE_TTL["daily"])
        return df
    except Exception as e:
        print(f"[US] 지수 {index_code} 조회 실패: {e}")
        return pd.DataFrame()
