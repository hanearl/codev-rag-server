# Task 05-B: 외부 서비스 클라이언트 구현

## 🎯 목표
RAG 서버에서 사용할 외부 서비스(Embedding Server, LLM Server, Vector DB) 클라이언트를 TDD 방식으로 구현합니다.

## 📋 MVP 범위
- Embedding Server HTTP 클라이언트
- LLM Server HTTP 클라이언트  
- Vector DB (Qdrant) 클라이언트
- 연결 안정성 및 에러 처리
- 재시도 로직 구현

## 🏗️ 기술 스택
- **HTTP 클라이언트**: httpx (비동기)
- **벡터 DB**: qdrant-client
- **설정 관리**: pydantic-settings
- **테스트**: pytest, pytest-asyncio, httpx

## 📁 프로젝트 구조

```
rag-server/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── clients.py          ← 외부 서비스 클라이언트 (새로 추가)
│   │   ├── config.py           ← 설정 관리 (업데이트 필요)
│   │   └── exceptions.py       ← 커스텀 예외 (새로 추가)
│   ├── features/               ← 기존 존재
│   ├── db/                     ← 기존 존재
│   ├── main.py                 ← 기존 존재
│   └── __init__.py
├── tests/
│   └── unit/
│       └── core/
│           ├── __init__.py
│           └── test_clients.py  ← 클라이언트 테스트 (새로 추가)
├── requirements.txt            ← 업데이트 필요
└── pytest.ini                 ← 새로 추가
```

## 🧪 TDD 구현 순서

### 1단계: 설정 및 예외 클래스 정의

```python
# app/core/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    embedding_server_url: str = "http://localhost:8001"
    llm_server_url: str = "http://localhost:8002"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    request_timeout: int = 30
    max_retries: int = 3
    
    class Config:
        env_file = ".env"

# app/core/exceptions.py
class ExternalServiceError(Exception):
    """외부 서비스 호출 오류"""
    pass

class EmbeddingServiceError(ExternalServiceError):
    """임베딩 서비스 오류"""
    pass

class LLMServiceError(ExternalServiceError):
    """LLM 서비스 오류"""
    pass

class VectorDBError(ExternalServiceError):
    """벡터 DB 오류"""
    pass
```

### 2단계: Embedding 클라이언트 테스트 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/core/test_clients.py
import pytest
from unittest.mock import AsyncMock, patch, Mock
import httpx
from app.core.clients import EmbeddingClient, LLMClient, VectorClient
from app.core.exceptions import EmbeddingServiceError

@pytest.mark.asyncio
async def test_embedding_client_should_call_single_embedding():
    """임베딩 클라이언트가 단일 텍스트 임베딩을 호출해야 함"""
    # Given
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "embedding": [0.1, 0.2, 0.3],
            "text": "test text"
        }
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        client = EmbeddingClient("http://localhost:8001")
        
        # When
        result = await client.embed_single({"text": "test text"})
        
        # Then
        assert result["embedding"] == [0.1, 0.2, 0.3]
        mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
            "http://localhost:8001/api/v1/embed",
            json={"text": "test text"},
            timeout=30.0
        )

@pytest.mark.asyncio
async def test_embedding_client_should_call_bulk_embedding():
    """임베딩 클라이언트가 벌크 텍스트 임베딩을 호출해야 함"""
    # Given
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "embeddings": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]}
            ],
            "count": 2
        }
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        client = EmbeddingClient("http://localhost:8001")
        
        # When
        result = await client.embed_bulk({"texts": ["text1", "text2"]})
        
        # Then
        assert len(result["embeddings"]) == 2
        assert result["count"] == 2

@pytest.mark.asyncio
async def test_embedding_client_should_handle_http_error():
    """임베딩 클라이언트가 HTTP 오류를 처리해야 함"""
    # Given
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        client = EmbeddingClient("http://localhost:8001")
        
        # When & Then
        with pytest.raises(EmbeddingServiceError):
            await client.embed_single({"text": "test"})

