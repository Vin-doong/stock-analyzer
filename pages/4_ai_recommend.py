"""AI 실시간 추천 페이지"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ui.styles import inject_css, score_card
from ui.components import market_selector, style_selector
inject_css()

st.title("🤖 AI 실시간 추천")
st.markdown("Claude AI가 시장을 분석하고 즉시 행동 가능한 종목을 추천합니다.")

# 사이드바 설정
with st.sidebar:
    market = market_selector("ai_market")
    style = style_selector("ai_style")

    from config import SCREEN_SIZES
    scan_label = st.selectbox("분석 범위", list(SCREEN_SIZES.keys()),
                               index=1, key="ai_scan")
    max_scan = SCREEN_SIZES[scan_label]

st.divider()

# 실시간 추천 실행
if st.button("🚀 AI 추천 시작", type="primary", use_container_width=True):
    # Step 1: 스크리닝
    progress = st.progress(0, text="종목 스크리닝 중...")

    if market in ("KOSPI", "KOSDAQ"):
        from data.fetcher_kr import get_stock_list
    else:
        from data.fetcher_us import get_stock_list

    from screener.ranker import screen_and_rank

    stock_df = get_stock_list(market)
    if stock_df is None or stock_df.empty:
        st.error("종목 리스트를 불러올 수 없습니다.")
        st.stop()

    progress.progress(20, text="종목 점수 산출 중... (1-2분)")
    results = screen_and_rank(market, style, stock_df, top_n=15, max_scan=max_scan)

    if not results:
        st.warning("스크리닝 결과가 없습니다.")
        st.stop()

    progress.progress(60, text="상위 종목 분석 완료")

    # Step 2: 상위 종목 표시
    st.subheader(f"📊 스크리닝 TOP 10 ({style.value}, {market})")
    for i, r in enumerate(results[:10], 1):
        cols = st.columns([0.5, 2, 1, 1, 1])
        with cols[0]:
            st.markdown(f"**{i}**")
        with cols[1]:
            st.markdown(f"**{r['name']}** ({r['ticker']})")
        with cols[2]:
            st.markdown(score_card(r['score'], r['signal']), unsafe_allow_html=True)
        with cols[3]:
            rsi = r.get("rsi")
            st.metric("RSI", f"{rsi:.1f}" if rsi else "-")
        with cols[4]:
            vr = r.get("volume_ratio")
            st.metric("거래량", f"{vr:.1f}x" if vr else "-")

    progress.progress(100, text="스크리닝 완료!")

    st.divider()

    # Step 3: AI 추천
    st.subheader("🤖 AI 추천 받기")
    from ai.clipboard_helper import ai_analyze_or_clipboard, build_recommendation_prompt
    prompt = build_recommendation_prompt(results, market, style.value)
    ai_analyze_or_clipboard(prompt, cache_key=f"ai:realtime:{market}:{style.value}")

st.divider()
st.caption("⚠️ AI 추천은 참고용이며 투자의 최종 결정과 책임은 본인에게 있습니다.")
