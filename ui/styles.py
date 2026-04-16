"""커스텀 스타일"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

.score-card {
    padding: 1rem;
    border-radius: 0.5rem;
    text-align: center;
    color: white;
    font-weight: bold;
    font-size: 1.2rem;
}
.score-strong-buy { background: linear-gradient(135deg, #00b894, #00cec9); }
.score-buy { background: linear-gradient(135deg, #0984e3, #74b9ff); }
.score-hold { background: linear-gradient(135deg, #fdcb6e, #ffeaa7); color: #2d3436; }
.score-sell { background: linear-gradient(135deg, #e17055, #fab1a0); }
.score-strong-sell { background: linear-gradient(135deg, #d63031, #ff7675); }

.metric-card {
    background: #f8f9fa;
    padding: 0.8rem;
    border-radius: 0.5rem;
    border-left: 4px solid #0984e3;
    margin-bottom: 0.5rem;
}

.signal-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-weight: 500;
    font-size: 0.85rem;
}
.signal-strong-buy { background: #00b894; color: white; }
.signal-buy { background: #0984e3; color: white; }
.signal-hold { background: #fdcb6e; color: #2d3436; }
.signal-sell { background: #e17055; color: white; }
.signal-strong-sell { background: #d63031; color: white; }

div[data-testid="stMetric"] {
    background: #f8f9fa;
    padding: 0.5rem;
    border-radius: 0.5rem;
}
</style>
"""


def inject_css():
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def signal_badge(signal: str) -> str:
    css_class = {
        "강력매수": "signal-strong-buy",
        "매수": "signal-buy",
        "관망": "signal-hold",
        "매도": "signal-sell",
        "강력매도": "signal-strong-sell",
    }.get(signal, "signal-hold")
    return f'<span class="signal-badge {css_class}">{signal}</span>'


def score_card(score: float, signal: str) -> str:
    css_class = {
        "강력매수": "score-strong-buy",
        "매수": "score-buy",
        "관망": "score-hold",
        "매도": "score-sell",
        "강력매도": "score-strong-sell",
    }.get(signal, "score-hold")
    return f'<div class="score-card {css_class}">{score:.1f}점 | {signal}</div>'
