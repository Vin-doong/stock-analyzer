"""커스텀 스타일"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

/* ===== 콤팩트 레이아웃 ===== */
/* 메인 컨테이너: 상단 여백 축소, 최대 너비 제한 */
.main .block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

/* 제목/부제목 여백 축소 */
h1 { font-size: 1.6rem !important; margin: 0.2rem 0 0.6rem 0 !important; }
h2 { font-size: 1.25rem !important; margin: 0.4rem 0 0.4rem 0 !important; }
h3 { font-size: 1.05rem !important; margin: 0.3rem 0 0.3rem 0 !important; }
h4 { font-size: 0.95rem !important; margin: 0.25rem 0 0.25rem 0 !important; }

/* 구분선 축소 */
hr { margin: 0.5rem 0 !important; }
[data-testid="stDivider"] { margin: 0.4rem 0 !important; }

/* 마크다운 단락 간격 */
.stMarkdown p { margin-bottom: 0.35rem; font-size: 0.92rem; }

/* 버튼 콤팩트 */
.stButton > button {
    padding: 0.3rem 0.8rem;
    font-size: 0.88rem;
    border-radius: 0.35rem;
}

/* 지수 metric 카드 크기 축소 */
div[data-testid="stMetric"] {
    background: #f8f9fa;
    padding: 0.45rem 0.6rem;
    border-radius: 0.4rem;
    border-left: 3px solid #0984e3;
}
div[data-testid="stMetric"] label {
    font-size: 0.8rem !important;
}
div[data-testid="stMetricValue"] {
    font-size: 1.15rem !important;
}
div[data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
}

/* 사이드바 컴팩트 */
section[data-testid="stSidebar"] .block-container {
    padding-top: 1rem;
}
section[data-testid="stSidebar"] h1 {
    font-size: 1.2rem !important;
}
section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
    padding: 0.25rem 0.5rem !important;
    font-size: 0.9rem !important;
}

/* 입력 요소 콤팩트 */
.stTextInput input, .stNumberInput input, .stSelectbox [data-baseweb="select"] {
    font-size: 0.88rem;
}

/* 탭 콤팩트 */
.stTabs [data-baseweb="tab"] {
    padding: 0.4rem 0.8rem;
    font-size: 0.9rem;
}

/* info/warning/success 박스 여백 축소 */
div[data-testid="stAlert"] {
    padding: 0.6rem 0.8rem;
    font-size: 0.88rem;
}

/* caption */
.stCaption, [data-testid="stCaptionContainer"] {
    font-size: 0.75rem;
}

/* ===== 점수 카드/배지 ===== */
.score-card {
    padding: 0.6rem;
    border-radius: 0.45rem;
    text-align: center;
    color: white;
    font-weight: 600;
    font-size: 1.05rem;
}
.score-strong-buy { background: linear-gradient(135deg, #00b894, #00cec9); }
.score-buy { background: linear-gradient(135deg, #0984e3, #74b9ff); }
.score-hold { background: linear-gradient(135deg, #fdcb6e, #ffeaa7); color: #2d3436; }
.score-sell { background: linear-gradient(135deg, #e17055, #fab1a0); }
.score-strong-sell { background: linear-gradient(135deg, #d63031, #ff7675); }

.metric-card {
    background: #f8f9fa;
    padding: 0.55rem 0.7rem;
    border-radius: 0.4rem;
    border-left: 3px solid #0984e3;
    margin-bottom: 0.35rem;
}

.signal-badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 0.9rem;
    font-weight: 500;
    font-size: 0.78rem;
}
.signal-strong-buy { background: #00b894; color: white; }
.signal-buy { background: #0984e3; color: white; }
.signal-hold { background: #fdcb6e; color: #2d3436; }
.signal-sell { background: #e17055; color: white; }
.signal-strong-sell { background: #d63031; color: white; }

/* 홈 카드 */
.home-card {
    background: #f8f9fa;
    padding: 0.9rem 1rem;
    border-radius: 0.5rem;
    border-left: 3px solid #0984e3;
    height: 100%;
}
.home-card h4 {
    margin: 0 0 0.35rem 0 !important;
    font-size: 0.98rem !important;
    color: #2d3436;
}
.home-card p {
    margin: 0;
    font-size: 0.82rem;
    color: #636e72;
    line-height: 1.35;
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
