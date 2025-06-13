# Task 14: LangChain LLMChain 구현

## 📋 작업 개요
LangChain LLMChain을 활용하여 PromptTemplate과 LLM을 연결하고, 검색된 코드 컨텍스트를 기반으로 한 고품질 응답 생성 시스템을 구현합니다.

## 🎯 작업 목표
- LangChain LLMChain 기반 응답 생성 시스템 구축
- 다양한 LLM 제공자 지원 (OpenAI, Anthropic 등)
- 스트리밍 응답 및 비동기 처리 지원
- 응답 품질 모니터링 및 캐싱 기능

## 🔗 의존성
- **선행 Task**: Task 13 (LangChain PromptTemplate 구현)
- **활용할 기존 코드**: `app/features/generation/service.py`

## 🔧 구현 사항

### 1. LLMChain 핵심 구현

```python
# app/llm/langchain_llm.py
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from langchain.llms.base import BaseLLM
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.chains import LLMChain
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler
from pydantic import BaseModel, Field
from enum import Enum
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

class LLMProvider(str, Enum):
    """LLM 제공자"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"

class LLMConfig(BaseModel):
    """LLM 설정"""
    provider: LLMProvider = LLMProvider.OPENAI
    model_name: str = "gpt-4"
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, gt=0)
    streaming: bool = True
    timeout: int = Field(default=30, gt=0)
    max_retries: int = Field(default=3, ge=0)
    
    # OpenAI 특화 설정
    openai_api_key: Optional[str] = None
    openai_organization: Optional[str] = None
    
    # Anthropic 특화 설정
    anthropic_api_key: Optional[str] = None
    
    # 로컬 LLM 설정
    local_model_path: Optional[str] = None
    local_api_url: Optional[str] = None

class ResponseMetadata(BaseModel):
    """응답 메타데이터"""
    provider: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    response_time_ms: int
    finish_reason: Optional[str] = None
    cached: bool = False

class LLMResponse(BaseModel):
    """LLM 응답 모델"""
    content: str
    metadata: ResponseMetadata
    error: Optional[str] = None
    is_complete: bool = True

class CustomCallbackHandler(BaseCallbackHandler):
    """커스텀 콜백 핸들러"""
    
    def __init__(self):
        self.tokens_used = 0
        self.start_time = None
        self.response_parts = []
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        self.start_time = time.time()
        logger.info(f"LLM 호출 시작: {serialized.get('name', 'unknown')}")
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.response_parts.append(token)
        self.tokens_used += 1
    
    def on_llm_end(self, response, **kwargs) -> None:
        end_time = time.time()
        response_time = int((end_time - self.start_time) * 1000) if self.start_time else 0
        logger.info(f"LLM 호출 완료: {response_time}ms, 토큰: {self.tokens_used}")
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        logger.error(f"LLM 호출 오류: {error}")

class CodeLLMChain:
    """코드 특화 LLM 체인"""
    
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self.llm = self._create_llm()
        self.callback_handler = CustomCallbackHandler()
        self._response_cache = {}
    
    def _create_llm(self) -> BaseLLM:
        """LLM 인스턴스 생성"""
        callback_manager = CallbackManager([self.callback_handler])
        
        if self.config.provider == LLMProvider.OPENAI:
            return ChatOpenAI(
                model_name=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                streaming=self.config.streaming,
                callback_manager=callback_manager,
                openai_api_key=self.config.openai_api_key,
                openai_organization=self.config.openai_organization,
                request_timeout=self.config.timeout,
                max_retries=self.config.max_retries
            )
        
        elif self.config.provider == LLMProvider.ANTHROPIC:
            return ChatAnthropic(
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                streaming=self.config.streaming,
                callback_manager=callback_manager,
                anthropic_api_key=self.config.anthropic_api_key,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries
            )
        
        else:
            raise ValueError(f"지원하지 않는 LLM 제공자: {self.config.provider}")
    
    async def generate_response(
        self,
        prompt: str,
        use_cache: bool = True,
        **kwargs
    ) -> LLMResponse:
        """응답 생성"""
        # 캐시 확인
        cache_key = self._generate_cache_key(prompt, kwargs)
        if use_cache and cache_key in self._response_cache:
            cached_response = self._response_cache[cache_key]
            cached_response.metadata.cached = True
            logger.info(f"캐시된 응답 반환: {cache_key[:16]}...")
            return cached_response
        
        start_time = time.time()
        
        try:
            # LLM 체인 생성
            chain = LLMChain(llm=self.llm, prompt=None, verbose=True)
            
            # 응답 생성
            self.callback_handler = CustomCallbackHandler()  # 리셋
            
            if self.config.streaming:
                response_content = await self._generate_streaming_response(prompt)
            else:
                response_content = await self._generate_simple_response(prompt)
            
            end_time = time.time()
            response_time = int((end_time - start_time) * 1000)
            
            # 메타데이터 생성
            metadata = ResponseMetadata(
                provider=self.config.provider.value,
                model_name=self.config.model_name,
                prompt_tokens=self._estimate_tokens(prompt),
                completion_tokens=self._estimate_tokens(response_content),
                total_tokens=self._estimate_tokens(prompt + response_content),
                response_time_ms=response_time,
                cached=False
            )
            
            response = LLMResponse(
                content=response_content,
                metadata=metadata
            )
            
            # 캐시 저장
            if use_cache:
                self._response_cache[cache_key] = response
            
            return response
            
        except Exception as e:
            logger.error(f"LLM 응답 생성 실패: {e}")
            return LLMResponse(
                content="",
                metadata=ResponseMetadata(
                    provider=self.config.provider.value,
                    model_name=self.config.model_name,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    response_time_ms=0
                ),
                error=str(e),
                is_complete=False
            )
    
    async def _generate_simple_response(self, prompt: str) -> str:
        """단순 응답 생성"""
        messages = [HumanMessage(content=prompt)]
        response = await self.llm.agenerate([messages])
        return response.generations[0][0].text
    
    async def _generate_streaming_response(self, prompt: str) -> str:
        """스트리밍 응답 생성"""
        messages = [HumanMessage(content=prompt)]
        response_parts = []
        
        async for chunk in self.llm.astream(messages):
            if hasattr(chunk, 'content'):
                response_parts.append(chunk.content)
            elif isinstance(chunk, str):
                response_parts.append(chunk)
        
        return "".join(response_parts)
    
    async def generate_streaming_response(
        self,
        prompt: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """스트리밍 응답 제너레이터"""
        try:
            messages = [HumanMessage(content=prompt)]
            
            async for chunk in self.llm.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
                elif isinstance(chunk, str) and chunk:
                    yield chunk
                    
        except Exception as e:
            logger.error(f"스트리밍 응답 생성 실패: {e}")
            yield f"오류가 발생했습니다: {str(e)}"
    
    def _generate_cache_key(self, prompt: str, kwargs: Dict[str, Any]) -> str:
        """캐시 키 생성"""
        import hashlib
        
        cache_data = {
            "prompt": prompt,
            "model": self.config.model_name,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            **kwargs
        }
        
        cache_string = str(sorted(cache_data.items()))
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _estimate_tokens(self, text: str) -> int:
        """토큰 수 추정 (대략적)"""
        # 실제로는 tiktoken 등을 사용해야 하지만, 여기서는 간단한 추정
        return int(len(text.split()) * 1.3)
    
    def clear_cache(self):
        """캐시 클리어"""
        self._response_cache.clear()
        logger.info("LLM 응답 캐시 클리어됨")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        return {
            "cache_size": len(self._response_cache),
            "cache_keys": list(self._response_cache.keys())[:10]  # 최대 10개만
        }
```

