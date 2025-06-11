# Task 05-D: 검색 및 코드 생성 서비스 구현

## 🎯 목표
하이브리드 검색과 코드 생성 기능을 통합한 RAG 서비스를 TDD 방식으로 구현합니다.

## 📋 MVP 범위
- 하이브리드 검색 서비스 (벡터 + 키워드)
- 코드 생성 서비스 (RAG 기반)
- 검색 및 생성 REST API
- 컨텍스트 기반 코드 생성

## 🏗️ 기술 스택
- **웹 프레임워크**: FastAPI
- **RAG 파이프라인**: LangChain/커스텀 구현
- **프롬프트 엔지니어링**: 컨텍스트 기반 템플릿
- **테스트**: pytest, httpx

## 📁 프로젝트 구조

```
rag-server/
├── app/
│   ├── features/
│   │   ├── search/
│   │   │   ├── __init__.py
│   │   │   ├── router.py        ← 검색 API
│   │   │   ├── service.py       ← 검색 비즈니스 로직
│   │   │   ├── schema.py        ← 검색 스키마
│   │   │   └── retriever.py     ← 하이브리드 검색기
│   │   └── generation/
│   │       ├── __init__.py
│   │       ├── router.py        ← 생성 API
│   │       ├── service.py       ← 생성 비즈니스 로직
│   │       ├── schema.py        ← 생성 스키마
│   │       ├── generator.py     ← 코드 생성기
│   │       └── prompts.py       ← 프롬프트 템플릿
│   └── main.py
├── tests/
│   ├── unit/
│   │   └── features/
│   │       ├── search/
│   │       └── generation/
│   └── integration/
│       ├── test_search_api.py
│       └── test_generation_api.py
├── requirements.txt
└── pytest.ini
```

## 🧪 TDD 구현 순서

### 1단계: 검색 스키마 및 서비스 (TDD)

**스키마 정의**
```python
# app/features/search/schema.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class SearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리")
    keywords: Optional[List[str]] = Field(default=None, description="키워드 필터")
    limit: int = Field(default=10, min=1, max=50, description="결과 개수")
    vector_weight: float = Field(default=0.7, min=0.0, max=1.0, description="벡터 가중치")
    keyword_weight: float = Field(default=0.3, min=0.0, max=1.0, description="키워드 가중치")

class SearchResult(BaseModel):
    id: str
    file_path: str
    function_name: str
    code_content: str
    code_type: str
    language: str
    line_start: int
    line_end: int
    keywords: List[str]
    vector_score: float
    keyword_score: float
    combined_score: float

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
```

**🔴 테스트 작성**
```python
# tests/unit/features/search/test_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.features.search.service import SearchService
from app.features.search.schema import SearchRequest

@pytest.fixture
def mock_embedding_client():
    client = Mock()
    client.embed_single = AsyncMock()
    return client

@pytest.fixture
def mock_vector_client():
    client = Mock()
    client.hybrid_search = Mock()
    return client

@pytest.mark.asyncio
async def test_search_service_should_perform_hybrid_search(
    mock_embedding_client, mock_vector_client
):
    """검색 서비스가 하이브리드 검색을 수행해야 함"""
    # Given
    service = SearchService(mock_embedding_client, mock_vector_client)
    
    mock_embedding_client.embed_single.return_value = {
        "embedding": [0.1, 0.2, 0.3]
    }
    
    mock_vector_client.hybrid_search.return_value = [
        {
            "id": "test-id",
            "file_path": "test.py",
            "function_name": "test_func",
            "code_content": "def test_func(): pass",
            "code_type": "function",
            "language": "python",
            "line_start": 1,
            "line_end": 1,
            "keywords": ["test", "func"],
            "vector_score": 0.9,
            "keyword_score": 0.8,
            "combined_score": 0.85
        }
    ]
    
    request = SearchRequest(query="test function", keywords=["test"])
    
    # When
    result = await service.search_code(request)
    
    # Then
    assert result.total_results == 1
    assert result.results[0].function_name == "test_func"
    assert result.results[0].combined_score == 0.85
    mock_embedding_client.embed_single.assert_called_once()
    mock_vector_client.hybrid_search.assert_called_once()

@pytest.mark.asyncio
async def test_search_service_should_handle_empty_results(
    mock_embedding_client, mock_vector_client
):
    """검색 서비스가 빈 결과를 처리해야 함"""
    # Given
    service = SearchService(mock_embedding_client, mock_vector_client)
    
    mock_embedding_client.embed_single.return_value = {
        "embedding": [0.1, 0.2, 0.3]
    }
    
    mock_vector_client.hybrid_search.return_value = []
    
    request = SearchRequest(query="nonexistent function")
    
    # When
    result = await service.search_code(request)
    
    # Then
    assert result.total_results == 0
    assert len(result.results) == 0
```

