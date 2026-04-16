"""AI 분석 통합 모듈: API 키 있으면 자동 분석, 없으면 클립보드 복사 방식"""
import os
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()


def has_api_key() -> bool:
    """API 키가 설정되어 있는지 확인"""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    return bool(key and key.startswith("sk-ant-"))


def ai_analyze_or_clipboard(prompt: str, cache_key: str | None = None):
    """API 키 유무에 따라 자동 분석 또는 클립보드 방식 선택

    - API 키 있음: 버튼 클릭 → 앱 내 바로 결과 표시
    - API 키 없음: 클립보드 복사 + claude.ai 열기
    """
    if has_api_key():
        _api_mode(prompt, cache_key)
    else:
        _clipboard_mode(prompt)


def _api_mode(prompt: str, cache_key: str | None = None):
    """API 키로 직접 분석 (앱 내 결과 표시)"""
    from ai.claude_client import analyze
    from data import cache
    from config import CACHE_TTL

    # 캐시 확인
    if cache_key:
        cached = cache.get(cache_key)
        if cached is not None:
            st.markdown(cached)
            st.caption("📦 캐시된 결과 (30분)")
            return

    if st.button("🤖 AI 분석 실행", type="primary"):
        with st.spinner("Claude AI가 분석 중... (10~30초)"):
            result = analyze(prompt, max_tokens=1500)
            if result:
                if cache_key:
                    cache.set(cache_key, result, CACHE_TTL["ai_analysis"])
                st.markdown(result)
            else:
                st.error("API 호출 실패. API 키를 확인해주세요.")


def _clipboard_mode(prompt: str):
    """클립보드 복사 + claude.ai 열기"""
    copy_and_open_claude(prompt)


def copy_and_open_claude(prompt: str, button_label: str = "📋 프롬프트 복사 + Claude 열기"):
    """프롬프트를 클립보드에 복사하고 claude.ai를 새 탭으로 열기"""

    # 프롬프트 표시 (접기)
    with st.expander("📝 AI에게 보낼 프롬프트 미리보기", expanded=False):
        st.text_area("프롬프트", prompt, height=300, disabled=True, label_visibility="collapsed")

    # 클립보드 복사 + 새 탭 열기 (JavaScript 활용)
    # Streamlit에서 직접 클립보드 접근이 어려우므로 HTML/JS 컴포넌트 사용
    escaped = prompt.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace("</", "<\\/")

    copy_js = f"""
    <div style="display:flex; gap:8px; flex-wrap:wrap;">
        <button onclick="copyPrompt()" id="copyBtn"
            style="background: linear-gradient(135deg, #0984e3, #74b9ff);
                   color: white; border: none; padding: 10px 20px;
                   border-radius: 8px; cursor: pointer; font-size: 14px;
                   font-weight: bold; transition: all 0.3s;">
            📋 클립보드에 복사
        </button>
        <button onclick="openClaude()"
            style="background: linear-gradient(135deg, #6c5ce7, #a29bfe);
                   color: white; border: none; padding: 10px 20px;
                   border-radius: 8px; cursor: pointer; font-size: 14px;
                   font-weight: bold; transition: all 0.3s;">
            🚀 Claude.ai 열기
        </button>
    </div>
    <p id="status" style="margin-top:8px; font-size:13px; color:#555;"></p>
    <script>
    const promptText = `{escaped}`;

    function copyPrompt() {{
        navigator.clipboard.writeText(promptText).then(() => {{
            document.getElementById('copyBtn').innerText = '✅ 복사 완료!';
            document.getElementById('copyBtn').style.background = 'linear-gradient(135deg, #00b894, #55efc4)';
            document.getElementById('status').innerText = '클립보드에 복사되었습니다. Claude.ai에 붙여넣기(Ctrl+V) 하세요.';
            setTimeout(() => {{
                document.getElementById('copyBtn').innerText = '📋 클립보드에 복사';
                document.getElementById('copyBtn').style.background = 'linear-gradient(135deg, #0984e3, #74b9ff)';
            }}, 3000);
        }}).catch(() => {{
            document.getElementById('status').innerText = '복사 실패: 브라우저에서 클립보드 권한을 허용해주세요.';
        }});
    }}

    function openClaude() {{
        window.open('https://claude.ai/new', '_blank');
    }}
    </script>
    """
    components.html(copy_js, height=100)

    st.caption("💡 **사용법**: 복사 → Claude.ai 열기 → 붙여넣기(Ctrl+V) → Enter")


def build_stock_prompt(name, ticker, market, style, tech_summary, fund_summary, score, signal):
    """종목 분석용 프롬프트 생성"""
    from ai.prompts import STOCK_ANALYSIS_PROMPT

    tech_lines = []
    for k, v in tech_summary.items():
        if v is not None and k != "close":
            tech_lines.append(f"- {k}: {v}")
    tech_str = "\n".join(tech_lines) if tech_lines else "데이터 없음"

    fund_lines = []
    for k, v in fund_summary.items():
        if v is not None:
            fund_lines.append(f"- {k}: {v}")
    fund_str = "\n".join(fund_lines) if fund_lines else "데이터 없음"

    return STOCK_ANALYSIS_PROMPT.format(
        name=name, ticker=ticker, market=market, style=style,
        technical_summary=tech_str, fundamental_summary=fund_str,
        composite_score=score, signal=signal,
    )


def build_screener_prompt(stock_list, market, style):
    """스크리너 결과 분석용 프롬프트 생성"""
    from ai.prompts import SCREENER_SUMMARY_PROMPT

    lines = []
    for i, s in enumerate(stock_list[:15], 1):
        lines.append(f"{i}. {s['name']}({s['ticker']}) - 점수: {s['score']}, 신호: {s['signal']}")
    stock_str = "\n".join(lines)

    return SCREENER_SUMMARY_PROMPT.format(
        style=style, market=market, stock_list=stock_str,
    )


def build_market_prompt(index_data, highlights):
    """시장 개요 분석용 프롬프트 생성"""
    from ai.prompts import MARKET_OVERVIEW_PROMPT
    return MARKET_OVERVIEW_PROMPT.format(
        index_data=index_data, market_highlights=highlights,
    )


def build_recommendation_prompt(screening_results, market, style):
    """실시간 추천용 프롬프트 생성"""
    from ai.prompts import REALTIME_RECOMMENDATION_PROMPT

    lines = []
    for s in screening_results[:10]:
        lines.append(
            f"- {s['name']}({s['ticker']}): 점수 {s['score']}, "
            f"신호 {s['signal']}, RSI {s.get('rsi', 'N/A')}, "
            f"거래량비율 {s.get('volume_ratio', 'N/A')}"
        )
    results_str = "\n".join(lines)

    return REALTIME_RECOMMENDATION_PROMPT.format(
        style=style, market=market, screening_results=results_str,
    )