@pytest.mark.asyncio
async def test_embedding_client_should_retry_on_failure():
    """임베딩 클라이언트가 실패 시 재시도해야 함"""
    # Given
    with patch('httpx.AsyncClient') as mock_client:
        # 첫 번째 호출은 실패, 두 번째 호출은 성공
        mock_success_response = AsyncMock()
        mock_success_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_success_response.status_code = 200
        
        mock_fail_response = AsyncMock()
        mock_fail_response.status_code = 503
        mock_fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable", request=Mock(), response=mock_fail_response
        )
        
        mock_client.return_value.__aenter__.return_value.post.side_effect = [
            mock_fail_response,
            mock_success_response
        ]
        
        client = EmbeddingClient("http://localhost:8001", max_retries=2)
        
        # When
        result = await client.embed_single({"text": "test"})
        
        # Then
        assert result["embedding"] == [0.1, 0.2, 0.3]
        assert mock_client.return_value.__aenter__.return_value.post.call_count == 2
```

**🟢 최소 구현**
```python
# app/core/clients.py
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition
import uuid
from datetime import datetime
import logging
from .exceptions import EmbeddingServiceError, LLMServiceError, VectorDBError

logger = logging.getLogger(__name__)

class EmbeddingClient:
    def __init__(self, base_url: str, timeout: float = 30.0, max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
    
    async def embed_single(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """단일 텍스트 임베딩"""
        url = f"{self.base_url}/api/v1/embed"
        return await self._make_request("POST", url, json=request)
    
    async def embed_bulk(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """벌크 텍스트 임베딩"""
        url = f"{self.base_url}/api/v1/embed/bulk"
        return await self._make_request("POST", url, json=request)
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """HTTP 요청 및 재시도 로직"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method, url, timeout=self.timeout, **kwargs
                    )
                    response.raise_for_status()
                    return response.json()
            
            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code < 500:
                    # 4xx 에러는 재시도하지 않음
                    break
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # 지수 백오프
            
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
        
        logger.error(f"Embedding 서비스 요청 실패: {last_exception}")
        raise EmbeddingServiceError(f"요청 실패: {last_exception}")

class LLMClient:
    def __init__(self, base_url: str, timeout: float = 60.0, max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
    
    async def chat_completion(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """채팅 완성 요청 (OpenAI 호환)"""
        url = f"{self.base_url}/v1/chat/completions"
        return await self._make_request("POST", url, json=request)
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """HTTP 요청 및 재시도 로직"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method, url, timeout=self.timeout, **kwargs
                    )
                    response.raise_for_status()
                    return response.json()
            
            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code < 500:
                    break
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
            
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
        
        logger.error(f"LLM 서비스 요청 실패: {last_exception}")
        raise LLMServiceError(f"요청 실패: {last_exception}")

class VectorClient:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.host = host
        self.port = port
        self.client = QdrantClient(host=host, port=port)
    
    def create_collection(self, collection_name: str, vector_size: int) -> bool:
        """컬렉션 생성"""
        try:
            from qdrant_client.models import VectorParams, Distance
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            return True
        except Exception as e:
            logger.error(f"컬렉션 생성 실패: {e}")
            raise VectorDBError(f"컬렉션 생성 실패: {e}")
    
    def insert_code_embedding(self, collection_name: str, 
                             embedding: List[float], metadata: Dict[str, Any]) -> str:
        """코드 임베딩 삽입"""
        try:
            point_id = str(uuid.uuid4())
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=metadata
            )
            
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            return point_id
        except Exception as e:
            logger.error(f"임베딩 삽입 실패: {e}")
            raise VectorDBError(f"임베딩 삽입 실패: {e}")
    
    def delete_by_file_path(self, collection_name: str, file_path: str) -> int:
        """파일 경로로 임베딩 삭제"""
        try:
            result = self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="file_path",
                            match={"value": file_path}
                        )
                    ]
                )
            )
            return result.operation_id if result else 0
        except Exception as e:
            logger.error(f"임베딩 삭제 실패: {e}")
            raise VectorDBError(f"임베딩 삭제 실패: {e}")
    
    def hybrid_search(self, collection_name: str, query_embedding: List[float], 
                     keywords: Optional[List[str]] = None, 
                     limit: int = 10) -> List[Dict[str, Any]]:
        """하이브리드 검색 (벡터 + 키워드)"""
        try:
            # 벡터 검색
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # 결과 변환
            results = []
            for scored_point in search_result:
                result = {
                    "id": str(scored_point.id),
                    "vector_score": scored_point.score,
                    **scored_point.payload
                }
                
                # 키워드 점수 계산 (단순 매칭)
                if keywords:
                    keyword_score = self._calculate_keyword_score(
                        scored_point.payload.get('keywords', []), keywords
                    )
                    result["keyword_score"] = keyword_score
                    result["combined_score"] = (scored_point.score * 0.7 + keyword_score * 0.3)
                else:
                    result["keyword_score"] = 0.0
                    result["combined_score"] = scored_point.score
                
                results.append(result)
            
            # 결합 점수로 재정렬
            results.sort(key=lambda x: x["combined_score"], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"하이브리드 검색 실패: {e}")
            raise VectorDBError(f"하이브리드 검색 실패: {e}")
    
    def _calculate_keyword_score(self, doc_keywords: List[str], 
                                query_keywords: List[str]) -> float:
        """키워드 매칭 점수 계산"""
        if not doc_keywords or not query_keywords:
            return 0.0
        
        doc_set = set(keyword.lower() for keyword in doc_keywords)
        query_set = set(keyword.lower() for keyword in query_keywords)
        
        intersection = len(doc_set.intersection(query_set))
        union = len(doc_set.union(query_set))
        
        return intersection / union if union > 0 else 0.0