**🟢 최소 구현**
```python
# app/features/search/service.py
import time
from typing import List
from .schema import SearchRequest, SearchResponse, SearchResult
from app.core.clients import EmbeddingClient, VectorClient
import logging

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, embedding_client: EmbeddingClient, vector_client: VectorClient):
        self.embedding_client = embedding_client
        self.vector_client = vector_client
        self.collection_name = "code_chunks"
    
    async def search_code(self, request: SearchRequest) -> SearchResponse:
        """코드 하이브리드 검색"""
        start_time = time.time()
        
        try:
            # 쿼리 임베딩 생성
            embedding_response = await self.embedding_client.embed_single({
                "text": request.query
            })
            query_embedding = embedding_response["embedding"]
            
            # 하이브리드 검색 수행
            search_results = self.vector_client.hybrid_search(
                collection_name=self.collection_name,
                query_embedding=query_embedding,
                keywords=request.keywords,
                limit=request.limit
            )
            
            # 결과 변환
            results = []
            for result in search_results:
                search_result = SearchResult(
                    id=result["id"],
                    file_path=result["file_path"],
                    function_name=result["function_name"],
                    code_content=result["code_content"],
                    code_type=result["code_type"],
                    language=result["language"],
                    line_start=result["line_start"],
                    line_end=result["line_end"],
                    keywords=result["keywords"],
                    vector_score=result["vector_score"],
                    keyword_score=result["keyword_score"],
                    combined_score=result["combined_score"]
                )
                results.append(search_result)
            
            end_time = time.time()
            search_time_ms = int((end_time - start_time) * 1000)
            
            return SearchResponse(
                query=request.query,
                results=results,
                total_results=len(results),
                search_time_ms=search_time_ms
            )
            
        except Exception as e:
            logger.error(f"코드 검색 실패: {e}")
            raise
```

### 2단계: 코드 생성 서비스 (TDD)

**스키마 정의**
```python
# app/features/generation/schema.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class GenerationRequest(BaseModel):
    query: str = Field(..., description="코드 생성 요청")
    context_limit: int = Field(default=3, min=1, max=10, description="컨텍스트 개수")
    language: str = Field(default="python", description="생성할 코드 언어")
    include_tests: bool = Field(default=False, description="테스트 코드 포함 여부")

class CodeContext(BaseModel):
    function_name: str
    code_content: str
    file_path: str
    relevance_score: float

class GenerationResponse(BaseModel):
    query: str
    generated_code: str
    contexts_used: List[CodeContext]
    generation_time_ms: int
    model_used: str
```

**🔴 테스트 작성**
```python
# tests/unit/features/generation/test_service.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.features.generation.service import GenerationService
from app.features.generation.schema import GenerationRequest
from app.features.search.schema import SearchResult

@pytest.fixture
def mock_search_service():
    service = Mock()
    service.search_code = AsyncMock()
    return service

@pytest.fixture
def mock_llm_client():
    client = Mock()
    client.chat_completion = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_generation_service_should_generate_code_with_context(
    mock_search_service, mock_llm_client
):
    """생성 서비스가 컨텍스트를 사용하여 코드를 생성해야 함"""
    # Given
    service = GenerationService(mock_search_service, mock_llm_client)
    
    # Mock 검색 결과
    mock_search_results = [
        SearchResult(
            id="1", file_path="test.py", function_name="test_func",
            code_content="def test_func(): pass", code_type="function",
            language="python", line_start=1, line_end=1,
            keywords=["test"], vector_score=0.9,
            keyword_score=0.8, combined_score=0.85
        )
    ]
    
    mock_search_service.search_code.return_value.results = mock_search_results
    
    # Mock LLM 응답
    mock_llm_client.chat_completion.return_value = {
        "choices": [
            {
                "message": {
                    "content": "def calculate_sum(a, b):\n    return a + b"
                }
            }
        ]
    }
    
    request = GenerationRequest(query="Create a function to calculate sum")
    
    # When
    result = await service.generate_code(request)
    
    # Then
    assert result.generated_code == "def calculate_sum(a, b):\n    return a + b"
    assert len(result.contexts_used) == 1
    assert result.contexts_used[0].function_name == "test_func"
    mock_search_service.search_code.assert_called_once()
    mock_llm_client.chat_completion.assert_called_once()
```

