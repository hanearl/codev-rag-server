# Task 05-C: 인덱싱 서비스 및 API 구현

## 🎯 목표
코드 파일을 인덱싱하여 벡터 DB에 저장하는 서비스와 API를 TDD 방식으로 구현합니다.

## 📋 MVP 범위
- 파일 인덱싱 비즈니스 로직
- 인덱싱 REST API 엔드포인트
- 배치 인덱싱 기능
- 중복 제거 및 업데이트 처리

## 🏗️ 기술 스택
- **웹 프레임워크**: FastAPI
- **의존성 주입**: FastAPI Depends
- **비동기 처리**: asyncio
- **테스트**: pytest, httpx

## 📁 프로젝트 구조

```
rag-server/
├── app/
│   ├── features/
│   │   └── indexing/
│   │       ├── __init__.py
│   │       ├── router.py        ← 인덱싱 API 엔드포인트
│   │       ├── service.py       ← 인덱싱 비즈니스 로직
│   │       └── schema.py        ← 요청/응답 스키마
│   ├── core/
│   │   ├── dependencies.py      ← 의존성 주입
│   │   └── config.py           ← 설정 관리
│   └── main.py                 ← FastAPI 앱
├── tests/
│   ├── unit/
│   │   └── features/
│   │       └── indexing/
│   │           ├── test_service.py
│   │           └── test_router.py
│   └── integration/
│       └── test_indexing_api.py
├── requirements.txt
└── pytest.ini
```

## 🧪 TDD 구현 순서

### 1단계: 스키마 정의

```python
# app/features/indexing/schema.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class IndexingRequest(BaseModel):
    file_path: str = Field(..., description="인덱싱할 파일 경로")
    force_update: bool = Field(default=False, description="강제 업데이트 여부")

class BatchIndexingRequest(BaseModel):
    file_paths: List[str] = Field(..., description="인덱싱할 파일 경로 목록")
    force_update: bool = Field(default=False, description="강제 업데이트 여부")

class IndexingResponse(BaseModel):
    file_path: str
    chunks_count: int
    message: str
    indexed_at: datetime

class BatchIndexingResponse(BaseModel):
    total_files: int
    successful_files: int
    failed_files: int
    total_chunks: int
    results: List[IndexingResponse]
    errors: List[str]
```

### 2단계: 인덱싱 서비스 테스트 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/indexing/test_service.py
import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from app.features.indexing.service import IndexingService
from app.features.indexing.schema import IndexingRequest, BatchIndexingRequest
from app.features.indexing.parser import CodeChunk

@pytest.fixture
def mock_embedding_client():
    client = Mock()
    client.embed_bulk = AsyncMock()
    return client

@pytest.fixture
def mock_vector_client():
    client = Mock()
    client.insert_code_embedding = Mock()
    client.delete_by_file_path = Mock()
    return client

@pytest.fixture
def mock_code_parser():
    parser = Mock()
    parser.parse_python_code = Mock()
    return parser

@pytest.mark.asyncio
async def test_indexing_service_should_process_file(
    mock_embedding_client, mock_vector_client, mock_code_parser
):
    """인덱싱 서비스가 파일을 처리해야 함"""
    # Given
    service = IndexingService(mock_embedding_client, mock_vector_client, mock_code_parser)
    
    mock_chunks = [
        CodeChunk(
            function_name="test_func",
            code_content="def test_func(): pass",
            code_type="function",
            file_path="test.py",
            line_start=1,
            line_end=1,
            keywords=["test", "func"]
        )
    ]
    mock_code_parser.parse_python_code.return_value = mock_chunks
    
    mock_embedding_client.embed_bulk.return_value = {
        "embeddings": [{"embedding": [0.1, 0.2, 0.3]}],
        "count": 1
    }
    
    mock_vector_client.insert_code_embedding.return_value = "test-id"
    
    request = IndexingRequest(file_path="test.py")
    
    # When
    with patch('builtins.open', mock_open(read_data="def test_func(): pass")):
        with patch('os.path.exists', return_value=True):
            result = await service.index_file(request)
    
    # Then
    assert result.chunks_count == 1
    assert result.file_path == "test.py"
    assert "성공" in result.message
    mock_embedding_client.embed_bulk.assert_called_once()
    mock_vector_client.insert_code_embedding.assert_called_once()