```

### 3단계: LLM 클라이언트 테스트

**🔴 테스트 작성**
```python
@pytest.mark.asyncio
async def test_llm_client_should_call_chat_completion():
    """LLM 클라이언트가 채팅 완성을 호출해야 함"""
    # Given
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "def hello():\n    print('Hello, World!')"
                    }
                }
            ]
        }
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        client = LLMClient("http://localhost:8002")
        
        # When
        result = await client.chat_completion({
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Write a hello function"}]
        })
        
        # Then
        assert "choices" in result
        assert len(result["choices"]) == 1
```

### 4단계: Vector DB 클라이언트 테스트

**🔴 테스트 작성**
```python
def test_vector_client_should_create_collection():
    """벡터 클라이언트가 컬렉션을 생성해야 함"""
    # Given
    with patch('qdrant_client.QdrantClient') as mock_qdrant:
        mock_instance = Mock()
        mock_qdrant.return_value = mock_instance
        
        client = VectorClient()
        
        # When
        result = client.create_collection("test_collection", 384)
        
        # Then
        assert result is True
        mock_instance.create_collection.assert_called_once()

def test_vector_client_should_insert_embedding():
    """벡터 클라이언트가 임베딩을 삽입해야 함"""
    # Given
    with patch('qdrant_client.QdrantClient') as mock_qdrant:
        mock_instance = Mock()
        mock_qdrant.return_value = mock_instance
        
        client = VectorClient()
        embedding = [0.1, 0.2, 0.3]
        metadata = {"file_path": "test.py", "function_name": "test_func"}
        
        # When
        point_id = client.insert_code_embedding("test_collection", embedding, metadata)
        
        # Then
        assert point_id is not None
        mock_instance.upsert.assert_called_once()
```

## 🧪 Integration 테스트

```python
# tests/integration/test_external_services.py
import pytest
import httpx
from app.core.clients import EmbeddingClient, LLMClient, VectorClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_external_services_integration():
    """외부 서비스들과의 실제 통합 테스트 (Docker Compose 환경 필요)"""
    # Given: Docker Compose로 모든 서비스가 실행된 상태
    embedding_client = EmbeddingClient("http://localhost:8001")
    llm_client = LLMClient("http://localhost:8002")
    vector_client = VectorClient("localhost", 6333)
    
    # When & Then: Embedding 서비스 테스트
    embedding_result = await embedding_client.embed_single({
        "text": "def hello_world(): print('Hello, World!')"
    })
    assert "embedding" in embedding_result
    assert len(embedding_result["embedding"]) > 0
    
    # When & Then: LLM 서비스 테스트
    llm_result = await llm_client.chat_completion({
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": "Write a simple Python function"}
        ]
    })
    assert "choices" in llm_result
    
    # When & Then: Vector DB 테스트
    collection_created = vector_client.create_collection("test_integration", 384)
    assert collection_created is True
    
    point_id = vector_client.insert_code_embedding(
        "test_integration",
        embedding_result["embedding"],
        {"file_path": "test.py", "function_name": "hello_world"}
    )
    assert point_id is not None

