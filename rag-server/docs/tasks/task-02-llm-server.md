# Task 02: LLM Server 구현

## 🎯 목표
vLLM 호환 API 인터페이스를 제공하면서 내부적으로는 OpenAI API를 사용하는 LLM 서비스를 TDD 방식으로 구현합니다.

## 📋 MVP 범위
- vLLM 호환 API 인터페이스 구현
- OpenAI API 프록시 기능
- gpt-4o-mini 기본 모델 사용
- 채팅 완성 및 텍스트 생성 API
- Docker 컨테이너화

## 🏗️ 기술 스택
- **웹 프레임워크**: FastAPI
- **LLM 서비스**: OpenAI API (gpt-4o-mini)
- **라이브러리**: openai, pydantic, httpx
- **컨테이너**: Docker
- **테스트**: pytest, httpx, pytest-mock

## 📁 프로젝트 구조

```
llm-server/
├── app/
│   ├── features/
│   │   └── llm/
│   │       ├── __init__.py
│   │       ├── router.py        ← vLLM 호환 API 엔드포인트
│   │       ├── service.py       ← LLM 서비스 로직
│   │       ├── schema.py        ← vLLM 호환 스키마
│   │       └── client.py        ← OpenAI API 클라이언트
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           ← 설정 관리
│   │   └── dependencies.py     ← 의존성 주입
│   ├── __init__.py
│   └── main.py                 ← FastAPI 애플리케이션
├── tests/
│   ├── unit/
│   │   └── features/
│   │       └── llm/
│   │           ├── test_router.py
│   │           ├── test_service.py
│   │           ├── test_schema.py
│   │           └── test_client.py
│   ├── integration/
│   │   └── test_llm_api.py
│   └── conftest.py
├── Dockerfile
├── requirements.txt
└── .dockerignore
```

## 🧪 TDD 구현 순서

### 1단계: OpenAI 클라이언트 클래스 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/llm/test_client.py
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.features.llm.client import OpenAIClient
from app.features.llm.schema import ChatCompletionRequest

@pytest.fixture
def mock_openai_client():
    mock_client = Mock()
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = AsyncMock()
    return mock_client

@pytest.mark.asyncio
async def test_openai_client_should_create_chat_completion(mock_openai_client):
    """OpenAI 클라이언트가 채팅 완성을 생성해야 함"""
    # Given
    client = OpenAIClient("test-api-key")
    client._client = mock_openai_client
    
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "테스트 응답"
    mock_response.model = "gpt-4o-mini"
    mock_response.usage.total_tokens = 100
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    request = ChatCompletionRequest(
        messages=[{"role": "user", "content": "안녕하세요"}],
        model="gpt-4o-mini"
    )
    
    # When
    response = await client.create_chat_completion(request)
    
    # Then
    assert response.choices[0].message.content == "테스트 응답"
    assert response.model == "gpt-4o-mini"
    mock_openai_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_openai_client_should_handle_api_error():
    """OpenAI 클라이언트가 API 오류를 처리해야 함"""
    # Given
    client = OpenAIClient("test-api-key")
    client._client = mock_openai_client
    
    mock_openai_client.chat.completions.create.side_effect = Exception("API 오류")
    
    request = ChatCompletionRequest(
        messages=[{"role": "user", "content": "안녕하세요"}],
        model="gpt-4o-mini"
    )
    
    # When & Then
    with pytest.raises(Exception) as exc_info:
        await client.create_chat_completion(request)
    
    assert "API 오류" in str(exc_info.value)
```

**🟢 최소 구현**
```python
# app/features/llm/client.py
import openai
from typing import Optional
from .schema import ChatCompletionRequest, ChatCompletionResponse

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
            response = await self._client.chat.completions.create(
                model=request.model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=request.stream
            )
            
            return ChatCompletionResponse(
                id=response.id,
                object=response.object,
                created=response.created,
                model=response.model,
                choices=response.choices,
                usage=response.usage
            )
        except Exception as e:
            raise Exception(f"OpenAI API 호출 실패: {str(e)}")