@pytest.mark.asyncio
async def test_indexing_service_should_handle_file_not_found(
    mock_embedding_client, mock_vector_client, mock_code_parser
):
    """인덱싱 서비스가 파일을 찾을 수 없을 때 예외를 발생시켜야 함"""
    # Given
    service = IndexingService(mock_embedding_client, mock_vector_client, mock_code_parser)
    request = IndexingRequest(file_path="nonexistent.py")
    
    # When & Then
    with patch('os.path.exists', return_value=False):
        with pytest.raises(FileNotFoundError):
            await service.index_file(request)

@pytest.mark.asyncio
async def test_indexing_service_should_handle_empty_file(
    mock_embedding_client, mock_vector_client, mock_code_parser
):
    """인덱싱 서비스가 빈 파일을 처리해야 함"""
    # Given
    service = IndexingService(mock_embedding_client, mock_vector_client, mock_code_parser)
    mock_code_parser.parse_python_code.return_value = []
    
    request = IndexingRequest(file_path="empty.py")
    
    # When
    with patch('builtins.open', mock_open(read_data="")):
        with patch('os.path.exists', return_value=True):
            result = await service.index_file(request)
    
    # Then
    assert result.chunks_count == 0
    assert "처리할 코드 청크가 없습니다" in result.message

@pytest.mark.asyncio
async def test_indexing_service_should_force_update_existing_file(
    mock_embedding_client, mock_vector_client, mock_code_parser
):
    """인덱싱 서비스가 기존 파일을 강제 업데이트해야 함"""
    # Given
    service = IndexingService(mock_embedding_client, mock_vector_client, mock_code_parser)
    
    mock_chunks = [
        CodeChunk(
            function_name="updated_func",
            code_content="def updated_func(): pass",
            code_type="function",
            file_path="test.py",
            line_start=1,
            line_end=1,
            keywords=["updated", "func"]
        )
    ]
    mock_code_parser.parse_python_code.return_value = mock_chunks
    
    mock_embedding_client.embed_bulk.return_value = {
        "embeddings": [{"embedding": [0.4, 0.5, 0.6]}],
        "count": 1
    }
    
    mock_vector_client.delete_by_file_path.return_value = 1
    mock_vector_client.insert_code_embedding.return_value = "updated-id"
    
    request = IndexingRequest(file_path="test.py", force_update=True)
    
    # When
    with patch('builtins.open', mock_open(read_data="def updated_func(): pass")):
        with patch('os.path.exists', return_value=True):
            result = await service.index_file(request)
    
    # Then
    assert result.chunks_count == 1
    assert "업데이트" in result.message
    mock_vector_client.delete_by_file_path.assert_called_once_with("code_chunks", "test.py")
```

**🟢 최소 구현**
```python
# app/features/indexing/service.py
import os
from typing import List, Dict, Any
from datetime import datetime
import logging
from .schema import IndexingRequest, IndexingResponse, BatchIndexingRequest, BatchIndexingResponse
from .parser import CodeParser, CodeChunk
from app.core.clients import EmbeddingClient, VectorClient

logger = logging.getLogger(__name__)

