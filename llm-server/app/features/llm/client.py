import openai
import time
import uuid
from typing import Optional
from .schema import (
    ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChoice,
    ChatCompletionUsage, ChatMessage, Role,
    CompletionRequest, CompletionResponse, CompletionChoice
)


class OpenAIClient:
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    async def create_chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """채팅 완성 생성"""
        try:
            # OpenAI API 호출을 위한 메시지 변환
            messages = [
                {"role": msg.role.value, "content": msg.content}
                for msg in request.messages
            ]
            
            response = await self._client.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty,
                stream=request.stream,
                stop=request.stop
            )
            
            # vLLM 호환 응답 형식으로 변환
            choices = []
            for choice in response.choices:
                choices.append(ChatCompletionChoice(
                    index=choice.index,
                    message=ChatMessage(
                        role=Role(choice.message.role),
                        content=choice.message.content or ""
                    ),
                    finish_reason=choice.finish_reason
                ))
            
            usage = None
            if response.usage:
                usage = ChatCompletionUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )
            
            return ChatCompletionResponse(
                id=response.id,
                object=response.object,
                created=response.created,
                model=response.model,
                choices=choices,
                usage=usage
            )
            
        except Exception as e:
            raise Exception(f"OpenAI API 호출 실패: {str(e)}")
    
    async def create_completion(self, request: CompletionRequest) -> CompletionResponse:
        """텍스트 완성 생성 (레거시 API)"""
        try:
            # OpenAI의 새로운 API에서는 chat completions을 사용하여 구현
            messages = [{"role": "user", "content": request.prompt}]
            
            response = await self._client.chat.completions.create(
                model=request.model,
                messages=messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                n=request.n,
                stream=request.stream,
                stop=request.stop
            )
            
            # 텍스트 완성 형식으로 변환
            choices = []
            for choice in response.choices:
                choices.append(CompletionChoice(
                    text=choice.message.content or "",
                    index=choice.index,
                    finish_reason=choice.finish_reason
                ))
            
            usage = None
            if response.usage:
                usage = ChatCompletionUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )
            
            return CompletionResponse(
                id=response.id,
                object="text_completion",
                created=response.created,
                model=response.model,
                choices=choices,
                usage=usage
            )
            
        except Exception as e:
            raise Exception(f"OpenAI API 호출 실패: {str(e)}") 