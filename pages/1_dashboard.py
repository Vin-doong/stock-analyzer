"""대시보드 - 시장 개요"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ui.styles import inject_css
from ui.formatters import format_percent, format_krw, format_usd
inject_css()

st.title("📈 시장 대시보드")

# 지수 데이터 로드
@st.cache_data(ttl=300)
def load_index_data():
    from data.fetcher_kr import get_index_data as kr_index
    from data.fetcher_us import get_index_data as us_index

    indices = {}
    for code, name in [("KS11", "KOSPI"), ("KQ11", "KOSDAQ")]:
        try:
            df = kr_index(code, days=30)
            if df is not None and not df.empty:
                last = df["Close"].iloc[-1]
                prev = df["Close"].iloc[-2] if len(df) >= 2 else last
                change = (last / prev - 1) * 100
                indices[name] = {"value": last, "change": change}
        except Exception:
            pass

    for code, name in [("^GSPC", "S&P 500"), ("^IXIC", "NASDAQ")]:
        try:
            df = us_index(code, days=30)
            if df is not None and not df.empty:
                last = df["Close"].iloc[-1]
                prev = df["Close"].iloc[-2] if len(df) >= 2 else last
                change = (last / prev - 1) * 100
                indices[name] = {"value": last, "change": change}
        except Exception:
            pass

    return indices

with st.spinner("시장 데이터 로딩 중..."):
    indices = load_index_data()

# 지수 카드
if indices:
    cols = st.columns(len(indices))
    for col, (name, data) in zip(cols, indices.items()):
        with col:
            delta = f"{data['change']:+.2f}%"
            st.metric(name, f"{data['value']:,.2f}", delta)
else:
    st.warning("시장 데이터를 불러올 수 없습니다.")

st.divider()

# AI 시장 요약
st.subheader("🤖 AI 시장 요약")

from ai.clipboard_helper import ai_analyze_or_clipboard, build_market_prompt

index_lines = []
for name, data in indices.items():
    index_lines.append(f"- {name}: {data['value']:,.2f} ({data['change']:+.2f}%)")
index_str = "\n".join(index_lines) if index_lines else "데이터 없음"

prompt = build_market_prompt(index_str, "일반적인 거래일")
ai_analyze_or_clipboard(prompt, cache_key="ai:market_overview")