### 2. 통합 LLM 서비스

```python
# app/llm/llm_service.py
from typing import List, Dict, Any, Optional, AsyncGenerator
from .langchain_llm import CodeLLMChain, LLMConfig, LLMResponse, LLMProvider
from .prompt_service import PromptService, PromptType
import logging
import asyncio

logger = logging.getLogger(__name__)

class LLMService:
    """통합 LLM 서비스"""
    
    def __init__(self, llm_config: LLMConfig = None, prompt_service: PromptService = None):
        self.llm_config = llm_config or LLMConfig()
        self.prompt_service = prompt_service or PromptService()
        self.llm_chain = CodeLLMChain(self.llm_config)
        self._request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0
        }
    
    async def explain_code(
        self,
        code_content: str,
        language: str,
        question: str = "이 코드가 무엇을 하는지 설명해주세요",
        context_data: Dict[str, Any] = None,
        use_cache: bool = True
    ) -> LLMResponse:
        """코드 설명 생성"""
        try:
            # 프롬프트 생성
            prompt = await self.prompt_service.create_code_explanation_prompt(
                code_content, language, question, context_data
            )
            
            # LLM 응답 생성
            response = await self.llm_chain.generate_response(prompt, use_cache)
            
            # 통계 업데이트
            self._update_stats(response)
            
            logger.info(f"코드 설명 생성 완료: {response.metadata.response_time_ms}ms")
            return response
            
        except Exception as e:
            logger.error(f"코드 설명 생성 실패: {e}")
            self._request_stats["failed_requests"] += 1
            raise
    
    async def generate_code(
        self,
        requirements: str,
        language: str,
        related_code: List[str] = None,
        context_data: Dict[str, Any] = None,
        use_cache: bool = True
    ) -> LLMResponse:
        """코드 생성"""
        try:
            # 프롬프트 생성
            prompt = await self.prompt_service.create_code_generation_prompt(
                requirements, language, related_code, context_data
            )
            
            # LLM 응답 생성
            response = await self.llm_chain.generate_response(prompt, use_cache)
            
            # 통계 업데이트
            self._update_stats(response)
            
            logger.info(f"코드 생성 완료: {response.metadata.response_time_ms}ms")
            return response
            
        except Exception as e:
            logger.error(f"코드 생성 실패: {e}")
            self._request_stats["failed_requests"] += 1
            raise
    
    async def review_code(
        self,
        code_content: str,
        language: str,
        context_data: Dict[str, Any] = None,
        use_cache: bool = True
    ) -> LLMResponse:
        """코드 리뷰"""
        try:
            # 프롬프트 생성
            prompt = await self.prompt_service.create_code_review_prompt(
                code_content, language, context_data
            )
            
            # LLM 응답 생성
            response = await self.llm_chain.generate_response(prompt, use_cache)
            
            # 통계 업데이트
            self._update_stats(response)
            
            logger.info(f"코드 리뷰 완료: {response.metadata.response_time_ms}ms")
            return response
            
        except Exception as e:
            logger.error(f"코드 리뷰 실패: {e}")
            self._request_stats["failed_requests"] += 1
            raise
    
    async def help_debug(
        self,
        code_content: str,
        language: str,
        problem_description: str,
        error_info: str = None,
        context_data: Dict[str, Any] = None,
        use_cache: bool = True
    ) -> LLMResponse:
        """디버깅 도움"""
        try:
            # 프롬프트 생성
            prompt = await self.prompt_service.create_debugging_help_prompt(
                code_content, language, problem_description, error_info, context_data
            )
            
            # LLM 응답 생성
            response = await self.llm_chain.generate_response(prompt, use_cache)
            
            # 통계 업데이트
            self._update_stats(response)
            
            logger.info(f"디버깅 도움 완료: {response.metadata.response_time_ms}ms")
            return response
            
        except Exception as e:
            logger.error(f"디버깅 도움 실패: {e}")
            self._request_stats["failed_requests"] += 1
            raise
    
    async def answer_question(
        self,
        question: str,
        code_contexts: List[Dict[str, Any]],
        language: str = "java",
        use_cache: bool = True
    ) -> LLMResponse:
        """질문 답변"""
        try:
            # 프롬프트 생성
            prompt = await self.prompt_service.create_general_qa_prompt(
                question, code_contexts, language
            )
            
            # LLM 응답 생성
            response = await self.llm_chain.generate_response(prompt, use_cache)
            
            # 통계 업데이트
            self._update_stats(response)
            
            logger.info(f"질문 답변 완료: {response.metadata.response_time_ms}ms")
            return response
            
        except Exception as e:
            logger.error(f"질문 답변 실패: {e}")
            self._request_stats["failed_requests"] += 1
            raise
    
    async def generate_streaming_response(
        self,
        prompt_type: PromptType,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """스트리밍 응답 생성"""
        try:
            # 프롬프트 타입에 따른 프롬프트 생성
            if prompt_type == PromptType.CODE_EXPLANATION:
                prompt = await self.prompt_service.create_code_explanation_prompt(
                    kwargs.get('code_content', ''),
                    kwargs.get('language', 'java'),
                    kwargs.get('question', '코드를 설명해주세요'),
                    kwargs.get('context_data')
                )
            elif prompt_type == PromptType.CODE_GENERATION:
                prompt = await self.prompt_service.create_code_generation_prompt(
                    kwargs.get('requirements', ''),
                    kwargs.get('language', 'java'),
                    kwargs.get('related_code'),
                    kwargs.get('context_data')
                )
            elif prompt_type == PromptType.GENERAL_QA:
                prompt = await self.prompt_service.create_general_qa_prompt(
                    kwargs.get('question', ''),
                    kwargs.get('code_contexts', []),
                    kwargs.get('language', 'java')
                )
            else:
                yield "지원하지 않는 프롬프트 타입입니다."
                return
            
            # 스트리밍 응답 생성
            async for chunk in self.llm_chain.generate_streaming_response(prompt):
                yield chunk
            
            # 통계 업데이트 (비동기로)
            asyncio.create_task(self._update_streaming_stats())
            
        except Exception as e:
            logger.error(f"스트리밍 응답 생성 실패: {e}")
            yield f"오류가 발생했습니다: {str(e)}"
    
    async def batch_process(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 3
    ) -> List[LLMResponse]:
        """배치 처리"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_request(request_data: Dict[str, Any]) -> LLMResponse:
            async with semaphore:
                request_type = request_data.get('type')
                
                if request_type == 'explain':
                    return await self.explain_code(**request_data.get('params', {}))
                elif request_type == 'generate':
                    return await self.generate_code(**request_data.get('params', {}))
                elif request_type == 'review':
                    return await self.review_code(**request_data.get('params', {}))
                elif request_type == 'debug':
                    return await self.help_debug(**request_data.get('params', {}))
                elif request_type == 'qa':
                    return await self.answer_question(**request_data.get('params', {}))
                else:
                    raise ValueError(f"지원하지 않는 요청 타입: {request_type}")
        
        # 모든 요청 병렬 처리
        tasks = [process_single_request(req) for req in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외를 LLMResponse로 변환
        processed_responses = []
        for response in responses:
            if isinstance(response, Exception):
                processed_responses.append(LLMResponse(
                    content="",
                    metadata=ResponseMetadata(
                        provider=self.llm_config.provider.value,
                        model_name=self.llm_config.model_name,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        response_time_ms=0
                    ),
                    error=str(response),
                    is_complete=False
                ))
            else:
                processed_responses.append(response)
        
        return processed_responses
    
    def _update_stats(self, response: LLMResponse):
        """통계 업데이트"""
        self._request_stats["total_requests"] += 1
        if response.error is None:
            self._request_stats["successful_requests"] += 1
        else:
            self._request_stats["failed_requests"] += 1
        
        self._request_stats["total_tokens"] += response.metadata.total_tokens
    
    async def _update_streaming_stats(self):
        """스트리밍 통계 업데이트"""
        self._request_stats["total_requests"] += 1
        self._request_stats["successful_requests"] += 1
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """서비스 통계"""
        cache_stats = self.llm_chain.get_cache_stats()
        
        return {
            "request_stats": self._request_stats,
            "cache_stats": cache_stats,
            "llm_config": {
                "provider": self.llm_config.provider.value,
                "model_name": self.llm_config.model_name,
                "temperature": self.llm_config.temperature,
                "max_tokens": self.llm_config.max_tokens,
                "streaming": self.llm_config.streaming
            }
        }
    
    async def update_llm_config(self, new_config: Dict[str, Any]):
        """LLM 설정 업데이트"""
        # 기존 설정 업데이트
        current_config = self.llm_config.dict()
        current_config.update(new_config)
        
        # 새 설정으로 LLM 재생성
        self.llm_config = LLMConfig(**current_config)
        self.llm_chain = CodeLLMChain(self.llm_config)
        
        logger.info(f"LLM 설정 업데이트: {new_config}")
    
    async def health_check(self) -> Dict[str, Any]:
        """헬스 체크"""
        try:
            # 간단한 테스트 응답 생성
            test_response = await self.llm_chain.generate_response(
                "안녕하세요. 간단한 테스트입니다.",
                use_cache=False
            )
            
            return {
                "status": "healthy",
                "provider": self.llm_config.provider.value,
                "model": self.llm_config.model_name,
                "test_response_time_ms": test_response.metadata.response_time_ms,
                "test_successful": test_response.error is None
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
```

