"""LLM 프로바이더 설정 모듈.

.env 파일의 LLM_PROVIDER 값에 따라 Gemini 또는 LMStudio 모델을 반환합니다.
"""

import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "lmstudio")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "local-model")


def get_model_name() -> str:
    """현재 설정된 LLM 프로바이더에 따른 모델명을 반환합니다."""
    if LLM_PROVIDER == "lmstudio":
        return f"openai/{LMSTUDIO_MODEL}"
    return GEMINI_MODEL


def get_model_kwargs() -> dict:
    """LiteLLM/ADK에 전달할 추가 모델 파라미터를 반환합니다."""
    if LLM_PROVIDER == "lmstudio":
        return {
            "api_base": LMSTUDIO_BASE_URL,
            "api_key": "not-needed",
        }
    return {}
