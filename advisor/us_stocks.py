"""미국 주식 장기 적립 포트폴리오 관리

본인의 미국 주식은 매월 자동 적립 + 장기 보유 목적이므로
스윙 트레이딩 규칙 대신 '누적 성과 추적 + 포트폴리오 건강도'에 초점.

데이터 소스:
- 실시간 가격: 네이버 API (naver_us.py) - ~100ms 실시간
- 펀더멘털 지표: yfinance - PER, 배당률 등
"""
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional
from advisor.naver_us import (
    fetch_us_realtime,
    fetch_us_realtime_parallel,
    fetch_krw_usd_rate_naver,
    fetch_us_with_detail,
)


def fetch_us_quote(ticker: str) -> Optional[dict]:
    """미국 주식 시세 조회 (yfinance 기반, 15~20분 지연)"""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        hist = t.history(period="5d")
        if hist.empty:
            return None

        current = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else current

        # 배당률 계산 (더 안정적인 방법)
        # trailingAnnualDividendRate = 지난 12개월 배당금 합계 (USD)
        # 이를 현재가로 나누면 정확한 배당률
        div_rate = info.get("trailingAnnualDividendRate")
        div_yield_pct = None
        if div_rate and current > 0:
            div_yield_pct = (div_rate / current) * 100
        else:
            # 폴백: dividendYield 필드 (포맷 불일치 있음)
            raw = info.get("dividendYield")
            if raw is not None:
                if raw > 1:
                    div_yield_pct = raw
                else:
                    div_yield_pct = raw * 100

        # 안전장치: 비현실적 배당률은 None 처리 (대부분 yfinance 버그)
        if div_yield_pct is not None and (div_yield_pct > 15 or div_yield_pct < 0):
            div_yield_pct = None

        return {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName", ticker),
            "price": current,
            "prev_close": prev,
            "change": current - prev,
            "change_pct": (current / prev - 1) * 100 if prev else 0,
            "market_cap": info.get("marketCap"),
            "pe": info.get("trailingPE"),
            "dividend_yield": div_yield_pct,
            "sector": info.get("sector"),
            "fifty_day_avg": info.get("fiftyDayAverage"),
            "two_hundred_day_avg": info.get("twoHundredDayAverage"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "beta": info.get("beta"),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return None


def fetch_us_quotes_parallel(tickers: list[str]) -> dict:
    """미국 주식 병렬 조회 (네이버 우선, yfinance 폴백)"""
    # 1차: 네이버 실시간 API (빠름)
    results = fetch_us_realtime_parallel(tickers)

    # 2차: 못 가져온 것만 yfinance 폴백
    missing = [t for t in tickers if t not in results]
    if missing:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_us_quote, t): t for t in missing}
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    data = future.result()
                    if data:
                        results[ticker] = data
                except Exception:
                    pass

    return results


def fetch_krw_usd_rate() -> float:
    """원-달러 환율 조회 (네이버 우선, yfinance 폴백)"""
    return fetch_krw_usd_rate_naver()