**🟢 최소 구현**
```python
# app/features/generation/service.py
import time
from typing import List
from .schema import GenerationRequest, GenerationResponse, CodeContext
from .prompts import CodeGenerationPrompts
from app.features.search.service import SearchService
from app.features.search.schema import SearchRequest
from app.core.clients import LLMClient
import logging

logger = logging.getLogger(__name__)

class GenerationService:
    def __init__(self, search_service: SearchService, llm_client: LLMClient):
        self.search_service = search_service
        self.llm_client = llm_client
        self.prompts = CodeGenerationPrompts()
    
    async def generate_code(self, request: GenerationRequest) -> GenerationResponse:
        """컨텍스트 기반 코드 생성"""
        start_time = time.time()
        
        try:
            # 관련 코드 검색
            search_request = SearchRequest(
                query=request.query,
                limit=request.context_limit
            )
            search_response = await self.search_service.search_code(search_request)
            
            # 컨텍스트 준비
            contexts = []
            for result in search_response.results:
                context = CodeContext(
                    function_name=result.function_name,
                    code_content=result.code_content,
                    file_path=result.file_path,
                    relevance_score=result.combined_score
                )
                contexts.append(context)
            
            # 프롬프트 생성
            system_prompt = self.prompts.get_system_prompt(request.language)
            user_prompt = self.prompts.get_user_prompt(
                request.query, contexts, request.include_tests
            )
            
            # LLM 호출
            llm_response = await self.llm_client.chat_completion({
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 2000
            })
            
            generated_code = llm_response["choices"][0]["message"]["content"]
            
            end_time = time.time()
            generation_time_ms = int((end_time - start_time) * 1000)
            
            return GenerationResponse(
                query=request.query,
                generated_code=generated_code,
                contexts_used=contexts,
                generation_time_ms=generation_time_ms,
                model_used="gpt-4o-mini"
            )
            
        except Exception as e:
            logger.error(f"코드 생성 실패: {e}")
            raise
```

### 3단계: 프롬프트 템플릿 (TDD)

```python
# app/features/generation/prompts.py
from typing import List
from .schema import CodeContext

class CodeGenerationPrompts:
    def get_system_prompt(self, language: str = "python") -> str:
        """시스템 프롬프트 생성"""
        return f"""당신은 {language} 코드 생성 전문가입니다.
        
주요 원칙:
1. 제공된 기존 코드 패턴과 스타일을 따르세요
2. 깔끔하고 읽기 쉬운 코드를 작성하세요
3. 적절한 독스트링과 주석을 포함하세요
4. 에러 처리를 고려하세요
5. 타입 힌트를 사용하세요 (Python 3.6+)

코드만 반환하고 추가 설명은 하지 마세요."""

    def get_user_prompt(self, query: str, contexts: List[CodeContext], 
                       include_tests: bool = False) -> str:
        """사용자 프롬프트 생성"""
        prompt = f"요청: {query}\n\n"
        
        if contexts:
            prompt += "참고할 기존 코드:\n\n"
            for i, context in enumerate(contexts, 1):
                prompt += f"예시 {i} ({context.function_name}):\n"
                prompt += f"```python\n{context.code_content}\n```\n\n"
        
        prompt += f"위 예시들을 참고하여 '{query}'에 대한 코드를 생성해주세요."
        
        if include_tests:
            prompt += " 테스트 코드도 함께 포함해주세요."
        
        return prompt
```

### 4단계: API 라우터 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/search/test_router.py
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app

def test_search_endpoint_should_return_results():
    """검색 엔드포인트가 결과를 반환해야 함"""
    # Given
    from app.features.search.schema import SearchResponse, SearchResult
    mock_response = SearchResponse(
        query="test function",
        results=[
            SearchResult(
                id="1", file_path="test.py", function_name="test_func",
                code_content="def test_func(): pass", code_type="function",
                language="python", line_start=1, line_end=1,
                keywords=["test"], vector_score=0.9,
                keyword_score=0.8, combined_score=0.85
            )
        ],
        total_results=1,
        search_time_ms=100
    )
    
    # Mock dependency
    mock_service = Mock()
    mock_service.search_code = AsyncMock(return_value=mock_response)
    
    app.dependency_overrides[SearchService] = lambda: mock_service
    client = TestClient(app)
    
    # When
    response = client.post("/api/v1/search", json={
        "query": "test function",
        "limit": 10
    })
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["function_name"] == "test_func"
```

**🟢 최소 구현**
```python
# app/features/search/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from .service import SearchService
from .schema import SearchRequest, SearchResponse
from app.core.dependencies import get_search_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["search"])

