# Task 05-D: 하이브리드 검색 서비스 구현

## 🎯 목표
벡터 검색과 키워드 검색을 결합한 하이브리드 검색 서비스를 TDD 방식으로 구현합니다.

## 📋 현재 프로젝트 구조 분석

### 🔍 기존 구현 현황
1. **임베딩 서버**: `sentence-transformers/all-MiniLM-L6-v2` 모델 사용
   - 단일/벌크 텍스트 임베딩 API 제공 (포트: 8001)
   - 스키마: `EmbeddingRequest`, `EmbeddingResponse`, `BulkEmbeddingRequest`, `BulkEmbeddingResponse`

2. **벡터 DB**: Qdrant 사용 (포트: 6333)
   - 컬렉션: `code_embeddings` (벡터 차원: 384, 거리: Cosine)
   - 기본 벡터 검색 기능 구현

3. **RAG 서버**: 오케스트레이션 서비스 (포트: 8000)
   - 기존 클라이언트: `EmbeddingClient`, `VectorClient`, `LLMClient`
   - 인덱싱 서비스 구현 완료 (코드 파싱 및 벡터 저장)

### 🚧 구현 필요 사항
- 하이브리드 검색 서비스 (벡터 + 키워드)
- 검색 결과 스코어링 및 랭킹
- 검색 REST API

## 🏗️ 기술 스택
- **웹 프레임워크**: FastAPI
- **벡터 검색**: Qdrant (기존 구현 활용)
- **키워드 검색**: BM25 기반 구현
- **임베딩**: 기존 embedding-server 활용
- **테스트**: pytest, httpx

## 📁 프로젝트 구조

```
rag-server/
├── app/
│   ├── features/
│   │   └── search/          ← 새로 구현할 검색 기능
│   │       ├── __init__.py
│   │       ├── router.py        ← 검색 API
│   │       ├── service.py       ← 검색 비즈니스 로직
│   │       ├── schema.py        ← 검색 스키마
│   │       ├── retriever.py     ← 하이브리드 검색기
│   │       └── scorer.py        ← 검색 결과 스코어링
│   └── core/                ← 기존 클라이언트 활용
│       └── clients.py       ← EmbeddingClient, VectorClient 활용
├── tests/
│   ├── unit/
│   │   └── features/
│   │       └── search/
│   │           ├── test_service.py
│   │           ├── test_retriever.py
│   │           ├── test_scorer.py
│   │           └── test_router.py
│   └── integration/
│       └── test_search_api.py
└── requirements.txt
```

## 🧪 TDD 구현 순서

### 1단계: 검색 스키마 정의 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/search/test_schema.py
import pytest
from pydantic import ValidationError
from app.features.search.schema import SearchRequest, SearchResponse

def test_search_request_should_validate_required_fields():
    """검색 요청이 필수 필드를 검증해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        SearchRequest()  # query 필드 누락
    
    # Valid request
    request = SearchRequest(query="test function")
    assert request.query == "test function"
    assert request.limit == 10  # 기본값
    assert request.vector_weight == 0.7  # 기본값
    assert request.keyword_weight == 0.3  # 기본값

def test_search_request_should_validate_weights():
    """검색 요청이 가중치를 검증해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        SearchRequest(query="test", vector_weight=1.5)  # 1.0 초과
    
    with pytest.raises(ValidationError):
        SearchRequest(query="test", keyword_weight=-0.1)  # 0.0 미만
