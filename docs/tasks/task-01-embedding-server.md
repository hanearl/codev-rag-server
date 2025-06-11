# Task 01: Embedding Server 구현

## 🎯 목표
HuggingFace Transformers를 사용하여 텍스트 임베딩을 생성하는 마이크로서비스를 TDD 방식으로 구현합니다.

## 📋 MVP 범위
- HuggingFace 임베딩 모델 로딩 및 서빙
- 단일 텍스트 임베딩 API
- 벌크 텍스트 임베딩 API
- FastAPI 기반 RESTful API
- Docker 컨테이너화

## 🏗️ 기술 스택
- **웹 프레임워크**: FastAPI
- **임베딩 모델**: sentence-transformers/all-MiniLM-L6-v2
- **라이브러리**: transformers, sentence-transformers, torch
- **컨테이너**: Docker
- **테스트**: pytest, httpx

## 📁 프로젝트 구조

```
embedding-server/
├── app/
│   ├── features/
│   │   └── embedding/
│   │       ├── __init__.py
│   │       ├── router.py        ← API 엔드포인트
│   │       ├── service.py       ← 임베딩 비즈니스 로직
│   │       ├── schema.py        ← 요청/응답 스키마
│   │       └── model.py         ← 임베딩 모델 관리
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           ← 설정 관리
│   │   └── dependencies.py     ← 의존성 주입
│   ├── __init__.py
│   └── main.py                 ← FastAPI 애플리케이션
├── tests/
│   ├── unit/
│   │   └── features/
│   │       └── embedding/
│   │           ├── test_router.py
│   │           ├── test_service.py
│   │           ├── test_schema.py
│   │           └── test_model.py
│   ├── integration/
│   │   └── test_embedding_api.py
│   └── conftest.py
├── Dockerfile
├── requirements.txt
└── .dockerignore
```

## 🧪 TDD 구현 순서

### 1단계: 임베딩 모델 클래스 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/embedding/test_model.py
import pytest
import torch
from app.features.embedding.model import EmbeddingModel

def test_embedding_model_should_load_model():
    """임베딩 모델이 정상적으로 로드되어야 함"""
    # Given
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    
    # When
    embedding_model = EmbeddingModel(model_name)
    
    # Then
    assert embedding_model.model is not None
    assert embedding_model.tokenizer is not None

def test_encode_should_return_embedding_vector():
    """텍스트 인코딩 시 임베딩 벡터를 반환해야 함"""
    # Given
    model = EmbeddingModel("sentence-transformers/all-MiniLM-L6-v2")
    text = "테스트 텍스트입니다"
    
    # When
    embedding = model.encode(text)
    
    # Then
    assert isinstance(embedding, list)
    assert len(embedding) == 384  # all-MiniLM-L6-v2 차원
    assert all(isinstance(x, float) for x in embedding)
```

**🟢 최소 구현**
```python
# app/features/embedding/model.py
from sentence_transformers import SentenceTransformer
from typing import List, Union

class EmbeddingModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.tokenizer = self.model.tokenizer
    
    def encode(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """텍스트를 임베딩 벡터로 변환"""
        embeddings = self.model.encode(text)
        
        if isinstance(text, str):
            return embeddings.tolist()
        else:
            return [emb.tolist() for emb in embeddings]
```

### 2단계: 임베딩 서비스 클래스 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/embedding/test_service.py
import pytest
from unittest.mock import Mock, patch
from app.features.embedding.service import EmbeddingService
from app.features.embedding.schema import EmbeddingRequest, BulkEmbeddingRequest

@pytest.fixture
def mock_embedding_model():
    mock_model = Mock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3]
    return mock_model

def test_embed_single_text_should_return_embedding(mock_embedding_model):
    """단일 텍스트 임베딩 시 임베딩 벡터를 반환해야 함"""
    # Given
    service = EmbeddingService(mock_embedding_model)
    request = EmbeddingRequest(text="테스트 텍스트")
    
    # When
    result = service.embed_single(request)
    
    # Then
    assert result.embedding == [0.1, 0.2, 0.3]
    assert result.text == "테스트 텍스트"
    mock_embedding_model.encode.assert_called_once_with("테스트 텍스트")

def test_embed_bulk_texts_should_return_multiple_embeddings(mock_embedding_model):
    """벌크 텍스트 임베딩 시 여러 임베딩 벡터를 반환해야 함"""
    # Given
    service = EmbeddingService(mock_embedding_model)
    mock_embedding_model.encode.return_value = [[0.1, 0.2], [0.3, 0.4]]
    request = BulkEmbeddingRequest(texts=["텍스트1", "텍스트2"])
    
    # When
    result = service.embed_bulk(request)
    
    # Then
    assert len(result.embeddings) == 2
    assert result.embeddings[0].embedding == [0.1, 0.2]
    assert result.embeddings[1].embedding == [0.3, 0.4]
```

**🟢 최소 구현**
```python
# app/features/embedding/service.py
from typing import List
from .model import EmbeddingModel
from .schema import (
    EmbeddingRequest, EmbeddingResponse,
    BulkEmbeddingRequest, BulkEmbeddingResponse
)

class EmbeddingService:
    def __init__(self, embedding_model: EmbeddingModel):
        self.embedding_model = embedding_model
    
    def embed_single(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """단일 텍스트 임베딩"""
        embedding = self.embedding_model.encode(request.text)
        return EmbeddingResponse(
            text=request.text,
            embedding=embedding,
            model=self.embedding_model.model_name
        )
    
    def embed_bulk(self, request: BulkEmbeddingRequest) -> BulkEmbeddingResponse:
        """벌크 텍스트 임베딩"""
        embeddings = self.embedding_model.encode(request.texts)
        
        embedding_responses = []
        for text, embedding in zip(request.texts, embeddings):
            embedding_responses.append(EmbeddingResponse(
                text=text,
                embedding=embedding,
                model=self.embedding_model.model_name
            ))
        
        return BulkEmbeddingResponse(
            embeddings=embedding_responses,
            count=len(embedding_responses)
        )
```

### 3단계: API 스키마 정의 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/embedding/test_schema.py
import pytest
from pydantic import ValidationError
from app.features.embedding.schema import (
    EmbeddingRequest, EmbeddingResponse,
    BulkEmbeddingRequest, BulkEmbeddingResponse
)

def test_embedding_request_should_validate_text():
    """임베딩 요청 스키마가 텍스트를 정상 검증해야 함"""
    # Given & When
    request = EmbeddingRequest(text="테스트 텍스트")
    
    # Then
    assert request.text == "테스트 텍스트"

def test_embedding_request_should_reject_empty_text():
    """임베딩 요청 스키마가 빈 텍스트를 거부해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        EmbeddingRequest(text="")

def test_bulk_embedding_request_should_validate_multiple_texts():
    """벌크 임베딩 요청 스키마가 여러 텍스트를 정상 검증해야 함"""
    # Given & When
    request = BulkEmbeddingRequest(texts=["텍스트1", "텍스트2"])
    
    # Then
    assert len(request.texts) == 2
    assert request.texts[0] == "텍스트1"

def test_bulk_embedding_request_should_reject_empty_list():
    """벌크 임베딩 요청 스키마가 빈 리스트를 거부해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        BulkEmbeddingRequest(texts=[])
```

**🟢 최소 구현**
```python
# app/features/embedding/schema.py
from pydantic import BaseModel, Field, validator
from typing import List

class EmbeddingRequest(BaseModel):
    text: str = Field(..., min_length=1, description="임베딩할 텍스트")

class EmbeddingResponse(BaseModel):
    text: str
    embedding: List[float]
    model: str

class BulkEmbeddingRequest(BaseModel):
    texts: List[str] = Field(..., min_items=1, description="임베딩할 텍스트 리스트")
    
    @validator('texts')
    def validate_texts(cls, v):
        if not v or len(v) == 0:
            raise ValueError('텍스트 리스트는 비어있을 수 없습니다')
        for text in v:
            if not text.strip():
                raise ValueError('빈 텍스트는 허용되지 않습니다')
        return v

class BulkEmbeddingResponse(BaseModel):
    embeddings: List[EmbeddingResponse]
    count: int
```

### 4단계: API 라우터 구현 (TDD)

**🔴 테스트 작성**
```python
# tests/integration/test_embedding_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_embed_single_endpoint_should_return_embedding():
    """단일 임베딩 엔드포인트가 임베딩을 반환해야 함"""
    # Given
    request_data = {"text": "테스트 텍스트"}
    
    # When
    response = client.post("/api/v1/embed", json=request_data)
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "테스트 텍스트"
    assert "embedding" in data
    assert isinstance(data["embedding"], list)
    assert len(data["embedding"]) == 384

def test_embed_bulk_endpoint_should_return_multiple_embeddings():
    """벌크 임베딩 엔드포인트가 여러 임베딩을 반환해야 함"""
    # Given
    request_data = {"texts": ["텍스트1", "텍스트2"]}
    
    # When
    response = client.post("/api/v1/embed/bulk", json=request_data)
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert len(data["embeddings"]) == 2
```

**🟢 최소 구현**
```python
# app/features/embedding/router.py
from fastapi import APIRouter, Depends
from .service import EmbeddingService
from .schema import (
    EmbeddingRequest, EmbeddingResponse,
    BulkEmbeddingRequest, BulkEmbeddingResponse
)
from app.core.dependencies import get_embedding_service

router = APIRouter()

@router.post("/embed", response_model=EmbeddingResponse)
async def embed_single(
    request: EmbeddingRequest,
    service: EmbeddingService = Depends(get_embedding_service)
) -> EmbeddingResponse:
    """단일 텍스트 임베딩"""
    return service.embed_single(request)

@router.post("/embed/bulk", response_model=BulkEmbeddingResponse)
async def embed_bulk(
    request: BulkEmbeddingRequest,
    service: EmbeddingService = Depends(get_embedding_service)
) -> BulkEmbeddingResponse:
    """벌크 텍스트 임베딩"""
    return service.embed_bulk(request)

@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "service": "embedding-server"}
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
EXPOSE 8001

