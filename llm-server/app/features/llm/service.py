from .client import OpenAIClient
from .schema import (
    ChatCompletionRequest, ChatCompletionResponse,
    CompletionRequest, CompletionResponse
)


class LLMService:
    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client
    
    async def create_chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """채팅 완성 생성"""
        try:
            return await self.openai_client.create_chat_completion(request)
        except Exception as e:
            raise Exception(f"LLM 서비스 오류: {str(e)}")
    
    async def create_completion(self, request: CompletionRequest) -> CompletionResponse:
        """텍스트 완성 생성"""
        try:
            return await self.openai_client.create_completion(request)
        except Exception as e:
            raise Exception(f"LLM 서비스 오류: {str(e)}")
    
    async def get_models(self) -> dict:
        """사용 가능한 모델 목록 반환"""
        return {
            "object": "list",
            "data": [
                {
                    "id": "gpt-4o-mini",
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "openai"
                }
            ]
        } 