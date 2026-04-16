"""네이버 금융 기반 미국 주식 실시간 시세

특징:
- 거의 실시간 (delayTime: 0)
- API 키 불필요
- 무료
- 빠름 (~50~150ms)

티커 규칙:
- NASDAQ: .O 접미사 (NVDA.O, AAPL.O)
- NYSE: 접미사 없음 (JNJ, IBM)
- AMEX: .K 또는 접미사 없음 (SCHD.K, VOO)

알 수 없을 땐 여러 변형을 순차 시도.
"""
import urllib.request
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# 알려진 티커 매핑 (빠른 조회용)
KNOWN_SYMBOLS = {
    # NASDAQ
    "NVDA": "NVDA.O",
    "AAPL": "AAPL.O",
    "MSFT": "MSFT.O",
    "GOOGL": "GOOGL.O",
    "GOOG": "GOOG.O",
    "AMZN": "AMZN.O",
    "META": "META.O",
    "TSLA": "TSLA.O",
    "QQQ": "QQQ.O",
    "AVGO": "AVGO.O",
    "COST": "COST.O",
    "NFLX": "NFLX.O",
    "AMD": "AMD.O",
    "INTC": "INTC.O",
    "PEP": "PEP.O",
    "ADBE": "ADBE.O",
    # NYSE
    "JNJ": "JNJ",
    "BRK-B": "BRK.B",
    "V": "V",
    "JPM": "JPM",
    "WMT": "WMT",
    "PG": "PG",
    "XOM": "XOM",
    "UNH": "UNH",
    "HD": "HD",
    "CVX": "CVX",
    "KO": "KO",
    "MRK": "MRK",
    "ABBV": "ABBV",
    "LLY": "LLY",
    "MA": "MA",
    "BA": "BA",
    "DIS": "DIS",
    "IBM": "IBM",
    # AMEX ETFs
    "SCHD": "SCHD.K",
    "VOO": "VOO",  # AMEX이지만 접미사 없이 작동
    "VTI": "VTI",
    "VIG": "VIG",
    "VXUS": "VXUS.O",
    "IEFA": "IEFA",
    "IEMG": "IEMG",
    "AGG": "AGG",
    "GLD": "GLD",
    "DGRO": "DGRO",
    "SCHY": "SCHY.K",
    "SOXX": "SOXX.O",
    "SMH": "SMH",
    "XLK": "XLK",
    "XLV": "XLV",
    "XLE": "XLE",
    "XLF": "XLF",
}


def _fetch_single(code: str) -> Optional[dict]:
    """단일 코드로 시도"""
    url = f"https://api.stock.naver.com/stock/{code}/basic"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def resolve_symbol(ticker: str) -> Optional[dict]:
    """티커로 네이버 API 응답 조회 (여러 변형 순차 시도)"""
    # 1. 알려진 매핑 먼저
    if ticker in KNOWN_SYMBOLS:
        code = KNOWN_SYMBOLS[ticker]
        result = _fetch_single(code)
        if result and result.get("closePrice"):
            return result

    # 2. 변형 순차 시도
    variants = [ticker, f"{ticker}.O", f"{ticker}.K"]
    for v in variants:
        result = _fetch_single(v)
        if result and result.get("closePrice"):
            return result

    return None


def fetch_us_realtime(ticker: str) -> Optional[dict]:
    """미국 주식 실시간 시세 조회 (네이버)"""
    data = resolve_symbol(ticker)
    if not data:
        return None

    price = float(data.get("closePrice", 0))
    change = float(data.get("compareToPreviousClosePrice", 0))
    change_pct = float(data.get("fluctuationsRatio", 0))

    return {
        "ticker": ticker,
        "name": data.get("stockName"),
        "name_en": data.get("stockNameEng"),
        "exchange": data.get("stockExchangeName"),
        "price": price,
        "prev_close": price - change if change else price,
        "change": change,
        "change_pct": change_pct,
        "delay_minutes": data.get("delayTime", 0),
        "delay_name": data.get("delayTimeName"),
        "market_status": data.get("marketStatus"),  # OPEN, CLOSE, PRE_OPEN
        "shares_outstanding": data.get("countOfListedStock"),
        "local_traded_at": data.get("localTradedAt"),
        "source": "naver",
        "timestamp": datetime.now().isoformat(),
    }


def fetch_us_realtime_parallel(tickers: list[str]) -> dict:
    """병렬 조회"""
    results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_us_realtime, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                data = future.result()
                if data:
                    results[ticker] = data
            except Exception:
                pass
    return results


def fetch_us_with_detail(ticker: str) -> Optional[dict]:
    """실시간 시세 + 펀더멘털 (yfinance로 보강)

    네이버는 실시간이 강점, yfinance는 상세 지표가 강점.
    둘을 합쳐서 최선의 데이터 제공.
    """
    # 1. 실시간 가격 (네이버, 빠름)
    rt = fetch_us_realtime(ticker)
    if not rt:
        # 네이버 실패 시 yfinance 완전 폴백
        from advisor.us_stocks import fetch_us_quote
        return fetch_us_quote(ticker)

    # 2. 펀더멘털 보강 (yfinance, 느림이지만 상세)
    try:
        import yfinance as yf
        yft = yf.Ticker(ticker)
        info = yft.info

        # 배당률 계산 (다중 방법)
        div_yield_pct = None
        # 방법 1: trailingAnnualDividendRate / 현재가
        div_rate = info.get("trailingAnnualDividendRate")
        if div_rate and rt["price"] > 0:
            div_yield_pct = (div_rate / rt["price"]) * 100

        # 방법 2: dividendYield 필드 (폴백)
        if div_yield_pct is None:
            raw = info.get("dividendYield")
            if raw is not None:
                # yfinance 버전별로 포맷 차이
                if raw > 1:
                    div_yield_pct = raw
                else:
                    div_yield_pct = raw * 100

        # 방법 3: yield 필드 (또 다른 폴백)
        if div_yield_pct is None:
            raw = info.get("yield")
            if raw is not None:
                if raw > 1:
                    div_yield_pct = raw
                else:
                    div_yield_pct = raw * 100

        # 안전장치: 비현실적 값 제거
        if div_yield_pct is not None and (div_yield_pct > 15 or div_yield_pct < 0):
            div_yield_pct = None

        return {
            **rt,  # 실시간 데이터 (가격, 변동)
            "pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "market_cap": info.get("marketCap"),
            "dividend_yield": div_yield_pct,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "fifty_day_avg": info.get("fiftyDayAverage"),
            "two_hundred_day_avg": info.get("twoHundredDayAverage"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "beta": info.get("beta"),
        }
    except Exception:
        # yfinance 실패해도 네이버 데이터는 반환
        return rt


def fetch_krw_usd_rate_naver() -> float:
    """원-달러 환율 조회 (네이버)"""
    try:
        url = "https://api.stock.naver.com/marketindex/exchange/FX_USDKRW/basic"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            rate = float(d.get("calcPrice") or d.get("closePrice") or 0)
            if rate > 0:
                return rate
    except Exception:
        pass
    # 폴백: yfinance
    try:
        import yfinance as yf
        t = yf.Ticker("KRW=X")
        hist = t.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return 1474.0
