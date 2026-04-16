"""종목 분석 페이지"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ui.styles import inject_css, score_card
from ui.components import market_selector, style_selector, period_selector
from ui.charts import candlestick_chart, indicator_chart, score_gauge, score_breakdown_bar
from ui.formatters import format_percent, format_price
inject_css()

st.title("🔍 종목 분석")

# 사이드바 설정
with st.sidebar:
    market = market_selector("analysis_market")
    style = style_selector("analysis_style")
    days = period_selector("analysis_period")

# 종목 리스트 로드
@st.cache_data(ttl=3600)
def load_stock_list(market):
    if market in ("KOSPI", "KOSDAQ"):
        from data.fetcher_kr import get_stock_list
    else:
        from data.fetcher_us import get_stock_list
    return get_stock_list(market)

stock_df = load_stock_list(market)
if stock_df is None or stock_df.empty:
    st.error("종목 리스트를 불러올 수 없습니다.")
    st.stop()

# 종목 선택
options = stock_df.to_dict("records")
display = [f"{r.get('name', r['ticker'])} ({r['ticker']})" for r in options]
selected_idx = st.selectbox("종목 검색", range(len(display)),
                             format_func=lambda i: display[i])
stock = options[selected_idx]
ticker = stock["ticker"]
name = stock.get("name", ticker)

st.subheader(f"{name} ({ticker})")

# 데이터 로드
@st.cache_data(ttl=300)
def load_data(ticker, market, days):
    if market in ("KOSPI", "KOSDAQ"):
        from data.fetcher_kr import get_price_data, get_fundamental_data
    else:
        from data.fetcher_us import get_price_data, get_fundamental_data
    price_df = get_price_data(ticker, days)
    fund = get_fundamental_data(ticker)
    return price_df, fund

with st.spinner("데이터 로딩 중..."):
    df, fund = load_data(ticker, market, days)

if df is None or df.empty:
    st.error("가격 데이터를 불러올 수 없습니다.")
    st.stop()

# 기술적 지표 추가
from analysis.technical import add_all_indicators, get_technical_summary
from analysis.scoring import score_stock

df_ind = add_all_indicators(df)
tech_summary = get_technical_summary(df_ind)
score_result = score_stock(ticker, name, df, style, fund)

# 점수 카드
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    st.plotly_chart(score_gauge(score_result.composite_score, f"{style.value} 점수"),
                     use_container_width=True)
with col2:
    st.plotly_chart(score_breakdown_bar(score_result.category_scores),
                     use_container_width=True)
with col3:
    st.markdown(score_card(score_result.composite_score, score_result.signal),
                unsafe_allow_html=True)
    st.metric("신뢰도", f"{score_result.confidence:.0f}%")
    if tech_summary.get("change_pct") is not None:
        st.metric("등락률", format_percent(tech_summary["change_pct"]))

# 차트 탭
tab1, tab2, tab3, tab4 = st.tabs(["📊 가격 차트", "📉 기술적 지표", "📋 재무 데이터", "🤖 AI 분석"])

with tab1:
    st.plotly_chart(candlestick_chart(df_ind), use_container_width=True)

with tab2:
    ind_col1, ind_col2 = st.columns(2)
    with ind_col1:
        st.markdown("**RSI**")
        st.plotly_chart(indicator_chart(df_ind, "RSI"), use_container_width=True)
    with ind_col2:
        st.markdown("**MACD**")
        st.plotly_chart(indicator_chart(df_ind, "MACD"), use_container_width=True)

    # 지표 요약 테이블
    st.markdown("**지표 요약**")
    summary_cols = st.columns(4)
    indicators = [
        ("RSI", tech_summary.get("rsi")),
        ("MACD Hist", tech_summary.get("macd_hist")),
        ("볼린저 %B", tech_summary.get("bb_pctb")),
        ("거래량 비율", tech_summary.get("volume_ratio")),
        ("ADX", tech_summary.get("adx")),
        ("스토캐스틱 %K", tech_summary.get("stoch_k")),
    ]
    for i, (label, value) in enumerate(indicators):
        with summary_cols[i % 4]:
            val_str = f"{value:.2f}" if value is not None else "-"
            st.metric(label, val_str)

with tab3:
    if fund:
        fund_col1, fund_col2 = st.columns(2)
        with fund_col1:
            st.metric("PER", f"{fund.get('per', '-')}")
            st.metric("PBR", f"{fund.get('pbr', '-')}")
            st.metric("EPS", f"{fund.get('eps', '-')}")
        with fund_col2:
            roe = fund.get("roe")
            if roe is not None:
                roe_str = f"{roe*100:.1f}%" if abs(roe) < 1 else f"{roe:.1f}%"
                st.metric("ROE", roe_str)
            else:
                st.metric("ROE", "-")
            rev_g = fund.get("revenue_growth")
            if rev_g is not None:
                rg_str = f"{rev_g*100:.1f}%" if abs(rev_g) < 5 else f"{rev_g:.1f}%"
                st.metric("매출 성장률", rg_str)
            else:
                st.metric("매출 성장률", "-")
            op_m = fund.get("operating_margin")
            if op_m is not None:
                om_str = f"{op_m*100:.1f}%" if abs(op_m) < 1 else f"{op_m:.1f}%"
                st.metric("영업이익률", om_str)
            else:
                st.metric("영업이익률", "-")
    else:
        st.info("재무 데이터가 없습니다.")

with tab4:
    from ai.clipboard_helper import ai_analyze_or_clipboard, build_stock_prompt
    prompt = build_stock_prompt(
        name, ticker, market, style.value,
        tech_summary, fund or {},
        score_result.composite_score, score_result.signal,
    )
    ai_analyze_or_clipboard(prompt, cache_key=f"ai:stock:{ticker}:{style.value}")

# 관심종목 추가 버튼
st.divider()
from screener.watchlist import exists, add, remove
if exists(ticker):
    if st.button(f"⭐ 관심종목에서 제거", key="remove_watch"):
        remove(ticker)
        st.success(f"{name} 관심종목에서 제거됨")
        st.rerun()
else:
    if st.button(f"☆ 관심종목에 추가", key="add_watch"):
        add(ticker, name, market)
        st.success(f"{name} 관심종목에 추가됨")
        st.rerun()
