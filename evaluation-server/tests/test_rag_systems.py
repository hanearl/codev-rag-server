import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from app.features.systems.interface import RetrievalResult
from app.features.systems.mock_client import MockRAGSystem
from app.features.systems.http_client import HTTPRAGSystem


class TestRetrievalResult:
    """검색 결과 모델 테스트"""
    
    def test_create_retrieval_result(self):
        """검색 결과 생성 테스트"""
        # Given
        result_data = {
            "content": "테스트 문서 내용",
            "score": 0.85,
            "filepath": "src/main/java/com/example/Test.java",
            "metadata": {"type": "java", "lines": 100}
        }
        
        # When
        result = RetrievalResult(**result_data)
        
        # Then
        assert result.content == "테스트 문서 내용"
        assert result.score == 0.85
        assert result.filepath == "src/main/java/com/example/Test.java"
        assert result.metadata["type"] == "java"
    
    def test_retrieval_result_defaults(self):
        """검색 결과 기본값 테스트"""
        # Given
        result = RetrievalResult(content="테스트", score=0.5)
        
        # Then
        assert result.filepath is None
        assert result.metadata == {}


class TestMockRAGSystem:
    """Mock RAG 시스템 테스트"""
    
    @pytest.fixture
    def mock_system(self):
        """Mock RAG 시스템 인스턴스"""
        return MockRAGSystem(
            embedding_dim=128,
            simulate_delay=False,  # 테스트에서는 지연 없음
            failure_rate=0.0
        )
    
    @pytest.mark.asyncio
    async def test_embed_query(self, mock_system):
        """쿼리 임베딩 테스트"""
        # Given
        query = "도서 관리 시스템"
        
        # When
        embedding = await mock_system.embed_query(query)
        
        # Then
        assert len(embedding) == 128
        assert all(isinstance(x, float) for x in embedding)
        assert all(-1 <= x <= 1 for x in embedding)
    
    @pytest.mark.asyncio
    async def test_embed_query_deterministic(self, mock_system):
        """동일한 쿼리에 대해 동일한 임베딩 생성 테스트"""
        # Given
        query = "테스트 쿼리"
        
        # When
        embedding1 = await mock_system.embed_query(query)
        embedding2 = await mock_system.embed_query(query)
        
        # Then
        assert embedding1 == embedding2
    
    @pytest.mark.asyncio
    async def test_retrieve_documents(self, mock_system):
        """문서 검색 테스트"""
        # Given
        query = "도서 관리"
        top_k = 5
        
        # When
        results = await mock_system.retrieve(query, top_k)
        
        # Then
        assert len(results) <= top_k
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert all(0 <= r.score <= 1 for r in results)
        
        # 점수 순으로 정렬되어 있는지 확인
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_retrieve_with_keyword_boost(self, mock_system):
        """키워드 매칭 시 점수 부스트 테스트"""
        # Given
        query_with_keyword = "BookController"
        query_without_keyword = "xyz123"
        
        # When
        results_with = await mock_system.retrieve(query_with_keyword, 10)
        results_without = await mock_system.retrieve(query_without_keyword, 10)
        
        # Then
        # BookController가 포함된 문서가 더 높은 점수를 받아야 함
        book_controller_result_with = next(
            (r for r in results_with if "BookController" in r.content), None
        )
        book_controller_result_without = next(
            (r for r in results_without if "BookController" in r.content), None
        )
        
        assert book_controller_result_with is not None
        assert book_controller_result_without is not None
        assert book_controller_result_with.score > book_controller_result_without.score
    
    @pytest.mark.asyncio
    async def test_health_check(self, mock_system):
        """헬스체크 테스트"""
        # When
        is_healthy = await mock_system.health_check()
        
        # Then
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_get_system_info(self, mock_system):
        """시스템 정보 조회 테스트"""
        # When
        info = await mock_system.get_system_info()
        
        # Then
        assert info["type"] == "MockRAGSystem"
        assert info["status"] == "healthy"
        assert info["embedding_dim"] == 128
        assert info["document_count"] > 0
        assert info["features"]["embedding"] is True
        assert info["features"]["retrieval"] is True
    
    @pytest.mark.asyncio
    async def test_failure_simulation(self):
        """실패 시뮬레이션 테스트"""
        # Given
        failing_system = MockRAGSystem(
            simulate_delay=False,
            failure_rate=1.0  # 100% 실패율
        )
        
        # When & Then
        with pytest.raises(Exception, match="Mock embedding failure"):
            await failing_system.embed_query("test")
        
        with pytest.raises(Exception, match="Mock retrieval failure"):
            await failing_system.retrieve("test")
        
        # 헬스체크는 실패해야 함
        is_healthy = await failing_system.health_check()
        assert is_healthy is False
    
    def test_document_management(self, mock_system):
        """문서 관리 기능 테스트"""
        # Given
        initial_count = len(mock_system.documents)
        
        # When - 문서 추가
        mock_system.add_document(
            content="새로운 테스트 문서",
            filepath="src/test/java/TestClass.java",
            score=0.9
        )
        
        # Then
        assert len(mock_system.documents) == initial_count + 1
        
        # When - 문서 제거
        mock_system.clear_documents()
        
        # Then
        assert len(mock_system.documents) == 0


