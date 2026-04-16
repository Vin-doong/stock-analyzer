"""AI 분석 오케스트레이터"""
from data import cache
from config import CACHE_TTL, TradingStyle, AI_PROVIDER
from ai import prompts


def analyze(prompt: str, **kwargs) -> str | None:
    """AI provider에 따라 분석 요청을 라우팅"""
    if AI_PROVIDER == "openai":
        from ai.openai_client import analyze as _analyze
    else:
        from ai.claude_client import analyze as _analyze
    return _analyze(prompt, **kwargs)


def analyze_stock(ticker: str, name: str, market: str, style: TradingStyle,
                  technical_summary: dict, fundamental_summary: dict,
                  composite_score: float, signal: str) -> str | None:
    """개별 종목 AI 분석"""
    cache_key = f"ai:stock:{ticker}:{style.value}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # 기술적 지표 포맷팅
    tech_lines = []
    for k, v in technical_summary.items():
        if v is not None and k != "close":
            tech_lines.append(f"- {k}: {v}")
    tech_str = "\n".join(tech_lines) if tech_lines else "데이터 없음"

    # 재무 데이터 포맷팅
    fund_lines = []
    for k, v in fundamental_summary.items():
        if v is not None:
            fund_lines.append(f"- {k}: {v}")
    fund_str = "\n".join(fund_lines) if fund_lines else "데이터 없음"

    prompt = prompts.STOCK_ANALYSIS_PROMPT.format(
        name=name, ticker=ticker, market=market, style=style.value,
        technical_summary=tech_str, fundamental_summary=fund_str,
        composite_score=composite_score, signal=signal,
    )

    result = analyze(prompt)
    if result:
        cache.set(cache_key, result, CACHE_TTL["ai_analysis"])
    return result


def analyze_screener_results(stock_list: list[dict], market: str,
                              style: TradingStyle) -> str | None:
    """스크리너 결과 AI 분석"""
    cache_key = f"ai:screener:{market}:{style.value}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    lines = []
    for i, s in enumerate(stock_list[:15], 1):
        lines.append(
            f"{i}. {s['name']}({s['ticker']}) - 점수: {s['score']}, "
            f"신호: {s['signal']}"
        )
    stock_str = "\n".join(lines)

    prompt = prompts.SCREENER_SUMMARY_PROMPT.format(
        style=style.value, market=market, stock_list=stock_str,
    )

    result = analyze(prompt)
    if result:
        cache.set(cache_key, result, CACHE_TTL["ai_analysis"])
    return result


def get_realtime_recommendation(screening_results: list[dict], market: str,
                                 style: TradingStyle) -> str | None:
    """실시간 AI 추천"""
    cache_key = f"ai:realtime:{market}:{style.value}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    lines = []
    for s in screening_results[:10]:
        lines.append(
            f"- {s['name']}({s['ticker']}): 점수 {s['score']}, "
            f"신호 {s['signal']}, RSI {s.get('rsi', 'N/A')}, "
            f"거래량비율 {s.get('volume_ratio', 'N/A')}"
        )
    results_str = "\n".join(lines)

    prompt = prompts.REALTIME_RECOMMENDATION_PROMPT.format(
        style=style.value, market=market, screening_results=results_str,
    )

    result = analyze(prompt, max_tokens=1500)
    if result:
        cache.set(cache_key, result, CACHE_TTL["ai_analysis"])
    return result


def analyze_market_overview(index_data: str, highlights: str) -> str | None:
    """시장 개요 AI 분석"""
    cache_key = "ai:market_overview"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    prompt = prompts.MARKET_OVERVIEW_PROMPT.format(
        index_data=index_data, market_highlights=highlights,
    )

    result = analyze(prompt)
    if result:
        cache.set(cache_key, result, CACHE_TTL["ai_analysis"])
    return result
