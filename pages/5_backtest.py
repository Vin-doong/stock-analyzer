"""백테스팅 페이지"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ui.styles import inject_css
from ui.components import market_selector, period_selector
from ui.charts import equity_curve_chart
from ui.formatters import format_krw, format_percent
inject_css()

st.title("📊 백테스팅")
st.markdown("전략의 과거 수익률을 검증합니다.")

# 사이드바 설정
with st.sidebar:
    market = market_selector("bt_market")
    days = period_selector("bt_period")

    from analysis.backtest import STRATEGIES
    strategy_name = st.selectbox("전략 선택", list(STRATEGIES.keys()), key="bt_strategy")

    initial_cap = st.number_input("초기 자본금", value=10_000_000, step=1_000_000,
                                   format="%d", key="bt_capital")

    if market in ("NYSE", "NASDAQ"):
        commission = st.number_input("수수료 (%)", value=0.01, step=0.01, key="bt_comm")
        tax = st.number_input("세금 (%)", value=0.0, step=0.1, key="bt_tax")
    else:
        commission = st.number_input("수수료 (%)", value=0.015, step=0.005, key="bt_comm")
        tax = st.number_input("매도세 (%)", value=0.23, step=0.01, key="bt_tax")

# 종목 선택
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

options = stock_df.to_dict("records")
display = [f"{r.get('name', r['ticker'])} ({r['ticker']})" for r in options]
selected_idx = st.selectbox("종목 검색", range(len(display)),
                             format_func=lambda i: display[i], key="bt_stock")
ticker = options[selected_idx]["ticker"]
name = options[selected_idx].get("name", ticker)

# 백테스팅 실행
if st.button("▶️ 백테스팅 실행", type="primary", use_container_width=True):
    with st.spinner(f"{name} ({ticker}) 백테스팅 중..."):
        if market in ("KOSPI", "KOSDAQ"):
            from data.fetcher_kr import get_price_data
        else:
            from data.fetcher_us import get_price_data

        from analysis.backtest import backtest_strategy, STRATEGIES

        df = get_price_data(ticker, days)
        if df is None or df.empty:
            st.error("가격 데이터를 불러올 수 없습니다.")
            st.stop()

        strategy_fn = STRATEGIES[strategy_name]
        result = backtest_strategy(df, strategy_fn, initial_cap, commission, tax)

        if "error" in result:
            st.error(result["error"])
            st.stop()

        # 결과 표시
        st.subheader(f"📋 결과: {name} ({ticker}) - {strategy_name}")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 수익률", format_percent(result["total_return"]))
        with col2:
            st.metric("최종 평가액", format_krw(result["final_value"]) if market in ("KOSPI", "KOSDAQ")
                       else f"${result['final_value']:,.0f}")
        with col3:
            st.metric("최대 낙폭", format_percent(result["max_drawdown"]))
        with col4:
            st.metric("승률", f"{result['win_rate']}%")

        col5, col6, col7 = st.columns(3)
        with col5:
            st.metric("거래 횟수", f"{result['trade_count']}회")
        with col6:
            st.metric("평균 수익", format_krw(result["avg_profit"]) if market in ("KOSPI", "KOSDAQ")
                       else f"${result['avg_profit']:,.0f}")
        with col7:
            st.metric("평균 손실", format_krw(result["avg_loss"]) if market in ("KOSPI", "KOSDAQ")
                       else f"${result['avg_loss']:,.0f}")

        # 수익 곡선
        st.divider()
        st.subheader("📈 수익 곡선")
        equity_df = result.get("equity_curve")
        if equity_df is not None and not equity_df.empty:
            st.plotly_chart(equity_curve_chart(equity_df), use_container_width=True)

        # 거래 내역
        trades = result.get("trades", [])
        if trades:
            st.divider()
            with st.expander(f"📝 거래 내역 ({len(trades)}건)"):
                for t in trades[-20:]:  # 최근 20건
                    icon = "🟢" if t["type"] == "buy" else "🔴"
                    pnl = t.get("pnl")
                    pnl_str = f" (PnL: {pnl:+,.0f})" if pnl is not None else ""
                    price_fmt = f"{t['price']:,.0f}" if market in ("KOSPI", "KOSDAQ") else f"${t['price']:,.2f}"
                    st.text(f"{icon} {t['date']} | {t['type'].upper()} | "
                           f"가격: {price_fmt} | 수량: {t['shares']}{pnl_str}")