# 애플리케이션 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
```

### requirements.txt
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sentence-transformers==2.2.2
torch==2.0.1
transformers==4.35.2
pydantic==2.5.0
httpx==0.25.2
pytest==7.4.3
pytest-asyncio==0.21.1
```

## ✅ 성공 기준

### 기능적 요구사항
- [ ] 단일 텍스트 임베딩 API가 정상 작동
- [ ] 벌크 텍스트 임베딩 API가 정상 작동
- [ ] 384차원 임베딩 벡터 반환
- [ ] 입력 검증 및 에러 처리
- [ ] API 문서 자동 생성 (FastAPI)

### 비기능적 요구사항
- [ ] 단위 테스트 커버리지 90% 이상
- [ ] 통합 테스트 통과
- [ ] Docker 컨테이너 정상 실행
- [ ] API 응답 시간 < 2초 (일반 텍스트)

### TDD 품질
- [ ] 모든 기능이 테스트 우선으로 개발됨
- [ ] Red-Green-Refactor 사이클 준수
- [ ] 테스트 코드의 가독성과 유지보수성

## 🚀 실행 방법

### 로컬 개발
```bash
# 의존성 설치
pip install -r requirements.txt

# 테스트 실행
pytest tests/ -v --cov=app

# 서버 실행
uvicorn app.main:app --reload --port 8001
```

### Docker 실행
```bash
# 이미지 빌드
docker build -t embedding-server .

# 컨테이너 실행
docker run -p 8001:8001 -v $(pwd):/app embedding-server
```

## 📚 API 문서
서버 실행 후 http://localhost:8001/docs 에서 Swagger UI 확인

## 🧪 Integration 테스트 단계

