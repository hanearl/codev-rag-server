from functools import lru_cache
from app.features.llm.client import OpenAIClient
from app.features.llm.service import LLMService
from app.core.config import settings


@lru_cache()
def get_openai_client() -> OpenAIClient:
    """OpenAI 클라이언트 인스턴스를 반환 (싱글톤)"""
    return OpenAIClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url
    )


def get_llm_service() -> LLMService:
    """LLM 서비스 인스턴스를 반환"""
    client = get_openai_client()
    return LLMService(client) 