## ✅ 완료 조건

1. **LLMChain 구현**: LangChain 기반 LLM 체인 완전 구현
2. **다중 제공자 지원**: OpenAI, Anthropic 등 다양한 LLM 지원
3. **스트리밍 응답**: 실시간 스트리밍 응답 지원
4. **응답 캐싱**: 효율적인 응답 캐싱 시스템
5. **배치 처리**: 다중 요청 병렬 처리 지원
6. **모니터링**: 상세한 통계 및 성능 모니터링
7. **에러 처리**: 모든 예외 상황 적절히 처리

## 📋 다음 Task와의 연관관계

- **Task 15**: HybridRAG 서비스에서 이 LLM 서비스를 핵심 구성요소로 활용

## 🧪 테스트 계획

```python
# tests/unit/llm/test_langchain_llm.py
async def test_llm_chain_initialization():
    """LLM 체인 초기화 테스트"""
    config = LLMConfig(provider=LLMProvider.OPENAI)
    chain = CodeLLMChain(config)
    assert chain.llm is not None

async def test_response_generation():
    """응답 생성 테스트"""
    service = LLMService()
    response = await service.explain_code(
        "public void test() {}", "java", "이 메서드를 설명해주세요"
    )
    assert response.content != ""
    assert response.metadata.response_time_ms > 0

async def test_streaming_response():
    """스트리밍 응답 테스트"""
    service = LLMService()
    chunks = []
    async for chunk in service.generate_streaming_response(
        PromptType.CODE_EXPLANATION,
        code_content="public void test() {}",
        language="java"
    ):
        chunks.append(chunk)
    
    assert len(chunks) > 0

async def test_batch_processing():
    """배치 처리 테스트"""
    service = LLMService()
    requests = [
        {"type": "explain", "params": {"code_content": "test", "language": "java"}},
        {"type": "generate", "params": {"requirements": "간단한 함수", "language": "java"}}
    ]
    responses = await service.batch_process(requests, max_concurrent=2)
    assert len(responses) == 2
```

이 Task는 검색된 코드 컨텍스트를 기반으로 고품질 응답을 생성하는 핵심 구성요소입니다. 다양한 LLM과 프롬프트를 효과적으로 조합하여 최적의 사용자 경험을 제공합니다. 