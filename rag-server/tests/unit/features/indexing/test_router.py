"""
하이브리드 인덱싱 API 라우터 TDD 테스트
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from app.main import app

client = TestClient(app)


class TestHybridIndexingRouter:
    """하이브리드 인덱싱 API 라우터 테스트"""
    
    @pytest.fixture
    def sample_parse_request(self):
        """샘플 파싱 요청 데이터"""
        return {
            "code": "public class TestClass { public void testMethod() {} }",
            "language": "java",
            "file_path": "TestClass.java",
            "extract_methods": True,
            "extract_classes": True,
            "extract_functions": True,
            "extract_imports": True
        }
    
    @pytest.fixture
    def sample_document_build_request(self):
        """샘플 문서 빌드 요청 데이터"""
        return {
            "ast_info_list": [
                {
                    "classes": ["TestClass"],
                    "methods": ["testMethod"], 
                    "functions": [],
                    "imports": [],
                    "metadata": {"file_path": "test.java", "language": "java"}
                }
            ],
            "chunking_strategy": "method_level",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "include_metadata": True
        }
    
    @pytest.fixture
    def sample_indexing_request(self):
        """샘플 인덱싱 요청 데이터"""
        return {
            "documents": [
                {
                    "content": "public void testMethod() { System.out.println(\"test\"); }",
                    "metadata": {
                        "file_path": "Test.java",
                        "language": "java",
                        "code_type": "method"
                    }
                }
            ],
            "collection_name": "test_collection",
            "batch_size": 100,
            "update_existing": False
        }
    
    @patch('app.features.indexing.service.HybridIndexingService.parse_code')
    def test_parse_code_api_should_return_success(self, mock_parse_code, sample_parse_request):
        """코드 파싱 API가 성공 응답을 반환해야 함"""
        # Given
        from app.features.indexing.schema import ParseResponse
        mock_parse_code.return_value = ParseResponse(
            success=True,
            ast_info={
                "classes": ["TestClass"],
                "methods": ["testMethod"],
                "imports": []
            },
            parse_time_ms=150
        )
        
        # When
        response = client.post("/api/v1/indexing/parse", json=sample_parse_request)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "ast_info" in data
        assert "parse_time_ms" in data
    
    def test_parse_code_api_should_handle_invalid_language(self):
        """잘못된 언어 파라미터에 대해 422 validation error를 반환해야 함"""
        # Given
        invalid_request = {
            "code": "test code",
            "language": "invalid_language"
        }
        
        # When
        response = client.post("/api/v1/indexing/parse", json=invalid_request)
        
        # Then
        assert response.status_code == 422  # Pydantic validation error
        # Validation error 응답은 detail이 다를 수 있음
    
    def test_parse_files_api_should_handle_multiple_files(self):
        """여러 파일 일괄 파싱 API가 정상 동작해야 함"""
        # Given
        files = [
            ("files", ("test1.java", "public class Test1 {}", "text/plain")),
            ("files", ("test2.java", "public class Test2 {}", "text/plain"))
        ]
        
        # When
        response = client.post(
            "/api/v1/indexing/parse/files",
            files=files,
            data={"language": "java"}
        )
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        for result in data:
            assert "success" in result
    
    @patch('app.features.indexing.service.HybridIndexingService.build_documents')
    def test_build_documents_api_should_return_success(self, mock_build_documents, sample_document_build_request):
        """문서 빌드 API가 성공 응답을 반환해야 함"""
        # Given
        from app.features.indexing.schema import DocumentBuildResponse
        mock_build_documents.return_value = DocumentBuildResponse(
            success=True,
            documents=[
                {
                    "content": "test content",
                    "metadata": {"file_path": "test.java", "language": "java"}
                }
            ],
            total_documents=1,
            build_time_ms=200
        )
        
        # When
        response = client.post("/api/v1/indexing/documents/build", json=sample_document_build_request)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "documents" in data
        assert "total_documents" in data
        assert "build_time_ms" in data
    
    @patch('app.features.indexing.service.HybridIndexingService.create_vector_index')
    def test_create_vector_index_api_should_return_success(self, mock_create_vector_index, sample_indexing_request):
        """벡터 인덱스 생성 API가 성공 응답을 반환해야 함"""
        # Given
        from app.features.indexing.schema import IndexingResponse
        mock_create_vector_index.return_value = IndexingResponse(
            success=True,
            indexed_count=1,
            collection_name="test_collection",
            index_time_ms=300
        )
        
        # When
        response = client.post("/api/v1/indexing/vector/index", json=sample_indexing_request)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "indexed_count" in data
        assert "collection_name" in data
        assert "index_time_ms" in data
    
    @patch('app.features.indexing.service.HybridIndexingService.create_bm25_index')
    def test_create_bm25_index_api_should_return_success(self, mock_create_bm25_index, sample_indexing_request):
        """BM25 인덱스 생성 API가 성공 응답을 반환해야 함"""
        # Given
        from app.features.indexing.schema import IndexingResponse
        mock_create_bm25_index.return_value = IndexingResponse(
            success=True,
            indexed_count=1,
            index_time_ms=250
        )
        
        # When
        response = client.post("/api/v1/indexing/bm25/index", json=sample_indexing_request)
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "indexed_count" in data
        assert "index_time_ms" in data
    
    @patch('app.features.indexing.service.HybridIndexingService.get_index_stats')
    def test_get_index_stats_api_should_return_stats(self, mock_get_index_stats):
        """인덱스 통계 조회 API가 통계 정보를 반환해야 함"""
        # Given
        from app.features.indexing.schema import IndexStatsResponse
        mock_get_index_stats.return_value = IndexStatsResponse(
            vector_index_stats={
                "total_documents": 100,
                "total_vectors": 100
            },
            bm25_index_stats={
                "total_documents": 100,
                "index_size": "5MB"
            },
            total_documents=100
        )
        
        # When
        response = client.get("/api/v1/indexing/stats")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert "vector_index_stats" in data
        assert "bm25_index_stats" in data
        assert "total_documents" in data
    
    def test_delete_vector_collection_api_should_return_success(self):
        """벡터 컬렉션 삭제 API가 성공 메시지를 반환해야 함"""
        # Given
        collection_name = "test_collection"
        
        # When
        response = client.delete(f"/api/v1/indexing/vector/{collection_name}")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert collection_name in data["message"]
    
    def test_delete_bm25_index_api_should_return_success(self):
        """BM25 인덱스 삭제 API가 성공 메시지를 반환해야 함"""
        # Given
        index_name = "test_index"
        
        # When
        response = client.delete(f"/api/v1/indexing/bm25/{index_name}")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert index_name in data["message"]
    
    def test_indexing_health_check_should_return_healthy(self):
        """인덱싱 서비스 헬스체크가 정상 상태를 반환해야 함"""
        # Given & When
        response = client.get("/api/v1/indexing/health")
        
        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["service"] == "indexing"
        assert "components" in data
    
    def test_parse_code_api_should_handle_server_error(self, sample_parse_request):
        """파싱 API가 서버 오류를 적절히 처리해야 함"""
        # Given
        with patch('app.features.indexing.service.HybridIndexingService.parse_code') as mock_parse:
            mock_parse.side_effect = Exception("Test server error")
            
            # When
            response = client.post("/api/v1/indexing/parse", json=sample_parse_request)
            
            # Then
            assert response.status_code == 500
            assert "코드 파싱 중 오류가 발생했습니다" in response.json()["detail"]
    
    def test_vector_index_api_should_handle_invalid_documents(self):
        """벡터 인덱싱 API가 잘못된 문서를 적절히 처리해야 함"""
        # Given
        invalid_request = {
            "documents": [],  # 빈 문서 리스트
            "collection_name": ""  # 빈 컬렉션 이름
        }
        
        # When
        response = client.post("/api/v1/indexing/vector/index", json=invalid_request)
        
        # Then
        assert response.status_code == 422  # Validation error
    
    def test_parse_files_api_should_handle_no_files(self):
        """파일 파싱 API가 파일이 없는 경우를 적절히 처리해야 함"""
        # Given & When
        response = client.post("/api/v1/indexing/parse/files", files=[])
        
        # Then
        assert response.status_code == 422  # Validation error 