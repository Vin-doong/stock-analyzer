"""관심종목 페이지"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ui.styles import inject_css, signal_badge
from ui.components import style_selector
from ui.formatters import format_percent
inject_css()

st.title("⭐ 관심종목")

style = style_selector("watch_style")

from screener.watchlist import get_all, remove

watchlist = get_all()

if not watchlist:
    st.info("관심종목이 없습니다. 종목분석 페이지에서 종목을 추가해보세요.")
    st.stop()

st.markdown(f"**{len(watchlist)}개 종목** | {style.value} 관점 점수")

# 점수 일괄 계산
if st.button("🔄 점수 업데이트", key="update_scores"):
    progress = st.progress(0)
    results = []

    for i, item in enumerate(watchlist):
        ticker = item["ticker"]
        name = item["name"]
        market = item["market"]

        try:
            if market in ("KOSPI", "KOSDAQ"):
                from data.fetcher_kr import get_price_data, get_fundamental_data
            else:
                from data.fetcher_us import get_price_data, get_fundamental_data

            from analysis.scoring import score_stock
            from analysis.technical import add_all_indicators, get_technical_summary

            df = get_price_data(ticker)
            fund = get_fundamental_data(ticker)

            if df is not None and not df.empty:
                result = score_stock(ticker, name, df, style, fund)
                df_ind = add_all_indicators(df)
                tech = get_technical_summary(df_ind)

                results.append({
                    "ticker": ticker,
                    "name": name,
                    "market": market,
                    "score": result.composite_score,
                    "signal": result.signal,
                    "change_pct": tech.get("change_pct"),
                    "rsi": tech.get("rsi"),
                })
        except Exception as e:
            results.append({"ticker": ticker, "name": name, "market": market,
                           "score": 0, "signal": "오류", "change_pct": None, "rsi": None})

        progress.progress((i + 1) / len(watchlist))

    st.session_state["watch_results"] = results

# 결과 표시
results = st.session_state.get("watch_results", [])

for item in watchlist:
    ticker = item["ticker"]
    name = item["name"]
    market = item["market"]

    # 점수 찾기
    score_data = next((r for r in results if r["ticker"] == ticker), None)

    cols = st.columns([2.5, 1, 1, 1, 0.5])
    with cols[0]:
        st.markdown(f"**{name}** ({ticker}) `{market}`")
    with cols[1]:
        if score_data:
            st.markdown(signal_badge(score_data["signal"]), unsafe_allow_html=True)
        else:
            st.markdown("-")
    with cols[2]:
        if score_data:
            st.metric("점수", f"{score_data['score']:.0f}", label_visibility="collapsed")
        else:
            st.markdown("-")
    with cols[3]:
        if score_data and score_data.get("change_pct") is not None:
            st.metric("등락", format_percent(score_data["change_pct"]),
                       label_visibility="collapsed")
        else:
            st.markdown("-")
    with cols[4]:
        if st.button("🗑", key=f"del_{ticker}"):
            remove(ticker)
            st.rerun()

# 관심종목 추가
st.divider()
st.subheader("종목 추가")
add_col1, add_col2 = st.columns(2)

with add_col1:
    add_market = st.selectbox("시장", ["KOSPI", "KOSDAQ", "NYSE", "NASDAQ"], key="add_market")

with add_col2:
    add_ticker = st.text_input("종목 코드 (예: 005930, AAPL)", key="add_ticker")

if st.button("추가", key="add_btn") and add_ticker:
    from screener.watchlist import add
    add(add_ticker.strip(), add_ticker.strip(), add_market)
    st.success(f"{add_ticker} 추가됨")
    st.rerun()