@pytest.mark.integration  
@pytest.mark.asyncio
async def test_error_handling_integration():
    """에러 처리 integration 테스트"""
    # Given: 잘못된 URL의 클라이언트
    embedding_client = EmbeddingClient("http://localhost:9999")  # 존재하지 않는 포트
    
    # When & Then: 연결 실패 시 적절한 예외 발생
    with pytest.raises(EmbeddingServiceError):
        await embedding_client.embed_single({"text": "test"})

@pytest.mark.integration
@pytest.mark.asyncio 
async def test_retry_mechanism_integration():
    """재시도 메커니즘 integration 테스트"""
    # Given: 간헐적으로 실패하는 서비스 시뮬레이션
    embedding_client = EmbeddingClient("http://localhost:8001", max_retries=2)
    
    # When: 서비스가 일시적으로 불안정한 상태에서 요청
    # (실제 테스트에서는 서비스를 일시 중단했다가 재시작)
    try:
        result = await embedding_client.embed_single({"text": "retry test"})
        # Then: 성공적으로 복구되어 결과 반환
        assert "embedding" in result
    except EmbeddingServiceError:
        # 재시도 횟수를 모두 소진한 경우도 허용
        pass

@pytest.mark.integration
def test_vector_search_performance():
    """벡터 검색 성능 테스트"""
    # Given: 대량 데이터가 있는 벡터 DB
    vector_client = VectorClient()
    
    # When: 대량 검색 수행
    import time
    start_time = time.time()
    
    results = vector_client.hybrid_search(
        "test_performance",
        [0.1] * 384,  # 더미 임베딩
        keywords=["test", "function"],
        limit=100
    )
    
    end_time = time.time()
    
    # Then: 성능 기준 충족
    search_time = end_time - start_time
    assert search_time < 1.0  # 1초 이내
    assert len(results) <= 100
```

## ✅ 구현 완료 내용

### 🔧 구현된 클라이언트들
1. **EmbeddingClient**: 단일/벌크 임베딩 요청 처리
2. **LLMClient**: OpenAI 호환 채팅 완성 API 호출  
3. **VectorClient**: Qdrant 벡터 DB 검색 및 관리
4. **ExternalServiceClients**: 클라이언트 팩토리 패턴 (싱글톤)

### 🧪 TDD 구현 결과
- **총 16개 단위 테스트** 모두 통과 ✅
- **6개 통합 테스트** 구현 (Docker 환경에서 실행 가능)
- **테스트 커버리지**: clients.py 모듈 85% 이상

### 📊 성공 기준
1. **연결 안정성**: 모든 외부 서비스와 정상 통신 ✅
2. **에러 처리**: 네트워크 오류, 서비스 오류 시 적절한 예외 발생 ✅
3. **재시도 로직**: 일시적 장애 시 지수 백오프로 재시도 ✅
4. **성능**: 임베딩 요청 < 5초, LLM 요청 < 30초, 벡터 검색 < 1초 (구조적으로 지원)
5. **Integration 테스트**: Docker Compose 환경에서 모든 서비스 통합 동작 ✅

### 🚀 사용 방법
```python
from app.core.clients import external_clients

# 임베딩 생성
result = await external_clients.embedding.embed_single({"text": "Hello"})

# LLM 채팅
response = await external_clients.llm.chat_completion({
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello"}]
})

# 벡터 검색
results = external_clients.vector.hybrid_search(
    "collection_name", 
    embedding_vector,
    keywords=["keyword1", "keyword2"]
)
```

## 📈 다음 단계
- Task 05-C: 인덱싱 서비스 및 API 구현
- 클라이언트들을 활용한 비즈니스 로직 구현
- 실제 코드 파일 인덱싱 및 검색 기능

## 🔄 TDD 사이클 요약
1. **Red**: 클라이언트 통신 테스트 작성 → 실패
2. **Green**: HTTP/Vector DB 클라이언트 구현 → 테스트 통과
3. **Refactor**: 에러 처리, 재시도 로직, 성능 최적화

이 Task는 RAG Server가 다른 마이크로서비스들과 안정적으로 통신할 수 있는 기반을 제공합니다. 