def evaluate_us_portfolio(holdings: list[dict]) -> dict:
    """미국 주식 포트폴리오 평가"""
    tickers = [h["name"] for h in holdings if h.get("name")]
    # 티커 매핑 (한글명 → 티커)
    ticker_map = {
        "SCHD": "SCHD",
        "VOO": "VOO",
        "QQQ": "QQQ",
        "JNJ": "JNJ",
        "엔비디아": "NVDA",
        "NVDA": "NVDA",
    }

    mapped = {}
    for h in holdings:
        name = h.get("name", "")
        symbol = ticker_map.get(name, name)
        mapped[symbol] = h

    # 실시간 조회 (네이버)
    realtime_quotes = fetch_us_realtime_parallel(list(mapped.keys()))
    krw_rate = fetch_krw_usd_rate()

    total_value_usd = 0
    items = []

    # 상세 정보는 별도 병렬 조회 (yfinance, 느림)
    def get_detail(sym):
        try:
            return fetch_us_with_detail(sym)
        except Exception:
            return None

    detail_futures = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        for symbol in mapped.keys():
            detail_futures[executor.submit(get_detail, symbol)] = symbol

        detail_results = {}
        for future in as_completed(detail_futures):
            symbol = detail_futures[future]
            try:
                detail_results[symbol] = future.result()
            except Exception:
                pass

    for symbol, holding in mapped.items():
        rt = realtime_quotes.get(symbol)
        detail = detail_results.get(symbol) or {}

        if not rt:
            items.append({
                "symbol": symbol,
                "name": holding.get("name", symbol),
                "error": "조회 실패",
            })
            continue

        qty = holding.get("qty", 0)
        monthly = holding.get("monthly", 0)

        value_usd = qty * rt["price"]
        value_krw = value_usd * krw_rate
        total_value_usd += value_usd

        items.append({
            "symbol": symbol,
            "name": holding.get("name", symbol),
            "full_name": rt.get("name") or detail.get("name"),
            "exchange": rt.get("exchange"),
            "delay_name": rt.get("delay_name"),
            "qty": qty,
            "price_usd": rt["price"],
            "value_usd": value_usd,
            "value_krw": value_krw,
            "change_pct": rt["change_pct"],
            "monthly_krw": monthly,
            "dividend_yield": detail.get("dividend_yield"),
            "pe": detail.get("pe"),
            "sector": detail.get("sector"),
            "fifty_day_avg": detail.get("fifty_day_avg"),
            "two_hundred_day_avg": detail.get("two_hundred_day_avg"),
            "52w_high": detail.get("fifty_two_week_high"),
            "52w_low": detail.get("fifty_two_week_low"),
            "beta": detail.get("beta"),
        })

    return {
        "items": items,
        "total_value_usd": total_value_usd,
        "total_value_krw": total_value_usd * krw_rate,
        "usd_krw_rate": krw_rate,
        "timestamp": datetime.now().isoformat(),
    }


# 대안 추천 후보 ETF/종목
ALTERNATIVE_CANDIDATES = {
    # 배당 성장 카테고리
    "DGRO": "iShares Core Dividend Growth (배당성장 ETF)",
    "VIG": "Vanguard Dividend Appreciation (배당성장 ETF)",
    "SCHY": "Schwab International Dividend Equity (해외배당)",
    # 브로드 시장 카테고리
    "VTI": "Vanguard Total Stock Market (미국 전체시장)",
    "VXUS": "Vanguard Total International Stock (해외전체)",
    # 섹터 집중
    "SOXX": "iShares Semiconductor ETF (반도체)",
    "SMH": "VanEck Semiconductor ETF (반도체)",
    "XLK": "Technology Select Sector (기술섹터)",
    "XLV": "Health Care Select Sector (헬스케어섹터)",
    # 신흥국/국제
    "IEMG": "iShares Core MSCI Emerging Markets (신흥국)",
    "IEFA": "iShares Core MSCI EAFE (선진국 해외)",
    # 채권/안전자산
    "AGG": "iShares Core US Aggregate Bond (채권)",
    "GLD": "SPDR Gold Shares (금)",
    # 개별 우량주
    "MSFT": "Microsoft",
    "AAPL": "Apple",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "AVGO": "Broadcom",
    "BRK-B": "Berkshire Hathaway",
    "V": "Visa",
    "COST": "Costco",
}


def evaluate_alternatives() -> list[dict]:
    """대안 후보 종목 평가"""
    symbols = list(ALTERNATIVE_CANDIDATES.keys())
    quotes = fetch_us_quotes_parallel(symbols)

    results = []
    for symbol, desc in ALTERNATIVE_CANDIDATES.items():
        q = quotes.get(symbol)
        if not q:
            continue

        price = q["price"]
        pe = q.get("pe")
        div = q.get("dividend_yield")
        ma50 = q.get("fifty_day_avg")
        ma200 = q.get("two_hundred_day_avg")
        high52 = q.get("fifty_two_week_high")

        # 간단한 건강도 점수
        health = 50
        if ma50 and price > ma50:
            health += 15
        if ma200 and price > ma200:
            health += 15
        if high52 and high52 > 0:
            off_high = (price / high52 - 1) * 100
            if off_high > -5:
                health += 10
            elif off_high < -20:
                health -= 10

        # div는 이미 percentage 형식
        results.append({
            "symbol": symbol,
            "description": desc,
            "price": price,
            "change_pct": q["change_pct"],
            "pe": pe,
            "dividend_yield": div,
            "sector": q.get("sector"),
            "ma50_above": price > ma50 if ma50 else None,
            "ma200_above": price > ma200 if ma200 else None,
            "off_52w_high": (price / high52 - 1) * 100 if high52 else None,
            "health_score": health,
        })

    return sorted(results, key=lambda x: -x["health_score"])
