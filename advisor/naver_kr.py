"""네이버 금융 기반 한국 주식 실시간 시세

엔드포인트: polling.finance.naver.com/api/realtime/domestic/stock/{code}

특징:
- 실시간 (delayTime: 0)
- API 키 불필요, 무료
- 빠름 (44~143ms)
- 데이터 품질 좋음 (숫자형, 시가총액 포함)
- 네이버 공식 내부 API
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


def fetch_kr_naver(ticker: str) -> Optional[dict]:
    """네이버에서 한국 주식 실시간 시세 조회

    Returns:
        {
            "ticker": "005930",
            "name": "삼성전자",
            "exchange": "KOSPI",
            "price": 72000,
            "change": 1200,
            "change_pct": 1.69,
            "open": 71500,
            "high": 72500,
            "low": 70800,
            "volume": 8500000,
            "trade_value": 610000000000,
            "market_cap": 430000000000000,
            "market_status": "CLOSE",
            "source": "naver",
            ...
        }
    """
    url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{ticker}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as resp:
            d = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    datas = d.get("datas", [])
    if not datas:
        return None

    s = datas[0]
    exchange = s.get("stockExchangeType", {})

    def _num(key, default=0):
        """필드 값을 숫자로 안전하게 변환"""
        v = s.get(key)
        if v is None:
            return default
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            try:
                return float(v.replace(",", ""))
            except (ValueError, AttributeError):
                return default
        return default

    price = _num("closePriceRaw")
    change = _num("compareToPreviousClosePriceRaw")

    return {
        "ticker": ticker,
        "name": s.get("stockName"),
        "exchange": exchange.get("nameKor") or exchange.get("nameEng"),
        "price": price,
        "prev_close": price - change,
        "change": change,
        "change_pct": _num("fluctuationsRatioRaw"),
        "open": _num("openPriceRaw"),
        "high": _num("highPriceRaw"),
        "low": _num("lowPriceRaw"),
        "volume": int(_num("accumulatedTradingVolumeRaw")),
        "trade_value": int(_num("accumulatedTradingValueRaw")),
        "market_cap": int(_num("marketValueFullRaw")),
        "market_status": s.get("marketStatus"),
        "local_traded_at": s.get("localTradedAt"),
        "isin_code": s.get("isinCode"),
        "delay_minutes": exchange.get("delayTime", 0),
        "source": "naver",
        "timestamp": datetime.now().isoformat(),
    }


def fetch_kr_naver_parallel(tickers: list[str], max_workers: int = 10) -> dict:
    """네이버 한국주식 병렬 조회"""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_kr_naver, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                data = future.result()
                if data:
                    results[ticker] = data
            except Exception:
                pass
    return results


def _to_num(v, default=0):
    """필드 값을 숫자로 안전하게 변환"""
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        try:
            return float(v.replace(",", ""))
        except (ValueError, AttributeError):
            return default
    return default


def fetch_kr_index_naver(index_code: str) -> Optional[dict]:
    """네이버 한국 지수 조회 (KOSPI, KOSDAQ)

    Args:
        index_code: "KOSPI" or "KOSDAQ"
    """
    url = f"https://polling.finance.naver.com/api/realtime/domestic/index/{index_code}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as resp:
            d = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    datas = d.get("datas", [])
    if not datas:
        return None

    s = datas[0]
    return {
        "code": index_code,
        "name": s.get("indexName") or s.get("indexCodeName"),
        "value": _to_num(s.get("closePriceRaw")),
        "change": _to_num(s.get("compareToPreviousClosePriceRaw")),
        "change_pct": _to_num(s.get("fluctuationsRatioRaw")),
        "open": _to_num(s.get("openPriceRaw")),
        "high": _to_num(s.get("highPriceRaw")),
        "low": _to_num(s.get("lowPriceRaw")),
        "volume": int(_to_num(s.get("accumulatedTradingVolumeRaw"))),
        "market_status": s.get("marketStatus"),
        "source": "naver",
        "timestamp": datetime.now().isoformat(),
    }
