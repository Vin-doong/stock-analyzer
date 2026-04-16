"""종목 스크리닝 페이지"""
import streamlit as st
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ui.styles import inject_css, signal_badge
from ui.components import market_selector, style_selector
from ui.formatters import format_percent
inject_css()

st.title("🎯 종목 스크리닝")

# 사이드바 설정
with st.sidebar:
    market = market_selector("screen_market")
    style = style_selector("screen_style")
    top_n = st.slider("상위 종목 수 (결과)", 5, 50, 20, key="screen_topn")

    from config import SCREEN_SIZES
    scan_label = st.selectbox("분석 범위", list(SCREEN_SIZES.keys()),
                               index=1, key="screen_scan")
    max_scan = SCREEN_SIZES[scan_label]
    est_min = max(1, max_scan // 50)
    st.caption(f"약 {est_min}~{est_min*3}분 소요 예상")

# 스크리닝 실행
if st.button("🔍 스크리닝 시작", type="primary", use_container_width=True):
    with st.spinner(f"{market} 시장에서 {style.value} 스타일로 스크리닝 중... (1-3분 소요)"):
        if market in ("KOSPI", "KOSDAQ"):
            from data.fetcher_kr import get_stock_list
        else:
            from data.fetcher_us import get_stock_list

        from screener.ranker import screen_and_rank

        stock_df = get_stock_list(market)
        if stock_df is None or stock_df.empty:
            st.error("종목 리스트를 불러올 수 없습니다.")
            st.stop()

        results = screen_and_rank(market, style, stock_df, top_n=top_n, max_scan=max_scan)

        if results:
            st.session_state["screen_results"] = results
            st.session_state["screen_market_result"] = market
            st.session_state["screen_style_val"] = style.value
        else:
            st.warning("스크리닝 결과가 없습니다.")

# 결과 표시
if "screen_results" in st.session_state:
    results = st.session_state["screen_results"]
    # 시황 표시
    regime = results[0].get("market_regime", "") if results else ""
    adj = results[0].get("regime_adjustment", 0) if results else 0
    regime_colors = {"강세": "🟢", "중립": "🟡", "약세": "🔴"}
    regime_icon = regime_colors.get(regime, "⚪")

    st.subheader(f"스크리닝 결과 ({st.session_state.get('screen_style_val', '')}, "
                 f"{st.session_state.get('screen_market_result', '')})")

    if regime:
        regime_msg = f"{regime_icon} **시장 상황: {regime}**"
        if adj != 0:
            regime_msg += f" (전체 점수 {adj:+d}점 보정 적용)"
        st.info(regime_msg)
        if regime == "약세":
            st.warning("⚠️ 현재 약세장입니다. 매수 신호가 나오더라도 신중하게 접근하세요.")

    # 결과 테이블
    rows = []
    for i, r in enumerate(results, 1):
        rows.append({
            "순위": i,
            "종목": f"{r['name']} ({r['ticker']})",
            "점수": r["score"],
            "신호": r["signal"],
            "신뢰도": f"{r['confidence']:.0f}%",
            "RSI": f"{r['rsi']:.1f}" if r.get("rsi") is not None else "-",
            "거래량비율": f"{r['volume_ratio']:.1f}x" if r.get("volume_ratio") is not None else "-",
            "등락률": format_percent(r.get("change_pct")),
        })

    df = pd.DataFrame(rows)

    # 신호별 색상
    def color_signal(val):
        colors = {
            "강력매수": "background-color: #00b894; color: white",
            "매수": "background-color: #0984e3; color: white",
            "관망": "background-color: #fdcb6e",
            "매도": "background-color: #e17055; color: white",
            "강력매도": "background-color: #d63031; color: white",
        }
        return colors.get(val, "")

    def color_score(val):
        if val >= 80:
            return "background-color: #55efc4"
        elif val >= 65:
            return "background-color: #81ecec"
        elif val >= 40:
            return "background-color: #ffeaa7"
        elif val >= 20:
            return "background-color: #fab1a0"
        else:
            return "background-color: #ff7675; color: white"

    styled = df.style.map(color_signal, subset=["신호"]).map(color_score, subset=["점수"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # 점수 분해 상세
    st.divider()
    st.subheader("📊 점수 분해 상세")
    st.caption("종목을 선택하면 점수가 어떻게 산출되었는지 확인할 수 있습니다.")

    score_labels = {
        "rsi": "RSI", "macd": "MACD", "bollinger": "볼린저",
        "volume": "거래량", "ma_trend": "이평선추세", "momentum": "모멘텀",
        "per_pbr": "PER/PBR", "roe_growth": "ROE/성장", "revenue": "매출",
    }

    # 종목 선택
    stock_names = [f"{r['name']} ({r['ticker']}) - {r['score']}점" for r in results]
    selected_idx = st.selectbox("종목 선택", range(len(stock_names)),
                                 format_func=lambda i: stock_names[i],
                                 key="score_detail_select")
    selected = results[selected_idx]
    cat_scores = selected.get("category_scores", {})

    if cat_scores:
        from config import SCORING_WEIGHTS, TradingStyle
        style_map = {"단타": TradingStyle.DAY, "스윙": TradingStyle.SWING, "중장기": TradingStyle.LONG}
        current_style = style_map.get(st.session_state.get("screen_style_val", ""), TradingStyle.SWING)
        weights = SCORING_WEIGHTS[current_style]

        detail_rows = []
        for key, score_val in cat_scores.items():
            w = weights.get(key, 0)
            contribution = score_val * w
            detail_rows.append({
                "지표": score_labels.get(key, key),
                "점수": f"{score_val:.1f}",
                "가중치": f"{w*100:.0f}%" if w > 0 else "-",
                "기여도": f"{contribution:.1f}" if w > 0 else "-",
            })

        detail_df = pd.DataFrame(detail_rows)
        st.dataframe(detail_df, use_container_width=True, hide_index=True)

        # 시각적 막대 차트
        from ui.charts import score_breakdown_bar
        st.plotly_chart(score_breakdown_bar(cat_scores), use_container_width=True)
    else:
        st.info("이 종목의 상세 점수 데이터가 없습니다.")

    # AI 분석
    st.divider()
    st.subheader("🤖 AI 분석")
    from ai.clipboard_helper import ai_analyze_or_clipboard, build_screener_prompt
    screen_market = st.session_state.get("screen_market_result", "")
    screen_style = st.session_state.get("screen_style_val", "")
    prompt = build_screener_prompt(results, screen_market, screen_style)
    ai_analyze_or_clipboard(prompt, cache_key=f"ai:screener:{screen_market}:{screen_style}")
