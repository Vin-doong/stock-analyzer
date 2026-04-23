"""주식 분석 AI 대시보드 - 메인 앱"""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="주식 분석 AI 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.styles import inject_css

inject_css()

# 사이드바
with st.sidebar:
    st.markdown("### 📊 주식 분석 AI")
    st.page_link("app.py", label="🏠 홈")
    st.page_link("pages/1_dashboard.py", label="📈 대시보드")
    st.page_link("pages/2_analysis.py", label="🔍 종목분석")
    st.page_link("pages/3_screener.py", label="🎯 스크리닝")
    st.page_link("pages/4_ai_recommend.py", label="🤖 AI추천")
    st.page_link("pages/5_backtest.py", label="📊 백테스팅")
    st.page_link("pages/6_watchlist.py", label="⭐ 관심종목")
    st.caption("v1.0 · 투자 책임은 본인")

# 메인 홈
st.markdown("### 📊 주식 분석 AI 대시보드")

CARDS = [
    ("🎯", "종목 스크리닝", "스타일별 (단타/스윙/중장기) AI 추천", "pages/3_screener.py", "home_screen"),
    ("🤖", "AI 실시간 추천", "Claude가 시장 분석 후 즉시 행동 종목 제시", "pages/4_ai_recommend.py", "home_ai"),
    ("🔍", "종목 분석", "개별 종목 기술/재무 분석 + AI 의견", "pages/2_analysis.py", "home_analysis"),
    ("📈", "시장 대시보드", "KOSPI/KOSDAQ/S&P/NASDAQ 현황", "pages/1_dashboard.py", "home_dash"),
    ("📊", "백테스팅", "전략별 과거 수익률 검증", "pages/5_backtest.py", "home_bt"),
    ("⭐", "관심종목", "즐겨찾는 종목 모니터링", "pages/6_watchlist.py", "home_wl"),
]

cols = st.columns(3)
for i, (icon, title, desc, page, key) in enumerate(CARDS):
    with cols[i % 3]:
        st.markdown(
            f'<div class="home-card"><h4>{icon} {title}</h4><p>{desc}</p></div>',
            unsafe_allow_html=True,
        )
        if st.button("열기", key=key, use_container_width=True):
            st.switch_page(page)

st.caption("💡 왼쪽 사이드바에서 기능을 선택하거나 위 카드를 눌러 이동하세요. "
           "AI 분석은 Claude.ai에 복사/붙여넣기로 무료 사용하거나, `.env`에 API 키를 설정하면 앱 내에서 바로 결과 확인 가능.")