```

**🟢 최소 구현**
```python
# app/features/search/schema.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class SearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리")
    keywords: Optional[List[str]] = Field(default=None, description="키워드 필터")
    limit: int = Field(default=10, min=1, max=50, description="결과 개수")
    vector_weight: float = Field(default=0.7, min=0.0, max=1.0, description="벡터 가중치")
    keyword_weight: float = Field(default=0.3, min=0.0, max=1.0, description="키워드 가중치")
    collection_name: str = Field(default="code_embeddings", description="검색할 컬렉션")
    
    @validator('vector_weight', 'keyword_weight')
    def validate_weights(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('가중치는 0.0과 1.0 사이여야 합니다')
        return v

class SearchResult(BaseModel):
    id: str
    file_path: str
    function_name: Optional[str] = None
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
    vector_results_count: int
    keyword_results_count: int
```

### 2단계: 하이브리드 검색기 구현 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/search/test_retriever.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.features.search.retriever import HybridRetriever

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
async def test_hybrid_retriever_should_combine_results(
    mock_embedding_client, mock_vector_client
):
    """하이브리드 검색기가 벡터와 키워드 결과를 결합해야 함"""
    # Given
    retriever = HybridRetriever(mock_embedding_client, mock_vector_client)
    
    mock_embedding_client.embed_single.return_value = {
        "embedding": [0.1, 0.2, 0.3]
    }
    
    mock_vector_client.hybrid_search.return_value = [
        {
            "id": "1", 
            "vector_score": 0.9, 
            "keyword_score": 0.7,
            "file_path": "test.py",
            "code_content": "def test(): pass",
            "code_type": "function",
            "language": "python",
            "line_start": 1,
            "line_end": 1,
            "keywords": ["test"]
        }
    ]
    
    # When
    results = await retriever.search(
        query="test function",
        keywords=["test"],
        limit=10,
        collection_name="code_embeddings"
    )
    
    # Then
    assert len(results) == 1
    assert results[0]["id"] == "1"
    assert "vector_score" in results[0]
    assert "keyword_score" in results[0]
    mock_embedding_client.embed_single.assert_called_once()
    mock_vector_client.hybrid_search.assert_called_once()
```

**🟢 최소 구현**
```python
# app/features/search/retriever.py
from typing import List, Dict, Any, Optional
from app.core.clients import EmbeddingClient, VectorClient
import logging

logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, embedding_client: EmbeddingClient, vector_client: VectorClient):
        self.embedding_client = embedding_client
        self.vector_client = vector_client
    
    async def search(
        self, 
        query: str,
        keywords: Optional[List[str]] = None,
        limit: int = 10,
        collection_name: str = "code_embeddings"
    ) -> List[Dict[str, Any]]:
        """하이브리드 검색 수행"""
        try:
            # 쿼리 임베딩 생성
            embedding_response = await self.embedding_client.embed_single({
                "text": query
            })
            query_embedding = embedding_response["embedding"]
            
            # 벡터 DB에서 하이브리드 검색 수행 (기존 구현 활용)
            results = self.vector_client.hybrid_search(
                collection_name=collection_name,
                query_embedding=query_embedding,
                keywords=keywords,
                limit=limit
            )
            
            return results
            
        except Exception as e:
            logger.error(f"하이브리드 검색 실패: {e}")
            raise
```

### 3단계: 스코어링 시스템 구현 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/search/test_scorer.py
import pytest
from app.features.search.scorer import SearchScorer

def test_search_scorer_should_calculate_combined_score():
    """스코어러가 결합 점수를 계산해야 함"""
    # Given
    scorer = SearchScorer()
    
    results = [
        {"id": "1", "vector_score": 0.9, "keyword_score": 0.7},
        {"id": "2", "vector_score": 0.8, "keyword_score": 0.6},
        {"id": "3", "vector_score": 0.7, "keyword_score": 0.9}
    ]
    
    # When
    scored_results = scorer.calculate_combined_scores(
        results, vector_weight=0.7, keyword_weight=0.3
    )
    
    # Then
    assert scored_results[0]["combined_score"] == 0.9 * 0.7 + 0.7 * 0.3
    assert scored_results[1]["combined_score"] == 0.8 * 0.7 + 0.6 * 0.3
    assert scored_results[2]["combined_score"] == 0.7 * 0.7 + 0.9 * 0.3

def test_search_scorer_should_sort_by_combined_score():
    """스코어러가 결합 점수 순으로 정렬해야 함"""
    # Given
    scorer = SearchScorer()
    
    results = [
        {"id": "1", "vector_score": 0.5, "keyword_score": 0.9},  # 0.65
        {"id": "2", "vector_score": 0.9, "keyword_score": 0.5},  # 0.78  
        {"id": "3", "vector_score": 0.8, "keyword_score": 0.8}   # 0.8
    ]
    
    # When
    scored_results = scorer.calculate_combined_scores(
        results, vector_weight=0.7, keyword_weight=0.3
    )
    
    # Then
    assert scored_results[0]["id"] == "3"  # 가장 높은 점수
    assert scored_results[1]["id"] == "2"
    assert scored_results[2]["id"] == "1"
```

**🟢 최소 구현**
```python
# app/features/search/scorer.py
from typing import List, Dict, Any

class SearchScorer:
    def calculate_combined_scores(
        self, 
        results: List[Dict[str, Any]], 
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """결합 점수 계산 및 정렬"""
        for result in results:
            vector_score = result.get("vector_score", 0.0)
            keyword_score = result.get("keyword_score", 0.0)
            
            combined_score = (
                vector_score * vector_weight + 
                keyword_score * keyword_weight
            )
            
            result["combined_score"] = combined_score
        
        # 결합 점수 기준 내림차순 정렬
        return sorted(results, key=lambda x: x["combined_score"], reverse=True)
    
    def normalize_scores(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """점수 정규화 (0-1 범위)"""
        if not results:
            return results
        
        # 각 점수 타입별 최대값 찾기
        max_vector = max(r.get("vector_score", 0.0) for r in results)
        max_keyword = max(r.get("keyword_score", 0.0) for r in results)
        
        # 정규화 적용
        for result in results:
            if max_vector > 0:
                result["vector_score"] = result.get("vector_score", 0.0) / max_vector
            if max_keyword > 0:
                result["keyword_score"] = result.get("keyword_score", 0.0) / max_keyword
        
        return results
```

### 4단계: 검색 서비스 구현 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/search/test_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.features.search.service import SearchService
from app.features.search.schema import SearchRequest

@pytest.fixture
def mock_retriever():
    retriever = Mock()
    retriever.search = AsyncMock()
    return retriever

@pytest.fixture
def mock_scorer():
    scorer = Mock()
    scorer.calculate_combined_scores = Mock()
    return scorer

@pytest.mark.asyncio
async def test_search_service_should_perform_hybrid_search(
    mock_retriever, mock_scorer
):
    """검색 서비스가 하이브리드 검색을 수행해야 함"""
    # Given
    service = SearchService(mock_retriever, mock_scorer)
    
    mock_retriever.search.return_value = [
        {
            "id": "test-id-1",
            "vector_score": 0.9,
            "keyword_score": 0.8,
            "file_path": "test.py",
            "function_name": "test_func",
            "code_content": "def test_func(): pass",
            "code_type": "function",
            "language": "python",
            "line_start": 1,
            "line_end": 1,
            "keywords": ["test", "func"]
        }
    ]
    
    mock_scorer.calculate_combined_scores.return_value = [
        {
            "id": "test-id-1",
            "vector_score": 0.9,
            "keyword_score": 0.8,
            "combined_score": 0.86,
            "file_path": "test.py",
            "function_name": "test_func",
            "code_content": "def test_func(): pass",
            "code_type": "function", 
            "language": "python",
            "line_start": 1,
            "line_end": 1,
            "keywords": ["test", "func"]
        }
    ]
    
    request = SearchRequest(query="test function", keywords=["test"])
    
    # When
    result = await service.search_code(request)
    
    # Then
    assert result.total_results == 1
    assert result.results[0].function_name == "test_func"
    assert result.results[0].combined_score == 0.86
    mock_retriever.search.assert_called_once()
    mock_scorer.calculate_combined_scores.assert_called_once()
```

**🟢 최소 구현**
```python
# app/features/search/service.py
import time
from typing import List
from .schema import SearchRequest, SearchResponse, SearchResult
from .retriever import HybridRetriever
from .scorer import SearchScorer
import logging

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, retriever: HybridRetriever, scorer: SearchScorer):
        self.retriever = retriever
        self.scorer = scorer
    
    async def search_code(self, request: SearchRequest) -> SearchResponse:
        """코드 하이브리드 검색"""
        start_time = time.time()
        
        try:
            # 하이브리드 검색 수행
            raw_results = await self.retriever.search(
                query=request.query,
                keywords=request.keywords,
                limit=request.limit,
                collection_name=request.collection_name
            )
            
            # 점수 계산 및 정렬
            scored_results = self.scorer.calculate_combined_scores(
                raw_results,
                vector_weight=request.vector_weight,
                keyword_weight=request.keyword_weight
            )
            
            # 결과 변환
            search_results = []
            vector_count = 0
            keyword_count = 0
            
            for result in scored_results:
                search_result = SearchResult(
                    id=result["id"],
                    file_path=result.get("file_path", ""),
                    function_name=result.get("function_name"),
                    code_content=result.get("code_content", ""),
                    code_type=result.get("code_type", ""),
                    language=result.get("language", ""),
                    line_start=result.get("line_start", 0),
                    line_end=result.get("line_end", 0),
                    keywords=result.get("keywords", []),
                    vector_score=result["vector_score"],
                    keyword_score=result["keyword_score"],
                    combined_score=result["combined_score"]
                )
                search_results.append(search_result)
                
                if result["vector_score"] > 0:
                    vector_count += 1
                if result["keyword_score"] > 0:
                    keyword_count += 1
            
            end_time = time.time()
            search_time_ms = int((end_time - start_time) * 1000)
            
            return SearchResponse(
                query=request.query,
                results=search_results,
                total_results=len(search_results),
                search_time_ms=search_time_ms,
                vector_results_count=vector_count,
                keyword_results_count=keyword_count
            )
            
        except Exception as e:
            logger.error(f"코드 검색 실패: {e}")
            raise
```

### 5단계: API 라우터 구현 (TDD)

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
                keyword_score=0.8, combined_score=0.86
            )
        ],
        total_results=1,
        search_time_ms=100,
        vector_results_count=1,
        keyword_results_count=1
    )
    
    # Mock dependency
    from app.features.search.service import SearchService
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
    
    # Cleanup
    del app.dependency_overrides[SearchService]
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
    """코드 하이브리드 검색
    
    벡터 검색과 키워드 검색을 결합하여 관련 코드를 찾습니다.
    """
    try:
        logger.info(f"검색 요청: {request.query}")
        result = await service.search_code(request)
        logger.info(f"검색 완료: {result.total_results}개 결과, {result.search_time_ms}ms")
        return result
    except Exception as e:
        logger.error(f"검색 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"검색 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """검색 서비스 헬스체크"""
    return {
        "status": "healthy",
        "service": "search-service"
    }
```

## 🧪 Integration 테스트

```python
# tests/integration/test_search_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.integration
def test_search_api_integration():
    """검색 API 통합 테스트"""
    client = TestClient(app)
    
    # When: 검색 수행
    response = client.post("/api/v1/search", json={
        "query": "function to calculate fibonacci",
        "limit": 5,
        "vector_weight": 0.7,
        "keyword_weight": 0.3
    })
    
    # Then: 성공적인 응답
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "results" in data
    assert "total_results" in data
    assert "search_time_ms" in data
    assert data["search_time_ms"] < 5000  # 5초 이내

@pytest.mark.integration  
def test_search_performance():
    """검색 성능 테스트"""
    client = TestClient(app)
    
    # When: 다양한 쿼리로 검색
    queries = [
        "recursive function",
        "data processing", 
        "error handling",
        "database connection",
        "API endpoint"
    ]
    
    for query in queries:
        response = client.post("/api/v1/search", json={
            "query": query,
            "limit": 10
        })
        
        # Then: 성능 기준 충족
        assert response.status_code == 200
        data = response.json()
        assert data["search_time_ms"] < 5000  # 5초 이내
```

## 📊 성공 기준
1. **검색 성능**: 쿼리 당 5초 이내 응답
2. **검색 정확도**: 관련 코드 검색 정확도 80% 이상  
3. **하이브리드 효과**: 벡터+키워드 결합이 단일 방식보다 10% 이상 성능 향상
4. **API 안정성**: 99% 이상 성공률
5. **테스트 커버리지**: 90% 이상

## 📈 다음 단계
- Task 05-E: 코드 생성 서비스 구현
- Task 05-F: 프롬프트 관리 서비스 구현  
- 검색 서비스와 생성 서비스 통합

## 🔄 TDD 사이클 요약
1. **Red**: 검색 기능별 테스트 작성 → 실패
2. **Green**: 하이브리드 검색 구현 → 테스트 통과  
3. **Refactor**: 검색 성능 최적화, 코드 정리

이 Task는 RAG 시스템의 핵심인 검색 기능을 완성하여 다음 단계인 코드 생성의 기반을 마련합니다. 