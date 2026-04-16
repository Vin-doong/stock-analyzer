"""OpenAI API 래퍼"""
import os
import time
from dotenv import load_dotenv

load_dotenv()


def get_client():
    """OpenAI 클라이언트 생성"""
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def analyze(prompt: str, model: str = None, max_tokens: int = 1024) -> str | None:
    """GPT에게 분석 요청 (재시도 로직 포함)"""
    from config import OPENAI_MODEL, OPENAI_MAX_RESPONSE

    client = get_client()
    if client is None:
        return None

    model = model or OPENAI_MODEL
    max_tokens = max_tokens or OPENAI_MAX_RESPONSE

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": "당신은 전문 주식 애널리스트입니다. 한국어로 간결하게 답변하세요."},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "503" in error_str:
                wait = (attempt + 1) * 5
                time.sleep(wait)
                continue
            print(f"OpenAI API 오류: {e}")
            return None

    return None
