"""실시간 금융 데이터 수집

데이터 소스 우선순위:
1. 네이버 금융 (polling.finance.naver.com) - 가장 빠름, 데이터 풍부
2. 다음금융 API (finance.daum.net) - 백업
3. FinanceDataReader - 최종 폴백 (과거 데이터용)

특징:
- 실시간 (delayTime: 0)
- 병렬 조회 가능
- 장중/장외 자동 판별
- 3단계 폴백으로 안정성 확보
"""
import urllib.request
import urllib.parse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

# 공통 헤더 (봇 차단 회피)
DAUM_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.daum.net/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

NAVER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com/",
}


def _http_get(url: str, headers: dict, timeout: int = 5) -> Optional[str]:
    """HTTP GET 요청"""
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return None


def fetch_daum_quote(ticker: str) -> Optional[dict]:
    """다음금융에서 실시간 시세 조회

    Returns:
        {
            "ticker": "005930",
            "name": "삼성전자",
            "price": 72000,
            "change": 1200,
            "change_pct": 1.69,
            "volume": 8500000,
            "open": 71500,
            "high": 72500,
            "low": 70800,
            "prev_close": 70800,
            "market_cap": ...,
            "source": "daum",
            "timestamp": "2026-04-15T15:26:00",
        }
    """
    code = f"A{ticker}" if not ticker.startswith("A") else ticker
    url = f"https://finance.daum.net/api/quotes/{code}"

    text = _http_get(url, DAUM_HEADERS)
    if not text:
        return None

    try:
        d = json.loads(text)
    except Exception:
        return None

    return {
        "ticker": ticker,
        "name": d.get("name"),
        "price": float(d.get("tradePrice", 0)),
        "change": float(d.get("change_price", 0)),
        "change_pct": float(d.get("changeRate", 0)) * 100,
        "change_sign": d.get("change"),  # "RISE", "FALL", "EVEN"
        "volume": int(d.get("accTradeVolume", 0)),
        "trade_value": int(d.get("accTradeValue", 0)),
        "open": float(d.get("openingPrice", 0)),
        "high": float(d.get("highPrice", 0)),
        "low": float(d.get("lowPrice", 0)),
        "prev_close": float(d.get("prevClosingPrice", 0)),
        "market_cap": int(d.get("marketCap", 0)) if d.get("marketCap") else None,
        "source": "daum",
        "timestamp": datetime.now().isoformat(),
    }


def fetch_naver_quote(ticker: str) -> Optional[dict]:
    """네이버 금융 백업 조회"""
    url = f"https://polling.finance.naver.com/api/realtime?query=SERVICE_ITEM:{ticker}"
    text = _http_get(url, NAVER_HEADERS)
    if not text:
        return None

    try:
        d = json.loads(text)
        datas = d.get("result", {}).get("areas", [{}])[0].get("datas", [])
        if not datas:
            return None
        stock = datas[0]
        return {
            "ticker": ticker,
            "name": stock.get("nm"),
            "price": float(stock.get("nv", 0)),
            "change_pct": float(stock.get("cr", 0)),
            "change": float(stock.get("cv", 0)),
            "volume": int(stock.get("aq", 0)),
            "open": float(stock.get("ov", 0)),
            "high": float(stock.get("hv", 0)),
            "low": float(stock.get("lv", 0)),
            "prev_close": float(stock.get("sv", 0)),
            "source": "naver",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception:
        return None


def fetch_quote(ticker: str) -> Optional[dict]:
    """실시간 시세 조회 (네이버 → 다음 → FDR 폴백)"""
    # 1차: 네이버 (가장 빠름, 데이터 풍부)
    try:
        from advisor.naver_kr import fetch_kr_naver
        result = fetch_kr_naver(ticker)
        if result and result.get("price", 0) > 0:
            return result
    except Exception:
        pass

    # 2차: 다음 (백업)
    result = fetch_daum_quote(ticker)
    if result and result.get("price", 0) > 0:
        return result

    # 3차: 이전 네이버 엔드포인트
    result = fetch_naver_quote(ticker)
    if result and result.get("price", 0) > 0:
        return result

    # 최종 폴백: FinanceDataReader
    try:
        import FinanceDataReader as fdr
        from datetime import timedelta
        now = datetime.now()
        df = fdr.DataReader(
            ticker,
            (now - timedelta(days=3)).strftime("%Y-%m-%d"),
            now.strftime("%Y-%m-%d"),
        )
        if df is not None and not df.empty:
            c = float(df["Close"].iloc[-1])
            pc = float(df["Close"].iloc[-2]) if len(df) >= 2 else c
            return {
                "ticker": ticker,
                "price": c,
                "change_pct": (c / pc - 1) * 100 if pc else 0,
                "change": c - pc,
                "volume": int(df["Volume"].iloc[-1]),
                "open": float(df["Open"].iloc[-1]),
                "high": float(df["High"].iloc[-1]),
                "low": float(df["Low"].iloc[-1]),
                "prev_close": pc,
                "source": "fdr",
                "timestamp": datetime.now().isoformat(),
            }
    except Exception:
        pass

    return None


def fetch_quotes_parallel(tickers: list[str], max_workers: int = 10) -> dict:
    """여러 종목 병렬 조회"""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_quote, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                data = future.result()
                if data:
                    results[ticker] = data
            except Exception:
                pass
    return results


def is_market_open() -> bool:
    """한국 시장 개장 여부"""
    now = datetime.now()
    if now.weekday() >= 5:  # 토/일
        return False
    return (now.hour > 9 or (now.hour == 9 and now.minute >= 0)) and \
           (now.hour < 15 or (now.hour == 15 and now.minute < 30))


def fetch_index_daum(code: str) -> Optional[dict]:
    """다음에서 지수 조회 (KOSPI, KOSDAQ)"""
    code_map = {
        "KOSPI": "KOSPI",
        "KOSDAQ": "KOSDAQ",
        "KS11": "KOSPI",
        "KQ11": "KOSDAQ",
    }
    mapped = code_map.get(code, code)
    url = f"https://finance.daum.net/api/market_index/days?page=1&perPage=1&code={mapped}&pagination=true"
    text = _http_get(url, DAUM_HEADERS)
    if not text:
        return None
    try:
        d = json.loads(text)
        data_list = d.get("data", [])
        if not data_list:
            return None
        stock = data_list[0]
        return {
            "code": mapped,
            "value": float(stock.get("tradePrice", 0)),
            "change": float(stock.get("change_price", 0)),
            "change_pct": float(stock.get("changeRate", 0)) * 100,
            "volume": int(stock.get("accTradeVolume", 0)),
            "source": "daum",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception:
        return None
