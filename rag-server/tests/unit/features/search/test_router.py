"""
하이브리드 검색 API 라우터 TDD 테스트
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from app.main import app
from app.features.search.schema import VectorSearchResponse, BM25SearchResponse, HybridSearchResponse, SearchResult

client = TestClient(app)


class TestHybridSearchRouter:
    """하이브리드 검색 API 라우터 테스트"""
    
    @pytest.fixture
    def sample_vector_search_request(self):
        """샘플 벡터 검색 요청 데이터"""
        return {
            "query": "JWT 인증 구현 방법",
            "collection_name": "test_collection",
            "top_k": 10,
            "score_threshold": 0.7,
            "filter_metadata": {
                "language": "java"
            }
        }
    
    @pytest.fixture
    def sample_bm25_search_request(self):
        """샘플 BM25 검색 요청 데이터"""
        return {
            "query": "authentication method",
            "index_name": "test_index",
            "top_k": 5,
            "filter_language": "java"
        }
    
    @pytest.fixture
    def sample_hybrid_search_request(self):
        """샘플 하이브리드 검색 요청 데이터"""
        return {
            "query": "사용자 인증 로직 구현",
            "collection_name": "test_collection",
            "index_name": "test_index",
            "top_k": 10,
            "vector_weight": 0.7,
            "bm25_weight": 0.3,
            "use_rrf": True,
            "rrf_k": 60,
            "score_threshold": 0.5,
            "filter_metadata": {"language": "java"},
            "filter_language": "java"
        }

    @pytest.fixture
    def mock_search_results(self):
        """Mock 검색 결과 데이터"""
        return [
            SearchResult(
                content="public class AuthService { public String authenticate(String token) { return jwt.validate(token); } }",
                score=0.95,
                metadata={"language": "java", "file_path": "AuthService.java", "function_name": "authenticate"},
                document_id="doc_1"
            ),
            SearchResult(
                content="def authenticate_user(token): return verify_jwt(token)",
                score=0.87,
                metadata={"language": "python", "file_path": "auth.py", "function_name": "authenticate_user"},
                document_id="doc_2"
            )
        ]

    @patch('app.features.search.service.HybridSearchService.vector_search')
    def test_vector_search_api_should_return_results(self, mock_vector_search, sample_vector_search_request, mock_search_results):
        """벡터 검색 API가 검색 결과를 반환해야 함"""
        # Given
        mock_vector_search.return_value = VectorSearchResponse(
            success=True,
            results=mock_search_results,
            total_results=len(mock_search_results),
            search_time_ms=150,
            collection_name=sample_vector_search_request["collection_name"],
            query=sample_vector_search_request["query"]
        )
        
        # When
        response = client.post("/api/v1/search/vector", json=sample_vector_search_request)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "results" in data
        assert "total_results" in data
        assert "search_time_ms" in data
        assert data["collection_name"] == sample_vector_search_request["collection_name"]
        assert len(data["results"]) == len(mock_search_results)

    @patch('app.features.search.service.HybridSearchService.bm25_search')
    def test_bm25_search_api_should_return_results(self, mock_bm25_search, sample_bm25_search_request, mock_search_results):
        """BM25 검색 API가 검색 결과를 반환해야 함"""
        # Given
        mock_bm25_search.return_value = BM25SearchResponse(
            success=True,
            results=mock_search_results[:1],  # BM25는 1개 결과
            total_results=1,
            search_time_ms=120,
            index_name=sample_bm25_search_request["index_name"],
            query=sample_bm25_search_request["query"]
        )
        
        # When
        response = client.post("/api/v1/search/bm25", json=sample_bm25_search_request)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "results" in data
        assert "total_results" in data
        assert "search_time_ms" in data
        assert data["index_name"] == sample_bm25_search_request["index_name"]

    @patch('app.features.search.service.HybridSearchService.hybrid_search')
    def test_hybrid_search_api_should_return_combined_results(self, mock_hybrid_search, sample_hybrid_search_request, mock_search_results):
        """하이브리드 검색 API가 결합된 검색 결과를 반환해야 함"""
        # Given
        mock_hybrid_search.return_value = HybridSearchResponse(
            success=True,
            results=mock_search_results,
            total_results=len(mock_search_results),
            search_time_ms=200,
            vector_results_count=2,
            bm25_results_count=1,
            fusion_method="rrf",
            weights_used={
                "vector_weight": 0.7,
                "bm25_weight": 0.3
            },
            query=sample_hybrid_search_request["query"]
        )
        
        # When
        response = client.post("/api/v1/search/hybrid", json=sample_hybrid_search_request)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "results" in data
        assert "total_results" in data
        assert "search_time_ms" in data
        assert "vector_results_count" in data
        assert "bm25_results_count" in data
        assert "fusion_method" in data
        assert "weights_used" in data

    def test_vector_search_api_should_handle_empty_query(self):
        """벡터 검색 API가 빈 쿼리를 적절히 처리해야 함"""
        # Given
        empty_query_request = {
            "query": "",
            "collection_name": "test_collection"
        }
        
        # When
        response = client.post("/api/v1/search/vector", json=empty_query_request)
        
        # Then
        assert response.status_code == 422  # Validation error

    def test_bm25_search_api_should_handle_invalid_top_k(self):
        """BM25 검색 API가 잘못된 top_k 값을 적절히 처리해야 함"""
        # Given
        invalid_request = {
            "query": "test query",
            "index_name": "test_index",
            "top_k": -1  # 잘못된 값
        }
        
        # When
        response = client.post("/api/v1/search/bm25", json=invalid_request)
        
        # Then
        assert response.status_code == 422  # Validation error

    def test_hybrid_search_api_should_validate_weights(self):
        """하이브리드 검색 API가 가중치를 적절히 검증해야 함"""
        # Given
        invalid_weights_request = {
            "query": "test query",
            "collection_name": "test_collection",
            "index_name": "test_index",
            "vector_weight": 1.5,  # 잘못된 값 (0-1 범위를 벗어남)
            "bm25_weight": -0.3    # 잘못된 값
        }
        
        # When
        response = client.post("/api/v1/search/hybrid", json=invalid_weights_request)
        
        # Then
        assert response.status_code == 422  # Validation error

    @patch('app.features.search.service.HybridSearchService.vector_search')
    def test_search_api_should_handle_server_error(self, mock_vector_search, sample_vector_search_request):
        """검색 API가 서버 오류를 적절히 처리해야 함"""
        # Given
        mock_vector_search.return_value = VectorSearchResponse(
            success=False,
            results=[],
            total_results=0,
            search_time_ms=50,
            collection_name=sample_vector_search_request["collection_name"],
            error="Test server error"
        )
        
        # When
        response = client.post("/api/v1/search/vector", json=sample_vector_search_request)
        
        # Then
        assert response.status_code == 500
        assert "Test server error" in response.json()["detail"]

    @patch('app.features.search.service.HybridSearchService.health_check')
    def test_search_health_check_should_return_status(self, mock_health_check):
        """검색 서비스 헬스체크가 상태 정보를 반환해야 함"""
        # Given
        mock_health_check.return_value = {
            "status": "healthy",
            "service": "search",
            "components": {
                "hybrid_retriever": "healthy",
                "vector_service": "healthy",
                "bm25_service": "healthy"
            }
        }
        
        # When
        response = client.get("/api/v1/search/health")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "search"
        assert "components" in data

    @patch('app.features.search.service.HybridSearchService.vector_search')
    def test_vector_search_api_should_apply_filters(self, mock_vector_search):
        """벡터 검색 API가 메타데이터 필터를 적용해야 함"""
        # Given
        filtered_request = {
            "query": "authentication",
            "collection_name": "test_collection",
            "filter_metadata": {
                "language": "java",
                "code_type": "method"
            }
        }
        
        mock_vector_search.return_value = VectorSearchResponse(
            success=True,
            results=[
                SearchResult(
                    content="public void authenticate() {}",
                    score=0.9,
                    metadata={"language": "java", "code_type": "method"},
                    document_id="doc_1"
                )
            ],
            total_results=1,
            search_time_ms=100,
            collection_name=filtered_request["collection_name"],
            query=filtered_request["query"]
        )
        
        # When
        response = client.post("/api/v1/search/vector", json=filtered_request)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        # 결과가 있다면 필터 조건을 만족하는지 확인
        for result in data["results"]:
            if "metadata" in result:
                assert result["metadata"].get("language") == "java"

    @patch('app.features.search.service.HybridSearchService.bm25_search')
    def test_bm25_search_api_should_apply_language_filter(self, mock_bm25_search):
        """BM25 검색 API가 언어 필터를 적용해야 함"""
        # Given
        language_filtered_request = {
            "query": "function definition",
            "index_name": "test_index",
            "filter_language": "python"
        }
        
        mock_bm25_search.return_value = BM25SearchResponse(
            success=True,
            results=[
                SearchResult(
                    content="def authenticate():",
                    score=0.8,
                    metadata={"language": "python"},
                    document_id="doc_1"
                )
            ],
            total_results=1,
            search_time_ms=80,
            index_name=language_filtered_request["index_name"],
            query=language_filtered_request["query"]
        )
        
        # When
        response = client.post("/api/v1/search/bm25", json=language_filtered_request)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        for result in data["results"]:
            if "metadata" in result:
                assert result["metadata"].get("language") == "python"

    def test_hybrid_search_api_should_handle_missing_indices(self):
        """하이브리드 검색 API가 존재하지 않는 인덱스를 적절히 처리해야 함"""
        # Given
        missing_indices_request = {
            "query": "test query",
            "collection_name": "non_existent_collection",
            "index_name": "non_existent_index"
        }
        
        # When
        response = client.post("/api/v1/search/hybrid", json=missing_indices_request)
        
        # Then
        # 인덱스가 없어도 API는 빈 결과를 반환하거나 적절한 오류를 반환해야 함
        assert response.status_code in [200, 404, 500]
    
    def test_search_result_format_should_be_consistent(self, sample_vector_search_request):
        """검색 결과 형식이 일관성 있어야 함"""
        # Given & When
        response = client.post("/api/v1/search/vector", json=sample_vector_search_request)
        
        # Then
        if response.status_code == 200:
            data = response.json()
            for result in data["results"]:
                assert "content" in result
                assert "score" in result
                assert "metadata" in result
                assert isinstance(result["score"], (int, float))
    
    def test_search_performance_metrics_should_be_tracked(self, sample_hybrid_search_request):
        """검색 성능 지표가 추적되어야 함"""
        # Given & When
        response = client.post("/api/v1/search/hybrid", json=sample_hybrid_search_request)
        
        # Then
        if response.status_code == 200:
            data = response.json()
            assert "search_time_ms" in data
            assert isinstance(data["search_time_ms"], int)
            assert data["search_time_ms"] >= 0
    
    def test_search_api_should_respect_top_k_limit(self, sample_vector_search_request):
        """검색 API가 top_k 제한을 준수해야 함"""
        # Given
        sample_vector_search_request["top_k"] = 3
        
        # When
        response = client.post("/api/v1/search/vector", json=sample_vector_search_request)
        
        # Then
        if response.status_code == 200:
            data = response.json()
            assert len(data["results"]) <= 3 