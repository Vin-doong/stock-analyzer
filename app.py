"""주식 분석 AI 대시보드 - 메인 앱"""
import streamlit as st
import sys
import os

# 프로젝트 루트를 path에 추가
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
    st.title("📊 주식 분석 AI")
    st.divider()
    st.markdown("**메뉴**")
    st.page_link("app.py", label="🏠 홈", icon=None)
    st.page_link("pages/1_dashboard.py", label="📈 대시보드")
    st.page_link("pages/2_analysis.py", label="🔍 종목분석")
    st.page_link("pages/3_screener.py", label="🎯 종목스크리닝")
    st.page_link("pages/4_ai_recommend.py", label="🤖 AI추천")
    st.page_link("pages/5_backtest.py", label="📊 백테스팅")
    st.page_link("pages/6_watchlist.py", label="⭐ 관심종목")
    st.divider()
    st.caption("v1.0 | 투자의 책임은 본인에게 있습니다")

# 메인 홈 화면
st.title("📊 주식 분석 AI 대시보드")
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🎯 종목 스크리닝")
    st.markdown("한국/미국 주식을 AI가 분석하여 단타, 스윙, 중장기 투자 스타일별로 추천합니다.")
    if st.button("스크리닝 시작", key="home_screen"):
        st.switch_page("pages/3_screener.py")

with col2:
    st.markdown("### 🤖 AI 실시간 추천")
    st.markdown("Claude AI가 시장을 분석하고 즉시 행동 가능한 종목을 추천합니다.")
    if st.button("AI 추천 보기", key="home_ai"):
        st.switch_page("pages/4_ai_recommend.py")

with col3:
    st.markdown("### 🔍 종목 분석")
    st.markdown("개별 종목의 기술적/재무적 분석과 AI 투자 의견을 확인합니다.")
    if st.button("종목 분석", key="home_analysis"):
        st.switch_page("pages/2_analysis.py")

st.markdown("---")

col4, col5 = st.columns(2)
with col4:
    st.markdown("### 📈 시장 대시보드")
    st.markdown("KOSPI, KOSDAQ, S&P 500, NASDAQ 지수 현황과 시장 요약을 확인합니다.")

with col5:
    st.markdown("### 📊 백테스팅")
    st.markdown("골든크로스, RSI반전 등 전략의 과거 수익률을 검증합니다.")

st.markdown("---")
st.info("💡 **시작하기**: 왼쪽 사이드바에서 원하는 기능을 선택하세요. AI 분석은 Claude.ai에 복사/붙여넣기로 무료 사용하거나, .env에 API 키를 설정하면 앱 내에서 바로 결과를 확인할 수 있습니다.")