@router.post("/", response_model=SearchResponse)
async def search_code(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service)
) -> SearchResponse:
    """코드 검색"""
    try:
        return await service.search_code(request)
    except Exception as e:
        logger.error(f"검색 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"검색 중 오류가 발생했습니다: {str(e)}"
        )

# app/features/generation/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from .service import GenerationService
from .schema import GenerationRequest, GenerationResponse
from app.core.dependencies import get_generation_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/generate", tags=["generation"])

@router.post("/", response_model=GenerationResponse)
async def generate_code(
    request: GenerationRequest,
    service: GenerationService = Depends(get_generation_service)
) -> GenerationResponse:
    """코드 생성"""
    try:
        return await service.generate_code(request)
    except Exception as e:
        logger.error(f"코드 생성 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"코드 생성 중 오류가 발생했습니다: {str(e)}"
        )
```

## 🧪 Integration 테스트

```python
# tests/integration/test_rag_workflow.py
import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.integration
def test_full_rag_workflow():
    """전체 RAG 워크플로우 integration 테스트"""
    # Given: 코드 파일 인덱싱
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
def fibonacci(n):
    """피보나치 수열을 계산하는 함수"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    """팩토리얼을 계산하는 함수"""
    if n <= 1:
        return 1
    return n * factorial(n-1)
''')
        temp_file_path = f.name
    
    try:
        client = TestClient(app)
        
        # 1. 파일 인덱싱
        index_response = client.post("/api/v1/indexing/file", json={
            "file_path": temp_file_path,
            "force_update": True
        })
        assert index_response.status_code == 200
        
        # 2. 코드 검색
        search_response = client.post("/api/v1/search", json={
            "query": "recursive function",
            "limit": 5
        })
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["total_results"] > 0
        
        # 3. 코드 생성
        generate_response = client.post("/api/v1/generate", json={
            "query": "Create a recursive function to calculate power",
            "context_limit": 2,
            "language": "python"
        })
        assert generate_response.status_code == 200
        generate_data = generate_response.json()
        assert "def" in generate_data["generated_code"]
        assert len(generate_data["contexts_used"]) > 0
        
    finally:
        os.unlink(temp_file_path)

@pytest.mark.integration
def test_search_performance():
    """검색 성능 테스트"""
    client = TestClient(app)
    
    # When: 검색 수행
    response = client.post("/api/v1/search", json={
        "query": "function calculation",
        "limit": 20
    })
    
    # Then: 성능 기준 충족
    assert response.status_code == 200
    data = response.json()
    assert data["search_time_ms"] < 5000  # 5초 이내

@pytest.mark.integration  
def test_generation_with_different_contexts():
    """다양한 컨텍스트로 코드 생성 테스트"""
    client = TestClient(app)
    
    # When: 다양한 요청으로 코드 생성
    requests = [
        "Create a sorting algorithm",
        "Write a class for data processing",
        "Implement error handling for file operations"
    ]
    
    for query in requests:
        response = client.post("/api/v1/generate", json={
            "query": query,
            "context_limit": 3,
            "include_tests": True
        })
        
        # Then: 성공적으로 생성됨
        assert response.status_code == 200
        data = response.json()
        assert data["generated_code"]
        assert data["generation_time_ms"] < 60000  # 1분 이내
```

## 📊 성공 기준
1. **검색 성능**: 쿼리 당 5초 이내 응답
2. **생성 품질**: 생성된 코드가 구문적으로 올바름
3. **컨텍스트 활용**: 관련 코드 패턴 반영도 80% 이상
4. **응답 속도**: 코드 생성 60초 이내
5. **정확도**: 사용자 의도 반영도 85% 이상 (수동 평가)

## 📈 다음 단계
- Task 06: 전체 시스템 통합 테스트 및 검증
- 성능 최적화 및 모니터링 구현
- 프로덕션 배포 준비

## 🔄 TDD 사이클 요약
1. **Red**: 검색/생성 서비스 테스트 작성 → 실패
2. **Green**: RAG 파이프라인 및 API 구현 → 테스트 통과  
3. **Refactor**: 프롬프트 최적화, 성능 개선, 코드 정리

이 Task는 RAG 시스템의 핵심 기능인 검색과 생성을 완성하여 사용자에게 가치를 제공하는 마지막 단계입니다. 