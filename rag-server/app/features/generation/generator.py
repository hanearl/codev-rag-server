import time
from typing import List
from .schema import GenerationRequest, GenerationResponse, CodeContext
from .prompt_manager import PromptManager
from app.core.clients import LLMClient
import logging

logger = logging.getLogger(__name__)

class CodeGenerator:
    def __init__(self, llm_client: LLMClient, prompt_manager: PromptManager):
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager

    async def generate_code(
        self, 
        request: GenerationRequest, 
        contexts: List[CodeContext]
    ) -> GenerationResponse:
        """코드 생성"""
        start_time = time.time()
        
        try:
            # 프롬프트 생성
            system_prompt = self.prompt_manager.get_system_prompt(
                request.language, request.include_tests
            )
            user_prompt = self.prompt_manager.get_user_prompt(
                request.query, contexts, request.language
            )
            
            # LLM 호출
            response = await self.llm_client.chat_completion({
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": request.max_tokens,
                "temperature": 0.1  # 일관성 있는 코드 생성을 위해 낮은 값
            })
            
            generated_code = response["choices"][0]["message"]["content"]
            tokens_used = response["usage"]["total_tokens"]
            model_used = response.get("model", "gpt-4o-mini")
            
            end_time = time.time()
            generation_time_ms = int((end_time - start_time) * 1000)
            
            return GenerationResponse(
                query=request.query,
                generated_code=generated_code,
                contexts_used=contexts,
                generation_time_ms=generation_time_ms,
                model_used=model_used,
                language=request.language,
                tokens_used=tokens_used,
                search_results_count=len(contexts)
            )
            
        except Exception as e:
            logger.error(f"코드 생성 실패: {e}")
            raise 