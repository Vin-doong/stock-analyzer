"""Plotly 차트 빌더"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


def candlestick_chart(df: pd.DataFrame, show_ma: bool = True, show_bb: bool = True,
                       show_volume: bool = True) -> go.Figure:
    """캔들스틱 차트 + 지표 오버레이"""
    rows = 1 + (1 if show_volume else 0)
    heights = [0.7, 0.3] if show_volume else [1.0]

    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=heights,
    )

    # 캔들스틱
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="가격",
        increasing_line_color="#00b894", decreasing_line_color="#d63031",
    ), row=1, col=1)

    # 이동평균선
    if show_ma:
        colors = {"MA5": "#fdcb6e", "MA20": "#e17055", "MA60": "#0984e3", "MA120": "#6c5ce7"}
        for ma, color in colors.items():
            if ma in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index, y=df[ma], name=ma,
                    line=dict(color=color, width=1),
                ), row=1, col=1)

    # 볼린저밴드
    if show_bb and "BB_Upper" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Upper"], name="BB 상단",
            line=dict(color="rgba(150,150,150,0.3)", width=1),
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_Lower"], name="BB 하단",
            line=dict(color="rgba(150,150,150,0.3)", width=1),
            fill="tonexty", fillcolor="rgba(150,150,150,0.1)",
        ), row=1, col=1)

    # 거래량
    if show_volume and "Volume" in df.columns:
        colors_vol = ["#00b894" if df["Close"].iloc[i] >= df["Open"].iloc[i]
                      else "#d63031" for i in range(len(df))]
        fig.add_trace(go.Bar(
            x=df.index, y=df["Volume"], name="거래량",
            marker_color=colors_vol, opacity=0.7,
        ), row=2, col=1)

    fig.update_layout(
        height=500, xaxis_rangeslider_visible=False,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0),
    )
    fig.update_xaxes(type="category", nticks=20)

    return fig


def indicator_chart(df: pd.DataFrame, indicator: str = "RSI") -> go.Figure:
    """개별 지표 차트"""
    fig = go.Figure()

    if indicator == "RSI" and "RSI" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
                                  line=dict(color="#0984e3", width=2)))
        fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="과매수 (70)")
        fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="과매도 (30)")
        fig.update_yaxes(range=[0, 100])

    elif indicator == "MACD" and "MACD" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD",
                                  line=dict(color="#0984e3", width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=df["MACD_Signal"], name="Signal",
                                  line=dict(color="#e17055", width=2)))
        if "MACD_Hist" in df.columns:
            colors = ["#00b894" if v >= 0 else "#d63031" for v in df["MACD_Hist"]]
            fig.add_trace(go.Bar(x=df.index, y=df["MACD_Hist"], name="Histogram",
                                  marker_color=colors, opacity=0.5))

    elif indicator == "Stochastic" and "Stoch_K" in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df["Stoch_K"], name="%K",
                                  line=dict(color="#0984e3", width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=df["Stoch_D"], name="%D",
                                  line=dict(color="#e17055", width=2)))
        fig.add_hline(y=80, line_dash="dash", line_color="red")
        fig.add_hline(y=20, line_dash="dash", line_color="green")

    fig.update_layout(
        height=250, template="plotly_white",
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_xaxes(type="category", nticks=20)

    return fig


def score_gauge(score: float, title: str = "종합 점수") -> go.Figure:
    """원형 게이지 차트"""
    color = "#00b894" if score >= 65 else "#fdcb6e" if score >= 40 else "#d63031"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": title, "font": {"size": 16}},
        number={"suffix": "점", "font": {"size": 28}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 20], "color": "#ff7675"},
                {"range": [20, 40], "color": "#fab1a0"},
                {"range": [40, 65], "color": "#ffeaa7"},
                {"range": [65, 80], "color": "#81ecec"},
                {"range": [80, 100], "color": "#55efc4"},
            ],
        },
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def score_breakdown_bar(category_scores: dict) -> go.Figure:
    """카테고리별 점수 막대 차트"""
    labels = {
        "rsi": "RSI", "macd": "MACD", "bollinger": "볼린저",
        "volume": "거래량", "ma_trend": "이평선", "momentum": "모멘텀",
        "per_pbr": "PER/PBR", "roe_growth": "ROE/성장", "revenue": "매출",
    }

    names = [labels.get(k, k) for k in category_scores.keys()]
    values = list(category_scores.values())
    colors = ["#00b894" if v >= 65 else "#fdcb6e" if v >= 40 else "#d63031" for v in values]

    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker_color=colors, text=[f"{v:.0f}" for v in values],
        textposition="auto",
    ))
    fig.update_layout(
        height=300, xaxis=dict(range=[0, 100], title="점수"),
        template="plotly_white",
        margin=dict(l=0, r=0, t=10, b=0),
    )
    return fig


def equity_curve_chart(equity_df: pd.DataFrame) -> go.Figure:
    """백테스팅 수익 곡선"""
    if equity_df.empty:
        return go.Figure()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity_df.index, y=equity_df["value"],
        name="평가액", fill="tozeroy",
        line=dict(color="#0984e3", width=2),
        fillcolor="rgba(9, 132, 227, 0.1)",
    ))

    fig.update_layout(
        height=350, template="plotly_white",
        yaxis_title="평가액",
        margin=dict(l=0, r=0, t=30, b=0),
    )
    return fig