```

### 2단계: LLM 서비스 클래스 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/llm/test_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.features.llm.service import LLMService
from app.features.llm.schema import ChatCompletionRequest, ChatCompletionResponse

@pytest.fixture
def mock_openai_client():
    mock_client = Mock()
    mock_client.create_chat_completion = AsyncMock()
    return mock_client

@pytest.mark.asyncio
async def test_llm_service_should_create_chat_completion(mock_openai_client):
    """LLM 서비스가 채팅 완성을 생성해야 함"""
    # Given
    service = LLMService(mock_openai_client)
    mock_response = ChatCompletionResponse(
        id="test-id",
        object="chat.completion",
        created=1234567890,
        model="gpt-4o-mini",
        choices=[],
        usage=None
    )
    mock_openai_client.create_chat_completion.return_value = mock_response
    
    request = ChatCompletionRequest(
        messages=[{"role": "user", "content": "안녕하세요"}],
        model="gpt-4o-mini"
    )
    
    # When
    response = await service.create_chat_completion(request)
    
    # Then
    assert response.model == "gpt-4o-mini"
    mock_openai_client.create_chat_completion.assert_called_once_with(request)

@pytest.mark.asyncio
async def test_llm_service_should_use_default_model_when_not_specified():
    """LLM 서비스가 모델이 지정되지 않았을 때 기본 모델을 사용해야 함"""
    # Given
    service = LLMService(mock_openai_client)
    request = ChatCompletionRequest(
        messages=[{"role": "user", "content": "안녕하세요"}]
    )
    
    # When
    await service.create_chat_completion(request)
    
    # Then
    called_request = mock_openai_client.create_chat_completion.call_args[0][0]
    assert called_request.model == "gpt-4o-mini"
```

**🟢 최소 구현**
```python
# app/features/llm/service.py
from typing import Optional
from .client import OpenAIClient
from .schema import ChatCompletionRequest, ChatCompletionResponse

class LLMService:
    def __init__(self, openai_client: OpenAIClient):
        self.openai_client = openai_client
        self.default_model = "gpt-4o-mini"
    
    async def create_chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """채팅 완성 생성"""
        # 기본 모델 설정
        if not request.model:
            request.model = self.default_model
        
        return await self.openai_client.create_chat_completion(request)
    
    async def get_models(self) -> dict:
        """사용 가능한 모델 목록 반환 (vLLM 호환)"""
        return {
            "object": "list",
            "data": [
                {
                    "id": "gpt-4o-mini",
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "openai-proxy"
                }
            ]
        }
```

### 3단계: vLLM 호환 스키마 정의 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/llm/test_schema.py
import pytest
from pydantic import ValidationError
from app.features.llm.schema import (
    ChatCompletionRequest, ChatCompletionResponse,
    ChatMessage, Choice, Usage
)

def test_chat_completion_request_should_validate_messages():
    """채팅 완성 요청 스키마가 메시지를 정상 검증해야 함"""
    # Given & When
    request = ChatCompletionRequest(
        messages=[
            {"role": "user", "content": "안녕하세요"},
            {"role": "assistant", "content": "안녕하세요! 어떻게 도와드릴까요?"}
        ]
    )
    
    # Then
    assert len(request.messages) == 2
    assert request.messages[0]["role"] == "user"
    assert request.model == "gpt-4o-mini"  # 기본값

def test_chat_completion_request_should_reject_empty_messages():
    """채팅 완성 요청 스키마가 빈 메시지 리스트를 거부해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        ChatCompletionRequest(messages=[])

def test_chat_completion_request_should_validate_temperature_range():
    """채팅 완성 요청 스키마가 temperature 범위를 검증해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        ChatCompletionRequest(
            messages=[{"role": "user", "content": "테스트"}],
            temperature=2.5  # 유효 범위 초과
        )

def test_chat_message_should_validate_role():
    """채팅 메시지 스키마가 역할을 정상 검증해야 함"""
    # Given & When
    message = ChatMessage(role="user", content="테스트 메시지")
    
    # Then
    assert message.role == "user"
    assert message.content == "테스트 메시지"
```

**🟢 최소 구현**
```python
# app/features/llm/schema.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union, Dict, Any
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(BaseModel):
    role: MessageRole
    content: str

class ChatCompletionRequest(BaseModel):
    messages: List[Union[ChatMessage, Dict[str, str]]] = Field(..., min_items=1)
    model: str = Field(default="gpt-4o-mini")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, gt=0)
    stream: bool = Field(default=False)
    
    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError('메시지는 최소 1개 이상이어야 합니다')
        return v

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class Choice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Optional[Usage] = None

class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str

class ModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]
```

### 4단계: vLLM 호환 API 라우터 구현 (TDD)

**🔴 테스트 작성**
```python
# tests/integration/test_llm_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)

