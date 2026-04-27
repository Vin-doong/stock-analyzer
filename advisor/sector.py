"""섹터 회전 분석 - 실시간 기반"""
from advisor.realtime import fetch_quotes_parallel
from datetime import datetime
from typing import Optional
import FinanceDataReader as fdr
from datetime import timedelta


SECTORS = {
    "반도체_대형": [
        ("005930", "삼성전자"),
        ("000660", "SK하이닉스"),
    ],
    "반도체_소부장": [
        ("042700", "한미반도체"),
        ("240810", "원익IPS"),
        ("007660", "이수페타시스"),
        ("067310", "하나마이크론"),
        ("253590", "네오셈"),
        ("213420", "덕산네오룩스"),
        ("357780", "솔브레인"),
        ("089030", "테크윙"),
    ],
    "2차전지": [
        ("373220", "LG에너지솔루션"),
        ("086520", "에코프로"),
        ("009830", "한화솔루션"),
    ],
    "조선_해운": [
        ("042660", "한화오션"),
        ("010140", "삼성중공업"),
        ("011200", "HMM"),
        ("028670", "팬오션"),
    ],
    "IT_플랫폼": [
        ("035420", "NAVER"),
        ("035720", "카카오"),
    ],
    "자동차": [
        ("005380", "현대차"),
        ("000270", "기아"),
    ],
    "방산": [
        ("012450", "한화에어로스페이스"),
        ("079550", "LIG넥스원"),
        ("064350", "현대로템"),
    ],
    "바이오": [
        ("207940", "삼성바이오로직스"),
        ("068270", "셀트리온"),
    ],
    "엔터": [
        ("352820", "하이브"),
        ("041510", "SM"),
        ("035900", "JYP Ent"),
    ],
    "원전_에너지": [
        ("034020", "두산에너빌리티"),
        ("052690", "한전기술"),
    ],
    "AI_SW": [
        ("328130", "루닛"),
        ("022100", "포스코DX"),
    ],
    "건설": [
        ("028260", "삼성물산"),
        ("000720", "현대건설"),
        ("006360", "GS건설"),
    ],
    "전력_케이블": [
        ("001440", "대한전선"),
        ("267260", "HD현대일렉트릭"),
        ("010120", "LS일렉트릭"),
        ("103590", "일진전기"),
        ("298040", "효성중공업"),
    ],
    "화학": [
        ("025860", "남해화학"),
        ("004020", "현대제철"),
        ("011170", "롯데케미칼"),
    ],
}


def analyze_sectors() -> dict:
    """모든 섹터의 오늘 등락 + 5일 수익률 분석"""
    # 모든 티커 수집
    all_tickers = []
    for sector, stocks in SECTORS.items():
        all_tickers.extend([t for t, _ in stocks])

    # 실시간 병렬 조회
    realtime = fetch_quotes_parallel(list(set(all_tickers)))

    # 과거 5일 수익률은 FDR로 별도 조회 (캐시됨)
    result = {}
    for sector, stocks in SECTORS.items():
        members = []
        for ticker, name in stocks:
            rt = realtime.get(ticker)
            if not rt:
                continue

            # 5일 수익률 계산
            ret_5d = 0
            try:
                now = datetime.now()
                df = fdr.DataReader(
                    ticker,
                    (now - timedelta(days=10)).strftime("%Y-%m-%d"),
                    now.strftime("%Y-%m-%d"),
                )
                if df is not None and len(df) >= 6:
                    ret_5d = (rt["price"] / df["Close"].iloc[-6] - 1) * 100
            except Exception:
                pass

            members.append({
                "ticker": ticker,
                "name": name,
                "price": rt["price"],
                "change_pct": rt["change_pct"],
                "ret_5d": ret_5d,
                "volume": rt.get("volume", 0),
            })

        if members:
            avg_today = sum(m["change_pct"] for m in members) / len(members)
            avg_5d = sum(m["ret_5d"] for m in members) / len(members)
            members.sort(key=lambda x: -x["change_pct"])

            result[sector] = {
                "avg_today": avg_today,
                "avg_5d": avg_5d,
                "members": members,
                "top": members[0],
                "count": len(members),
            }

    return result


def sector_ranking(by: str = "today") -> list:
    """섹터 랭킹

    Args:
        by: "today" | "5d"
    """
    sectors = analyze_sectors()
    key = "avg_today" if by == "today" else "avg_5d"
    return sorted(sectors.items(), key=lambda x: -x[1][key])


def hot_sectors() -> list:
    """핫한 섹터 (당일 + 5일 모두 상승)"""
    sectors = analyze_sectors()
    hot = []
    for name, data in sectors.items():
        if data["avg_today"] > 1 and data["avg_5d"] > 3:
            hot.append((name, data))
    return sorted(hot, key=lambda x: -x[1]["avg_5d"])


def cold_sectors() -> list:
    """차가운 섹터 (당일 + 5일 모두 하락)"""
    sectors = analyze_sectors()
    cold = []
    for name, data in sectors.items():
        if data["avg_today"] < 0 and data["avg_5d"] < 0:
            cold.append((name, data))
    return sorted(cold, key=lambda x: x[1]["avg_5d"])
