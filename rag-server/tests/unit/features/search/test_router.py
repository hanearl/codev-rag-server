import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.features.search.schema import SearchResponse, SearchResult

def test_search_endpoint_should_return_results():
    """검색 엔드포인트가 결과를 반환해야 함"""
    # Given
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
    
    # Mock the search service dependency
    mock_service = Mock()
    mock_service.search_code = AsyncMock(return_value=mock_response)
    
    # Override dependency
    from app.core.dependencies import get_search_service
    app.dependency_overrides[get_search_service] = lambda: mock_service
    
    try:
        client = TestClient(app)
        
        # When
        response = client.post("/api/v1/search/", json={
            "query": "test function",
            "limit": 10
        })
    finally:
        # Cleanup
        app.dependency_overrides.clear()
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["function_name"] == "test_func"

def test_search_endpoint_should_validate_request():
    """검색 엔드포인트가 요청을 검증해야 함"""
    # Given
    client = TestClient(app)
    
    # When: 잘못된 요청 (query 누락)
    response = client.post("/api/v1/search/", json={
        "limit": 10
    })
    
    # Then
    assert response.status_code == 422  # Validation Error

def test_search_health_endpoint():
    """검색 헬스체크 엔드포인트 테스트"""
    # Given
    client = TestClient(app)
    
    # When
    response = client.get("/api/v1/search/health")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "search-service" 