### 임베딩 서비스 통합 테스트

**목표**: 임베딩 서비스의 외부 연동 및 실제 환경 동작 검증

```python
# tests/integration/test_embedding_integration.py
import pytest
import httpx
import asyncio
from sentence_transformers import SentenceTransformer

@pytest.mark.asyncio
class TestEmbeddingIntegration:
    """임베딩 서비스 통합 테스트"""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Docker Compose 환경에서 서비스 시작 확인"""
        async with httpx.AsyncClient() as client:
            # 서비스 준비 대기 (최대 60초)
            for _ in range(60):
                try:
                    response = await client.get("http://localhost:8001/health")
                    if response.status_code == 200:
                        break
                    await asyncio.sleep(1)
                except:
                    await asyncio.sleep(1)
            else:
                pytest.fail("임베딩 서비스가 시작되지 않았습니다")
    
    async def test_model_loading_performance(self):
        """모델 로딩 성능 테스트"""
        start_time = time.time()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/api/v1/embed",
                json={"text": "테스트"},
                timeout=30.0
            )
        load_time = time.time() - start_time
        
        assert response.status_code == 200
        assert load_time < 10.0  # 첫 요청은 10초 이내
        print(f"✅ 첫 모델 로딩 시간: {load_time:.2f}초")
    
    async def test_concurrent_embedding_requests(self):
        """동시 임베딩 요청 처리 테스트"""
        async with httpx.AsyncClient() as client:
            tasks = []
            for i in range(10):
                task = client.post(
                    "http://localhost:8001/api/v1/embed",
                    json={"text": f"테스트 텍스트 {i}"},
                    timeout=30.0
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            
            success_count = sum(1 for r in responses if r.status_code == 200)
            assert success_count >= 8, f"동시 요청 실패: {success_count}/10"
            print(f"✅ 동시 요청 성공: {success_count}/10")
    
    async def test_bulk_embedding_performance(self):
        """대용량 배치 임베딩 성능 테스트"""
        texts = [f"테스트 문서 {i}" for i in range(100)]
        
        start_time = time.time()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8001/api/v1/embed/batch",
                json={"texts": texts},
                timeout=120.0
            )
        process_time = time.time() - start_time
        
        assert response.status_code == 200
        result = response.json()
        assert len(result["embeddings"]) == 100
        assert process_time < 60.0  # 100개 처리 1분 이내
        print(f"✅ 배치 처리 성능: {len(texts)}개 문서 {process_time:.2f}초")
    
    async def test_memory_usage_stability(self):
        """메모리 사용량 안정성 테스트"""
        import psutil
        import docker
        
        client = docker.from_env()
        container = client.containers.get("codev-embedding-server-1")
        
        # 초기 메모리 사용량 측정
        stats = container.stats(stream=False)
        initial_memory = stats['memory_stats']['usage']
        
        # 연속 100회 요청
        async with httpx.AsyncClient() as http_client:
            for i in range(100):
                await http_client.post(
                    "http://localhost:8001/api/v1/embed",
                    json={"text": f"메모리 테스트 {i}"},
                    timeout=10.0
                )
        
        # 최종 메모리 사용량 측정
        stats = container.stats(stream=False)
        final_memory = stats['memory_stats']['usage']
        
        memory_increase = (final_memory - initial_memory) / initial_memory
        assert memory_increase < 0.1  # 메모리 증가율 10% 미만
        print(f"✅ 메모리 안정성: 증가율 {memory_increase*100:.1f}%")
```

**실행 방법**:
```bash
# Docker Compose 환경 시작
docker-compose up -d embedding-server

# Integration 테스트 실행
pytest tests/integration/test_embedding_integration.py -v

# 성공 기준
# - 모든 테스트 통과
# - 첫 모델 로딩 < 10초
# - 동시 요청 성공률 > 80%
# - 배치 처리 성능 적절
# - 메모리 누수 없음
```

## 🔄 다음 단계
Task 02: LLM Server 구현 