"""종목/시장 분석 모듈 - Claude가 조언할 때 필요한 데이터 수집"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 경로 추가
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def fetch_stock_price(ticker: str, days: int = 90) -> dict:
    """종목 실시간 시세 + 기술적 지표 조회

    실시간 가격은 다음금융 API (ms 단위),
    기술적 지표는 FDR 과거 데이터 기반으로 계산.
    """
    from advisor.realtime import fetch_quote

    # 1. 실시간 가격 (다음금융)
    rt = fetch_quote(ticker)
    if not rt:
        return {}

    # 2. 기술적 지표용 과거 데이터
    from data.fetcher_kr import get_price_data
    from analysis.technical import add_all_indicators, get_technical_summary
    df = get_price_data(ticker, days=days)

    summary = {}
    if df is not None and not df.empty:
        df_ind = add_all_indicators(df)
        summary = get_technical_summary(df_ind)

    current = rt["price"]
    ma20 = summary.get("ma20")

    # 중장기 모멘텀 (60일/90일 수익률)
    ret_60d = None
    ret_90d = None
    try:
        if df is not None and len(df) >= 61:
            ret_60d = (current / float(df["Close"].iloc[-61]) - 1) * 100
        if df is not None and len(df) >= 91:
            ret_90d = (current / float(df["Close"].iloc[-91]) - 1) * 100
        elif df is not None and not df.empty:
            ret_90d = (current / float(df["Close"].iloc[0]) - 1) * 100
    except Exception:
        pass

    return {
        "ticker": ticker,
        "name": rt.get("name"),
        "current": current,
        "open": rt.get("open", 0),
        "high": rt.get("high", 0),
        "low": rt.get("low", 0),
        "prev_close": rt.get("prev_close", 0),
        "day_change_pct": rt.get("change_pct", 0),
        "volume": rt.get("volume", 0),
        "market_cap": rt.get("market_cap"),
        "source": rt.get("source"),
        "timestamp": rt.get("timestamp"),
        # 기술적 지표 (과거 데이터 기반)
        "rsi": summary.get("rsi"),
        "macd_hist": summary.get("macd_hist"),
        "bb_pctb": summary.get("bb_pctb"),
        "volume_ratio": summary.get("volume_ratio"),
        "adx": summary.get("adx"),
        "ma5": summary.get("ma5"),
        "ma20": ma20,
        "ma60": summary.get("ma60"),
        "above_ma20": current > ma20 if ma20 else None,
        # 중장기 모멘텀
        "ret_60d": ret_60d,
        "ret_90d": ret_90d,
    }


def fetch_market_overview() -> dict:
    """시장 전체 개요 (실시간 KOSPI/KOSDAQ + 미국 지수)"""
    from advisor.naver_kr import fetch_kr_index_naver
    from advisor.realtime import fetch_index_daum
    import FinanceDataReader as fdr

    now = datetime.now()
    result = {"timestamp": now.strftime("%Y-%m-%d %H:%M")}

    # 한국 지수: 네이버 우선, 다음 폴백, FDR 최종 폴백
    for code, key in [("KOSPI", "kospi"), ("KOSDAQ", "kosdaq")]:
        # 1차: 네이버
        d = fetch_kr_index_naver(code)
        if d and d.get("value", 0) > 0:
            result[key] = {
                "value": d["value"],
                "day_change": d["change_pct"],
            }
            continue

        # 2차: 다음
        d = fetch_index_daum(code)
        if d:
            result[key] = {
                "value": d["value"],
                "day_change": d["change_pct"],
            }
            continue

        # 3차: FDR
        try:
            fdr_code = "KS11" if code == "KOSPI" else "KQ11"
            df = fdr.DataReader(
                fdr_code,
                (now - timedelta(days=90)).strftime("%Y-%m-%d"),
                now.strftime("%Y-%m-%d"),
            )
            if df is not None and not df.empty:
                c = float(df["Close"].iloc[-1])
                pc = float(df["Close"].iloc[-2]) if len(df) >= 2 else c
                result[key] = {
                    "value": c,
                    "day_change": (c / pc - 1) * 100,
                }
        except Exception:
            pass

    # 5일/20일 수익률은 FDR에서 추가 조회
    for code, key in [("KS11", "kospi"), ("KQ11", "kosdaq")]:
        if key not in result:
            continue
        try:
            df = fdr.DataReader(
                code,
                (now - timedelta(days=90)).strftime("%Y-%m-%d"),
                now.strftime("%Y-%m-%d"),
            )
            if df is not None and len(df) >= 21:
                c = result[key]["value"]
                result[key]["ret_5d"] = (c / df["Close"].iloc[-6] - 1) * 100
                result[key]["ret_20d"] = (c / df["Close"].iloc[-21] - 1) * 100
        except Exception:
            pass

    # 미국 지수 (yfinance는 15분 지연이지만 장 열렸을 때만 사용)
    try:
        import yfinance as yf
        for code, key in [("^GSPC", "sp500"), ("^IXIC", "nasdaq")]:
            try:
                t = yf.Ticker(code)
                df = t.history(period="5d")
                if df.empty:
                    continue
                c = float(df["Close"].iloc[-1])
                pc = float(df["Close"].iloc[-2])
                result[key] = {"value": c, "day_change": (c / pc - 1) * 100}
            except Exception:
                pass
    except Exception:
        pass

    return result


def fetch_holdings_realtime() -> list[dict]:
    """현재 보유 종목 전부 실시간 조회 (병렬)"""
    from advisor.realtime import fetch_quotes_parallel
    from advisor.portfolio import get_swing_holdings

    holdings = get_swing_holdings()
    if not holdings:
        return []

    tickers = [h["ticker"] for h in holdings]
    realtime = fetch_quotes_parallel(tickers)

    result = []
    for h in holdings:
        rt = realtime.get(h["ticker"], {})
        current = rt.get("price", h["avg_price"])
        qty = h["qty"]
        avg = h["avg_price"]
        result.append({
            **h,
            "current": current,
            "day_change_pct": rt.get("change_pct", 0),
            "value": qty * current,
            "pnl": (current - avg) * qty,
            "pnl_pct": (current / avg - 1) * 100 if avg else 0,
        })
    return result


def fetch_sector_leaders() -> dict:
    """주요 섹터별 리딩주 간단 체크"""
    import FinanceDataReader as fdr
    now = datetime.now()
    start = (now - timedelta(days=10)).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")

    sectors = {
        "반도체": [("005930", "삼성전자"), ("000660", "SK하이닉스"), ("042700", "한미반도체")],
        "조선": [("042660", "한화오션"), ("010140", "삼성중공업")],
        "2차전지": [("373220", "LG에너지솔루션"), ("009830", "한화솔루션")],
        "바이오": [("207940", "삼성바이오"), ("068270", "셀트리온")],
        "방산": [("012450", "한화에어로스페이스"), ("079550", "LIG넥스원")],
        "IT": [("035420", "NAVER"), ("035720", "카카오")],
    }

    result = {}
    for sector, stocks in sectors.items():
        sector_data = []
        total_change = 0
        count = 0
        for ticker, name in stocks:
            try:
                df = fdr.DataReader(ticker, start, end)
                if df is None or df.empty or len(df) < 2:
                    continue
                c = float(df["Close"].iloc[-1])
                pc = float(df["Close"].iloc[-2])
                chg = (c / pc - 1) * 100
                sector_data.append({"name": name, "price": c, "change": chg})
                total_change += chg
                count += 1
            except Exception:
                pass
        if count > 0:
            result[sector] = {
                "avg_change": total_change / count,
                "leaders": sector_data,
            }
    return result
