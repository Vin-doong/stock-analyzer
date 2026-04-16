"""재사용 가능한 Streamlit 위젯"""
import streamlit as st
from config import TradingStyle, Market


def market_selector(key: str = "market") -> str:
    """시장 선택"""
    options = {
        "KOSPI": "KOSPI (한국 대형주)",
        "KOSDAQ": "KOSDAQ (한국 중소형주)",
        "NYSE": "NYSE (미국 대형주)",
        "NASDAQ": "NASDAQ (미국 기술주)",
    }
    selected = st.selectbox(
        "시장 선택", list(options.keys()),
        format_func=lambda x: options[x],
        key=key,
    )
    return selected


def style_selector(key: str = "style") -> TradingStyle:
    """투자 스타일 선택"""
    style_map = {
        "단타": TradingStyle.DAY,
        "스윙": TradingStyle.SWING,
        "중장기": TradingStyle.LONG,
    }
    selected = st.radio(
        "투자 스타일", list(style_map.keys()),
        horizontal=True, key=key,
    )
    return style_map[selected]


def stock_selector(stock_df, key: str = "stock") -> dict | None:
    """종목 선택"""
    if stock_df is None or stock_df.empty:
        st.warning("종목 리스트를 불러올 수 없습니다.")
        return None

    options = stock_df.to_dict("records")
    display = [f"{r.get('name', r['ticker'])} ({r['ticker']})" for r in options]

    selected_idx = st.selectbox(
        "종목 검색", range(len(display)),
        format_func=lambda i: display[i],
        key=key,
    )
    return options[selected_idx] if selected_idx is not None else None


def period_selector(key: str = "period") -> int:
    """조회 기간 선택"""
    periods = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "2년": 730}
    selected = st.select_slider(
        "조회 기간", list(periods.keys()),
        value="1년", key=key,
    )
    return periods[selected]