class TestHTTPRAGSystem:
    """HTTP RAG 시스템 테스트"""
    
    @pytest.fixture
    def http_system(self):
        """HTTP RAG 시스템 인스턴스"""
        return HTTPRAGSystem(
            base_url="http://localhost:8001",
            api_key="test-key",
            timeout=10.0
        )
    
    @pytest.mark.asyncio
    async def test_embed_query_success(self, http_system):
        """임베딩 생성 성공 테스트"""
        # Given
        mock_response = {
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
        }
        
        # When
        with patch.object(http_system.client, 'post') as mock_post:
            # Mock response 객체 생성
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            
            mock_post.return_value = mock_response_obj
            
            embedding = await http_system.embed_query("test query")
        
        # Then
        assert embedding == [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_post.assert_called_once_with(
            "/api/v1/embed",
            json={"text": "test query"}
        )
    
    @pytest.mark.asyncio
    async def test_retrieve_success(self, http_system):
        """검색 성공 테스트"""
        # Given
        mock_response = {
            "results": [
                {
                    "content": "테스트 문서 1",
                    "score": 0.9,
                    "filepath": "src/main/java/Test1.java",
                    "metadata": {"type": "java"}
                },
                {
                    "content": "테스트 문서 2",
                    "score": 0.8,
                    "filepath": "src/main/java/Test2.java",
                    "metadata": {"type": "java"}
                }
            ]
        }
        
        # When
        with patch.object(http_system.client, 'post') as mock_post:
            # Mock response 객체 생성
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            
            mock_post.return_value = mock_response_obj
            
            results = await http_system.retrieve("test query", 5)
        
        # Then
        assert len(results) == 2
        assert results[0].content == "테스트 문서 1"
        assert results[0].score == 0.9
        assert results[0].filepath == "src/main/java/Test1.java"
        assert results[1].content == "테스트 문서 2"
        assert results[1].score == 0.8
        
        mock_post.assert_called_once_with(
            "/api/v1/search",
            json={"query": "test query", "k": 5}
        )
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, http_system):
        """헬스체크 성공 테스트"""
        # When
        with patch.object(http_system.client, 'get') as mock_get:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_get.return_value = mock_response_obj
            
            is_healthy = await http_system.health_check()
        
        # Then
        assert is_healthy is True
        mock_get.assert_called_once_with("/health")
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, http_system):
        """헬스체크 실패 테스트"""
        # When
        with patch.object(http_system.client, 'get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")
            
            is_healthy = await http_system.health_check()
        
        # Then
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_get_system_info_success(self, http_system):
        """시스템 정보 조회 성공 테스트"""
        # Given
        mock_response = {
            "type": "ExternalRAGSystem",
            "status": "healthy",
            "version": "1.0.0"
        }
        
        # When
        with patch.object(http_system.client, 'get') as mock_get:
            mock_response_obj = MagicMock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response
            mock_get.return_value = mock_response_obj
            
            info = await http_system.get_system_info()
        
        # Then
        assert info == mock_response
        mock_get.assert_called_once_with("/api/v1/info")
    
    @pytest.mark.asyncio
    async def test_http_error_handling(self, http_system):
        """HTTP 오류 처리 테스트"""
        # When & Then
        with patch.object(http_system.client, 'post') as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "404 Not Found", 
                request=MagicMock(), 
                response=MagicMock()
            )
            
            with pytest.raises(httpx.HTTPStatusError):
                await http_system.embed_query("test")
    
    @pytest.mark.asyncio
    async def test_close_client(self, http_system):
        """클라이언트 종료 테스트"""
        # When
        with patch.object(http_system.client, 'aclose') as mock_close:
            await http_system.close()
        
        # Then
        mock_close.assert_called_once()
    
    def test_repr(self, http_system):
        """문자열 표현 테스트"""
        # When
        repr_str = repr(http_system)
        
        # Then
        assert "HTTPRAGSystem" in repr_str
        assert "http://localhost:8001" in repr_str 