class IndexingService:
    def __init__(self, embedding_client: EmbeddingClient, 
                 vector_client: VectorClient, code_parser: CodeParser):
        self.embedding_client = embedding_client
        self.vector_client = vector_client
        self.code_parser = code_parser
        self.collection_name = "code_chunks"
    
    async def index_file(self, request: IndexingRequest) -> IndexingResponse:
        """단일 파일 인덱싱"""
        if not os.path.exists(request.file_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {request.file_path}")
        
        try:
            # 파일 읽기
            with open(request.file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            # 코드 파싱
            chunks = self.code_parser.parse_python_code(code_content, request.file_path)
            
            if not chunks:
                return IndexingResponse(
                    file_path=request.file_path,
                    chunks_count=0,
                    message="처리할 코드 청크가 없습니다.",
                    indexed_at=datetime.now()
                )
            
            # 강제 업데이트 시 기존 데이터 삭제
            if request.force_update:
                self.vector_client.delete_by_file_path(self.collection_name, request.file_path)
            
            # 임베딩 생성
            texts = [chunk.code_content for chunk in chunks]
            embedding_response = await self.embedding_client.embed_bulk({"texts": texts})
            embeddings = [emb["embedding"] for emb in embedding_response["embeddings"]]
            
            # 벡터 DB에 저장
            inserted_count = 0
            for chunk, embedding in zip(chunks, embeddings):
                metadata = {
                    "file_path": chunk.file_path,
                    "function_name": chunk.function_name,
                    "code_content": chunk.code_content,
                    "code_type": chunk.code_type,
                    "language": "python",
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                    "keywords": chunk.keywords,
                    "indexed_at": datetime.now().isoformat()
                }
                
                point_id = self.vector_client.insert_code_embedding(
                    self.collection_name, embedding, metadata
                )
                
                if point_id:
                    inserted_count += 1
            
            message = f"인덱싱 성공: {inserted_count}개 청크 처리"
            if request.force_update:
                message += " (기존 데이터 업데이트)"
            
            return IndexingResponse(
                file_path=request.file_path,
                chunks_count=inserted_count,
                message=message,
                indexed_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"파일 인덱싱 실패 ({request.file_path}): {e}")
            raise
    
    async def index_batch(self, request: BatchIndexingRequest) -> BatchIndexingResponse:
        """배치 파일 인덱싱"""
        results = []
        errors = []
        total_chunks = 0
        successful_files = 0
        
        for file_path in request.file_paths:
            try:
                file_request = IndexingRequest(
                    file_path=file_path, 
                    force_update=request.force_update
                )
                result = await self.index_file(file_request)
                results.append(result)
                total_chunks += result.chunks_count
                successful_files += 1
                
            except Exception as e:
                error_msg = f"{file_path}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"배치 인덱싱 오류: {error_msg}")
        
        return BatchIndexingResponse(
            total_files=len(request.file_paths),
            successful_files=successful_files,
            failed_files=len(request.file_paths) - successful_files,
            total_chunks=total_chunks,
            results=results,
            errors=errors
        )
```

### 3단계: API 라우터 테스트 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/indexing/test_router.py
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.features.indexing.service import IndexingService
from app.features.indexing.schema import IndexingResponse
from datetime import datetime

@pytest.fixture
def mock_indexing_service():
    service = Mock(spec=IndexingService)
    return service

def test_index_file_endpoint_should_return_success(mock_indexing_service):
    """파일 인덱싱 엔드포인트가 성공 응답을 반환해야 함"""
    # Given
    mock_response = IndexingResponse(
        file_path="test.py",
        chunks_count=2,
        message="인덱싱 성공: 2개 청크 처리",
        indexed_at=datetime.now()
    )
    mock_indexing_service.index_file = AsyncMock(return_value=mock_response)
    
    # Mock 의존성 주입
    app.dependency_overrides[IndexingService] = lambda: mock_indexing_service
    
    client = TestClient(app)
    
    # When
    response = client.post("/api/v1/indexing/file", json={
        "file_path": "test.py",
        "force_update": False
    })
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["chunks_count"] == 2
    assert data["file_path"] == "test.py"
    assert "성공" in data["message"]

def test_index_file_endpoint_should_handle_file_not_found(mock_indexing_service):
    """파일 인덱싱 엔드포인트가 파일 없음 오류를 처리해야 함"""
    # Given
    mock_indexing_service.index_file = AsyncMock(
        side_effect=FileNotFoundError("파일을 찾을 수 없습니다")
    )
    
    app.dependency_overrides[IndexingService] = lambda: mock_indexing_service
    client = TestClient(app)
    
    # When
    response = client.post("/api/v1/indexing/file", json={
        "file_path": "nonexistent.py"
    })
    
    # Then
    assert response.status_code == 404
    data = response.json()
    assert "파일을 찾을 수 없습니다" in data["detail"]

def test_batch_index_endpoint_should_return_batch_results(mock_indexing_service):
    """배치 인덱싱 엔드포인트가 배치 결과를 반환해야 함"""
    # Given
    from app.features.indexing.schema import BatchIndexingResponse
    mock_response = BatchIndexingResponse(
        total_files=2,
        successful_files=2,
        failed_files=0,
        total_chunks=4,
        results=[],
        errors=[]
    )
    mock_indexing_service.index_batch = AsyncMock(return_value=mock_response)
    
    app.dependency_overrides[IndexingService] = lambda: mock_indexing_service
    client = TestClient(app)
    
    # When
    response = client.post("/api/v1/indexing/batch", json={
        "file_paths": ["test1.py", "test2.py"],
        "force_update": False
    })
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["total_files"] == 2
    assert data["successful_files"] == 2
    assert data["total_chunks"] == 4
```

**🟢 최소 구현**
```python
# app/features/indexing/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from .service import IndexingService
from .schema import IndexingRequest, IndexingResponse, BatchIndexingRequest, BatchIndexingResponse
from app.core.dependencies import get_indexing_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/indexing", tags=["indexing"])

@router.post("/file", response_model=IndexingResponse)
async def index_file(
    request: IndexingRequest,
    service: IndexingService = Depends(get_indexing_service)
) -> IndexingResponse:
    """단일 파일 인덱싱"""
    try:
        return await service.index_file(request)
    except FileNotFoundError as e:
        logger.warning(f"파일 없음: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"인덱싱 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인덱싱 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/batch", response_model=BatchIndexingResponse)
async def index_batch(
    request: BatchIndexingRequest,
    service: IndexingService = Depends(get_indexing_service)
) -> BatchIndexingResponse:
    """배치 파일 인덱싱"""
    try:
        return await service.index_batch(request)
    except Exception as e:
        logger.error(f"배치 인덱싱 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"배치 인덱싱 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """인덱싱 서비스 헬스체크"""
    return {"status": "healthy", "service": "indexing"}
```

### 4단계: 의존성 주입 설정

```python
# app/core/dependencies.py
from functools import lru_cache
from .clients import EmbeddingClient, VectorClient
from .config import Settings
from app.features.indexing.parser import CodeParser
from app.features.indexing.service import IndexingService

@lru_cache()
def get_settings() -> Settings:
    return Settings()

@lru_cache()
def get_embedding_client() -> EmbeddingClient:
    settings = get_settings()
    return EmbeddingClient(
        base_url=settings.embedding_server_url,
        timeout=settings.request_timeout,
        max_retries=settings.max_retries
    )

@lru_cache()
def get_vector_client() -> VectorClient:
    settings = get_settings()
    return VectorClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port
    )

@lru_cache()
def get_code_parser() -> CodeParser:
    return CodeParser()

def get_indexing_service() -> IndexingService:
    return IndexingService(
        embedding_client=get_embedding_client(),
        vector_client=get_vector_client(),
        code_parser=get_code_parser()
    )
```

### 5단계: FastAPI 앱 설정

```python
# app/main.py
from fastapi import FastAPI
from app.features.indexing.router import router as indexing_router

app = FastAPI(
    title="RAG Server",
    description="코드 인덱싱 및 검색 서비스",
    version="1.0.0"
)

app.include_router(indexing_router)

@app.get("/")
async def root():
    return {"message": "RAG Server is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

## 🧪 Integration 테스트

```python
# tests/integration/test_indexing_api.py
import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.integration
def test_full_indexing_workflow():
    """전체 인덱싱 워크플로우 integration 테스트"""
    # Given: 임시 Python 파일 생성
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
def calculate_sum(a, b):
    """두 수의 합을 계산하는 함수"""
    return a + b

class Calculator:
    """계산기 클래스"""
    
    def multiply(self, x, y):
        """곱셈 메소드"""
        return x * y
''')
        temp_file_path = f.name
    
    try:
        client = TestClient(app)
        
        # When: 파일 인덱싱 요청
        response = client.post("/api/v1/indexing/file", json={
            "file_path": temp_file_path,
            "force_update": False
        })
        
        # Then: 성공적으로 인덱싱됨
        assert response.status_code == 200
        data = response.json()
        assert data["chunks_count"] > 0
        assert temp_file_path in data["file_path"]
        assert "성공" in data["message"]
        
    finally:
        # Cleanup
        os.unlink(temp_file_path)

@pytest.mark.integration  
def test_batch_indexing_integration():
    """배치 인덱싱 integration 테스트"""
    # Given: 여러 임시 파일 생성
    temp_files = []
    try:
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{i}.py', delete=False) as f:
                f.write(f'''
def function_{i}():
    """Function {i}"""
    return {i}
''')
                temp_files.append(f.name)
        
        client = TestClient(app)
        
        # When: 배치 인덱싱 요청
        response = client.post("/api/v1/indexing/batch", json={
            "file_paths": temp_files,
            "force_update": False
        })
        
        # Then: 성공적으로 배치 인덱싱됨
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 3
        assert data["successful_files"] == 3
        assert data["failed_files"] == 0
        assert data["total_chunks"] >= 3
        
    finally:
        # Cleanup
        for temp_file in temp_files:
            os.unlink(temp_file)

@pytest.mark.integration
def test_indexing_error_handling():
    """인덱싱 에러 처리 integration 테스트"""
    client = TestClient(app)
    
    # When: 존재하지 않는 파일 인덱싱 시도
    response = client.post("/api/v1/indexing/file", json={
        "file_path": "/nonexistent/file.py"
    })
    
    # Then: 404 에러 반환
    assert response.status_code == 404
    data = response.json()
    assert "파일을 찾을 수 없습니다" in data["detail"]

@pytest.mark.integration
def test_force_update_integration():
    """강제 업데이트 integration 테스트"""
    # Given: 임시 파일 생성 및 초기 인덱싱
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('def original_function(): pass')
        temp_file_path = f.name
    
    try:
        client = TestClient(app)
        
        # 초기 인덱싱
        response1 = client.post("/api/v1/indexing/file", json={
            "file_path": temp_file_path,
            "force_update": False
        })
        assert response1.status_code == 200
        
        # 파일 내용 수정
        with open(temp_file_path, 'w') as f:
            f.write('def updated_function(): pass')
        
        # When: 강제 업데이트로 재인덱싱
        response2 = client.post("/api/v1/indexing/file", json={
            "file_path": temp_file_path,
            "force_update": True
        })
        
        # Then: 업데이트 성공
        assert response2.status_code == 200
        data = response2.json()
        assert "업데이트" in data["message"]
        
    finally:
        os.unlink(temp_file_path)
```

## 📊 성공 기준
1. **API 응답성**: 단일 파일 < 10초, 배치 파일 < 1분
2. **정확성**: 코드 청크 추출 및 임베딩 저장 100% 정확
3. **에러 처리**: 파일 없음, 권한 오류 등 적절한 HTTP 상태 코드
4. **멱등성**: 동일 파일 재인덱싱 시 중복 방지
5. **확장성**: 100개 파일 동시 처리 가능

## 📈 다음 단계
- Task 05-D: 검색 및 코드 생성 서비스 구현
- 인덱싱된 데이터를 활용한 검색 기능
- RAG 기반 코드 생성 기능

## 🔄 TDD 사이클 요약
1. **Red**: 인덱싱 서비스 및 API 테스트 작성 → 실패
2. **Green**: 비즈니스 로직 및 FastAPI 라우터 구현 → 테스트 통과
3. **Refactor**: 에러 처리, 성능 최적화, 코드 정리

이 Task는 코드 파일을 벡터 DB에 저장하여 검색 가능한 형태로 만드는 핵심 기능을 제공합니다. 