@patch('app.features.llm.client.OpenAIClient')
def test_chat_completions_endpoint_should_return_completion(mock_openai_client):
    """채팅 완성 엔드포인트가 완성을 반환해야 함"""
    # Given
    mock_instance = AsyncMock()
    mock_openai_client.return_value = mock_instance
    
    mock_response = {
        "id": "test-id",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "안녕하세요! 어떻게 도와드릴까요?"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }
    mock_instance.create_chat_completion.return_value = mock_response
    
    request_data = {
        "messages": [
            {"role": "user", "content": "안녕하세요"}
        ],
        "model": "gpt-4o-mini"
    }
    
    # When
    response = client.post("/v1/chat/completions", json=request_data)
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "gpt-4o-mini"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["content"] == "안녕하세요! 어떻게 도와드릴까요?"

def test_models_endpoint_should_return_available_models():
    """모델 목록 엔드포인트가 사용 가능한 모델을 반환해야 함"""
    # When
    response = client.get("/v1/models")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert len(data["data"]) >= 1
    assert data["data"][0]["id"] == "gpt-4o-mini"
```

**🟢 최소 구현**
```python
# app/features/llm/router.py
from fastapi import APIRouter, Depends, HTTPException
from .service import LLMService
from .schema import (
    ChatCompletionRequest, ChatCompletionResponse,
    ModelsResponse
)
from app.core.dependencies import get_llm_service

router = APIRouter()

@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest,
    service: LLMService = Depends(get_llm_service)
) -> ChatCompletionResponse:
    """채팅 완성 생성 (vLLM 호환)"""
    try:
        return await service.create_chat_completion(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models", response_model=ModelsResponse)
async def list_models(
    service: LLMService = Depends(get_llm_service)
) -> ModelsResponse:
    """사용 가능한 모델 목록 반환"""
    return await service.get_models()

@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "service": "llm-server"}
```

## 🐳 Docker 구성

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY app/ app/

# 포트 노출
EXPOSE 8002

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]
```

### requirements.txt
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
openai==1.3.0
pydantic==2.5.0
httpx==0.25.2
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
```

## 🔧 설정 관리

### app/core/config.py
```python
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    openai_api_key: str
    openai_base_url: Optional[str] = None
    default_model: str = "gpt-4o-mini"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### app/core/dependencies.py
```python
from functools import lru_cache
from .config import settings
from ..features.llm.client import OpenAIClient
from ..features.llm.service import LLMService

@lru_cache()
def get_openai_client() -> OpenAIClient:
    return OpenAIClient(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url
    )

def get_llm_service() -> LLMService:
    return LLMService(get_openai_client())
```

## ✅ 성공 기준

### 기능적 요구사항
- [ ] vLLM 호환 채팅 완성 API 구현
- [ ] 모델 목록 API 구현
- [ ] OpenAI API 프록시 기능 동작
- [ ] gpt-4o-mini 기본 모델 사용
- [ ] 적절한 에러 처리 및 응답

### 비기능적 요구사항
- [ ] 단위 테스트 커버리지 90% 이상
- [ ] 통합 테스트 통과
- [ ] Docker 컨테이너 정상 실행
- [ ] API 응답 시간 < 10초 (일반 요청)

### vLLM 호환성
- [ ] vLLM API 스키마와 호환
- [ ] 표준 엔드포인트 경로 사용 (/v1/chat/completions)
- [ ] 표준 응답 형식 준수

## 🚀 실행 방법

### 로컬 개발
```bash
# 환경 변수 설정
export OPENAI_API_KEY="your-api-key-here"

# 의존성 설치
pip install -r requirements.txt

# 테스트 실행
pytest tests/ -v --cov=app

# 서버 실행
uvicorn app.main:app --reload --port 8002
```

### Docker 실행
```bash
# 이미지 빌드
docker build -t llm-server .

# 컨테이너 실행
docker run -p 8002:8002 -v $(pwd):/app \
  -e OPENAI_API_KEY="your-api-key-here" \
  llm-server
```

## 📚 API 문서
서버 실행 후 http://localhost:8002/docs 에서 Swagger UI 확인

## 🔗 vLLM 호환성 확인
```bash
# vLLM 클라이언트로 테스트
curl -X POST "http://localhost:8002/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-4o-mini",
       "messages": [{"role": "user", "content": "안녕하세요"}]
     }'
```

## 🧪 Integration 테스트 단계

### LLM 서비스 통합 테스트

**목표**: LLM 서비스의 OpenAI API 호환성 및 실제 환경 동작 검증

