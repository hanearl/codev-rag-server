import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.features.indexing.service import IndexingService
from app.features.indexing.schema import IndexingResponse, BatchIndexingResponse

@pytest.fixture
def mock_indexing_service():
    service = Mock(spec=IndexingService)
    return service

@pytest.fixture
def client():
    return TestClient(app)

def test_index_file_endpoint_should_return_success(mock_indexing_service, client):
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
    from app.core.dependencies import get_indexing_service
    app.dependency_overrides[get_indexing_service] = lambda: mock_indexing_service
    
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
    
    # Cleanup
    app.dependency_overrides.clear()

def test_index_file_endpoint_should_handle_file_not_found(mock_indexing_service, client):
    """파일 인덱싱 엔드포인트가 파일 없음 오류를 처리해야 함"""
    # Given
    mock_indexing_service.index_file = AsyncMock(
        side_effect=FileNotFoundError("파일을 찾을 수 없습니다")
    )
    
    from app.core.dependencies import get_indexing_service
    app.dependency_overrides[get_indexing_service] = lambda: mock_indexing_service
    
    # When
    response = client.post("/api/v1/indexing/file", json={
        "file_path": "nonexistent.py"
    })
    
    # Then
    assert response.status_code == 404
    data = response.json()
    assert "파일을 찾을 수 없습니다" in data["detail"]
    
    # Cleanup
    app.dependency_overrides.clear()

def test_batch_index_endpoint_should_return_batch_results(mock_indexing_service, client):
    """배치 인덱싱 엔드포인트가 배치 결과를 반환해야 함"""
    # Given
    mock_response = BatchIndexingResponse(
        total_files=2,
        successful_files=2,
        failed_files=0,
        total_chunks=4,
        results=[],
        errors=[]
    )
    mock_indexing_service.index_batch = AsyncMock(return_value=mock_response)
    
    from app.core.dependencies import get_indexing_service
    app.dependency_overrides[get_indexing_service] = lambda: mock_indexing_service
    
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

def test_query_chunks_endpoint_should_return_chunks(mock_indexing_service):
    """청크 조회 엔드포인트가 청크 목록을 반환해야 함"""
    # Given
    from app.features.indexing.schema import ChunkQueryResponse, CodeChunkResponse
    from datetime import datetime
    
    mock_chunks = [
        CodeChunkResponse(
            id="chunk-1",
            file_path="test.py",
            function_name="test_func",
            code_content="def test_func(): pass",
            code_type="function",
            language="python",
            line_start=1,
            line_end=1,
            keywords=["test", "func"],
            indexed_at=datetime.now()
        )
    ]
    
    mock_response = ChunkQueryResponse(
        chunks=mock_chunks,
        total=1,
        page=1,
        size=10,
        total_pages=1
    )
    
    mock_indexing_service.query_chunks = AsyncMock(return_value=mock_response)
    
    from app.core.dependencies import get_indexing_service
    app.dependency_overrides[get_indexing_service] = lambda: mock_indexing_service
    client = TestClient(app)
    
    try:
        # When
        response = client.get("/api/v1/indexing/chunks")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert len(data["chunks"]) == 1
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["chunks"][0]["file_path"] == "test.py"
    finally:
        app.dependency_overrides.clear()

def test_query_chunks_endpoint_should_handle_filters(mock_indexing_service):
    """청크 조회 엔드포인트가 필터를 처리해야 함"""
    # Given
    from app.features.indexing.schema import ChunkQueryResponse
    from app.core.dependencies import get_indexing_service
    
    mock_response = ChunkQueryResponse(
        chunks=[],
        total=0,
        page=1,
        size=5,
        total_pages=0
    )
    
    mock_indexing_service.query_chunks = AsyncMock(return_value=mock_response)
    
    app.dependency_overrides[get_indexing_service] = lambda: mock_indexing_service
    client = TestClient(app)
    
    try:
        # When
        response = client.get("/api/v1/indexing/chunks", params={
            "file_path": "test.py",
            "code_type": "function",
            "language": "python",
            "keyword": "test",
            "page": 1,
            "size": 5
        })
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["size"] == 5
        
        # 서비스가 올바른 파라미터로 호출되었는지 확인
        mock_indexing_service.query_chunks.assert_called_once()
        call_args = mock_indexing_service.query_chunks.call_args[0][0]
        assert call_args.file_path == "test.py"
        assert call_args.code_type == "function"
        assert call_args.language == "python"
        assert call_args.keyword == "test"
        assert call_args.page == 1
        assert call_args.size == 5
    finally:
        app.dependency_overrides.clear()

def test_query_chunks_endpoint_should_handle_error(mock_indexing_service):
    """청크 조회 엔드포인트가 오류를 처리해야 함"""
    # Given
    from app.core.dependencies import get_indexing_service
    
    mock_indexing_service.query_chunks = AsyncMock(side_effect=Exception("조회 오류"))
    
    app.dependency_overrides[get_indexing_service] = lambda: mock_indexing_service
    client = TestClient(app)
    
    try:
        # When
        response = client.get("/api/v1/indexing/chunks")
        
        # Then
        assert response.status_code == 500
        data = response.json()
        assert "청크 조회 중 오류가 발생했습니다" in data["detail"]
    finally:
        app.dependency_overrides.clear()

def test_health_check_endpoint_should_return_healthy(client):
    """헬스체크 엔드포인트가 정상 응답을 반환해야 함"""
    # When
    response = client.get("/api/v1/indexing/health")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "indexing"

def test_index_file_endpoint_should_handle_validation_error(client):
    """파일 인덱싱 엔드포인트가 검증 오류를 처리해야 함"""
    # When
    response = client.post("/api/v1/indexing/file", json={
        # file_path 누락
        "force_update": False
    })
    
    # Then
    assert response.status_code == 422  # Validation Error 