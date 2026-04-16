"""Claude API 래퍼"""
import os
import time
from dotenv import load_dotenv

load_dotenv()


def get_client():
    """Anthropic 클라이언트 생성"""
    from anthropic import Anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return Anthropic(api_key=api_key)


def analyze(prompt: str, model: str = None, max_tokens: int = 1024) -> str | None:
    """Claude에게 분석 요청 (재시도 로직 포함)"""
    from config import CLAUDE_MODEL, CLAUDE_MAX_RESPONSE

    client = get_client()
    if client is None:
        return None

    model = model or CLAUDE_MODEL
    max_tokens = max_tokens or CLAUDE_MAX_RESPONSE

    for attempt in range(3):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "529" in error_str:
                wait = (attempt + 1) * 5
                time.sleep(wait)
                continue
            print(f"Claude API 오류: {e}")
            return None

    return None