```python
# tests/integration/test_llm_integration.py
import pytest
import httpx
import asyncio
import time

@pytest.mark.asyncio
class TestLLMIntegration:
    """LLM 서비스 통합 테스트"""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Docker Compose 환경에서 LLM 서비스 시작 확인"""
        async with httpx.AsyncClient() as client:
            # 서비스 준비 대기 (최대 120초 - LLM 모델 로딩 시간 고려)
            for _ in range(120):
                try:
                    response = await client.get("http://localhost:8002/health")
                    if response.status_code == 200:
                        break
                    await asyncio.sleep(1)
                except:
                    await asyncio.sleep(1)
            else:
                pytest.fail("LLM 서비스가 시작되지 않았습니다")
    
    async def test_openai_api_compatibility(self):
        """OpenAI API 호환성 테스트"""
        async with httpx.AsyncClient() as client:
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "user", "content": "Hello, how are you?"}
                ],
                "max_tokens": 100,
                "temperature": 0.7
            }
            
            response = await client.post(
                "http://localhost:8002/v1/chat/completions",
                json=payload,
                timeout=60.0
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # OpenAI API 형식 검증
            assert "choices" in result
            assert "message" in result["choices"][0]
            assert "content" in result["choices"][0]["message"]
            assert "usage" in result
            
            print(f"✅ OpenAI API 호환성 검증 완료")
            print(f"응답: {result['choices'][0]['message']['content'][:50]}...")
    
    async def test_streaming_response(self):
        """스트리밍 응답 테스트"""
        async with httpx.AsyncClient() as client:
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "user", "content": "Count from 1 to 5"}
                ],
                "max_tokens": 50,
                "stream": True
            }
            
            chunks_received = 0
            async with client.stream(
                "POST",
                "http://localhost:8002/v1/chat/completions",
                json=payload,
                timeout=60.0
            ) as response:
                assert response.status_code == 200
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        chunks_received += 1
                        if chunks_received >= 5:  # 충분한 청크 수신 확인
                            break
            
            assert chunks_received >= 5
            print(f"✅ 스트리밍 응답 테스트 완료: {chunks_received}개 청크 수신")
    
    async def test_concurrent_llm_requests(self):
        """동시 LLM 요청 처리 테스트"""
        async with httpx.AsyncClient() as client:
            tasks = []
            for i in range(5):  # LLM은 처리 시간이 길어 5개만 테스트
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "user", "content": f"Task {i}: Say hello"}
                    ],
                    "max_tokens": 20
                }
                task = client.post(
                    "http://localhost:8002/v1/chat/completions",
                    json=payload,
                    timeout=120.0
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = 0
            for response in responses:
                if not isinstance(response, Exception) and response.status_code == 200:
                    success_count += 1
            
            assert success_count >= 3, f"동시 요청 실패: {success_count}/5"
            print(f"✅ 동시 요청 성공: {success_count}/5")
    
    async def test_error_handling(self):
        """에러 처리 테스트"""
        async with httpx.AsyncClient() as client:
            # 잘못된 모델명
            payload = {
                "model": "invalid-model",
                "messages": [{"role": "user", "content": "test"}]
            }
            
            response = await client.post(
                "http://localhost:8002/v1/chat/completions",
                json=payload,
                timeout=30.0
            )
            
            assert response.status_code == 400
            error_result = response.json()
            assert "error" in error_result
            print(f"✅ 에러 처리 검증 완료")
    
    async def test_response_time_performance(self):
        """응답 시간 성능 테스트"""
        response_times = []
        
        async with httpx.AsyncClient() as client:
            for i in range(3):  # 3회 측정
                start_time = time.time()
                
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "user", "content": "Write a short hello message"}
                    ],
                    "max_tokens": 30
                }
                
                response = await client.post(
                    "http://localhost:8002/v1/chat/completions",
                    json=payload,
                    timeout=120.0
                )
                
                response_time = time.time() - start_time
                response_times.append(response_time)
                
                assert response.status_code == 200
        
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 30.0  # 평균 응답시간 30초 이내
        
        print(f"✅ 응답 시간 성능: 평균 {avg_response_time:.2f}초")
        print(f"개별 측정: {[f'{t:.2f}s' for t in response_times]}")
```

**실행 방법**:
```bash
# 환경 변수 설정
export OPENAI_API_KEY="your-api-key-here"

# Docker Compose 환경 시작
docker-compose up -d llm-server

# Integration 테스트 실행
pytest tests/integration/test_llm_integration.py -v

# 성공 기준
# - OpenAI API 호환성 검증 통과
# - 스트리밍 응답 정상 동작
# - 동시 요청 성공률 > 60%
# - 평균 응답 시간 < 30초
# - 에러 처리 적절
```

## 🔄 다음 단계
Task 03: Vector DB 구성 