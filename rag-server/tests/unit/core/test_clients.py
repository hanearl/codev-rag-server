"""
외부 서비스 클라이언트 테스트
"""
import pytest
from unittest.mock import AsyncMock, patch, Mock
import httpx
from app.core.clients import EmbeddingClient, LLMClient, VectorClient, ExternalServiceClients, external_clients
from app.core.exceptions import EmbeddingServiceError, LLMServiceError, VectorDBError


class TestEmbeddingClient:
    """임베딩 클라이언트 테스트"""
    
    @pytest.mark.asyncio
    async def test_embed_single_should_call_embedding_api(self):
        """단일 텍스트 임베딩 API를 호출해야 함"""
        # Given
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "embedding": [0.1, 0.2, 0.3],
                "text": "test text"
            }
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response
            
            client = EmbeddingClient("http://localhost:8001")
            
            # When
            result = await client.embed_single({"text": "test text"})
            
            # Then
            assert result["embedding"] == [0.1, 0.2, 0.3]
            mock_client.return_value.__aenter__.return_value.request.assert_called_once_with(
                "POST",
                "http://localhost:8001/api/v1/embed",
                json={"text": "test text"},
                timeout=30.0
            )

    @pytest.mark.asyncio
    async def test_embed_bulk_should_call_bulk_embedding_api(self):
        """벌크 텍스트 임베딩 API를 호출해야 함"""
        # Given
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "embeddings": [
                    {"embedding": [0.1, 0.2, 0.3]},
                    {"embedding": [0.4, 0.5, 0.6]}
                ],
                "count": 2
            }
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response
            
            client = EmbeddingClient("http://localhost:8001")
            
            # When
            result = await client.embed_bulk({"texts": ["text1", "text2"]})
            
            # Then
            assert len(result["embeddings"]) == 2
            assert result["count"] == 2
            mock_client.return_value.__aenter__.return_value.request.assert_called_once_with(
                "POST",
                "http://localhost:8001/api/v1/embed/bulk",
                json={"texts": ["text1", "text2"]},
                timeout=30.0
            )

    @pytest.mark.asyncio
    async def test_embedding_client_should_handle_http_error(self):
        """HTTP 오류를 적절히 처리해야 함"""
        # Given
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=Mock(), response=mock_response
            )
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response
            
            client = EmbeddingClient("http://localhost:8001")
            
            # When & Then
            with pytest.raises(EmbeddingServiceError):
                await client.embed_single({"text": "test"})

    @pytest.mark.asyncio
    async def test_embedding_client_should_retry_on_temporary_failure(self):
        """일시적 장애 시 재시도해야 함"""
        # Given
        with patch('httpx.AsyncClient') as mock_client:
            # 첫 번째 호출은 실패, 두 번째 호출은 성공
            mock_success_response = Mock()
            mock_success_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
            mock_success_response.status_code = 200
            mock_success_response.raise_for_status.return_value = None
            
            mock_fail_response = Mock()
            mock_fail_response.status_code = 503
            mock_fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Service Unavailable", request=Mock(), response=mock_fail_response
            )
            
            mock_client.return_value.__aenter__.return_value.request.side_effect = [
                mock_fail_response,
                mock_success_response
            ]
            
            client = EmbeddingClient("http://localhost:8001", max_retries=2)
            
            # When
            result = await client.embed_single({"text": "test"})
            
            # Then
            assert result["embedding"] == [0.1, 0.2, 0.3]
            assert mock_client.return_value.__aenter__.return_value.request.call_count == 2

    def test_embedding_client_should_use_default_settings(self):
        """설정이 없을 때 기본값을 사용해야 함"""
        # Given & When
        client = EmbeddingClient()
        
        # Then
        assert client.base_url == "http://localhost:8001"  # settings에서 가져온 값
        assert client.timeout == 30  # settings에서 가져온 값
        assert client.max_retries == 3  # settings에서 가져온 값


class TestLLMClient:
    """LLM 클라이언트 테스트"""
    
    @pytest.mark.asyncio
    async def test_chat_completion_should_call_llm_api(self):
        """채팅 완성 API를 호출해야 함"""
        # Given
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
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
            mock_response.raise_for_status.return_value = None
            
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response
            
            client = LLMClient("http://localhost:8002")
            
            # When
            result = await client.chat_completion({
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Write a hello function"}]
            })
            
            # Then
            assert "choices" in result
            assert len(result["choices"]) == 1
            mock_client.return_value.__aenter__.return_value.request.assert_called_once_with(
                "POST",
                "http://localhost:8002/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Write a hello function"}]
                },
                timeout=60.0
            )

    @pytest.mark.asyncio
    async def test_llm_client_should_handle_error(self):
        """LLM 서비스 오류를 처리해야 함"""
        # Given
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=Mock(), response=mock_response
            )
            mock_client.return_value.__aenter__.return_value.request.return_value = mock_response
            
            client = LLMClient("http://localhost:8002")
            
            # When & Then
            with pytest.raises(LLMServiceError):
                await client.chat_completion({"messages": []})


class TestVectorClient:
    """벡터 DB 클라이언트 테스트"""
    
    @patch('app.core.clients.QdrantClient')
    def test_create_collection_should_create_qdrant_collection(self, mock_qdrant):
        """Qdrant 컬렉션을 생성해야 함"""
        # Given
        mock_instance = Mock()
        mock_qdrant.return_value = mock_instance
        
        client = VectorClient()
        
        # When
        result = client.create_collection("test_collection", 384)
        
        # Then
        assert result is True
        mock_instance.create_collection.assert_called_once()

    @patch('app.core.clients.QdrantClient')
    def test_insert_code_embedding_should_upsert_point(self, mock_qdrant):
        """코드 임베딩을 Qdrant에 삽입해야 함"""
        # Given
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

    @patch('app.core.clients.QdrantClient')
    def test_delete_by_file_path_should_delete_points(self, mock_qdrant):
        """파일 경로로 포인트들을 삭제해야 함"""
        # Given
        mock_instance = Mock()
        mock_result = Mock()
        mock_result.operation_id = 123
        mock_instance.delete.return_value = mock_result
        mock_qdrant.return_value = mock_instance
        
        client = VectorClient()
        
        # When
        result = client.delete_by_file_path("test_collection", "test.py")
        
        # Then
        assert result == 123
        mock_instance.delete.assert_called_once()

    @patch('app.core.clients.QdrantClient')
    def test_hybrid_search_should_return_search_results(self, mock_qdrant):
        """하이브리드 검색 결과를 반환해야 함"""
        # Given
        mock_instance = Mock()
        mock_scored_point = Mock()
        mock_scored_point.id = "test-id"
        mock_scored_point.score = 0.95
        mock_scored_point.payload = {
            "file_path": "test.py",
            "function_name": "test_func",
            "keywords": ["test", "function"]
        }
        mock_instance.search.return_value = [mock_scored_point]
        mock_qdrant.return_value = mock_instance
        
        client = VectorClient()
        
        # When
        results = client.hybrid_search(
            "test_collection",
            [0.1, 0.2, 0.3],
            keywords=["test"],
            limit=10
        )
        
        # Then
        assert len(results) == 1
        assert results[0]["id"] == "test-id"
        assert results[0]["vector_score"] == 0.95
        assert "keyword_score" in results[0]
        assert "combined_score" in results[0]
        mock_instance.search.assert_called_once()

    @patch('app.core.clients.QdrantClient')
    def test_vector_client_should_handle_error(self, mock_qdrant):
        """벡터 DB 오류를 처리해야 함"""
        # Given
        mock_instance = Mock()
        mock_instance.create_collection.side_effect = Exception("Connection failed")
        mock_qdrant.return_value = mock_instance
        
        client = VectorClient()
        
        # When & Then
        with pytest.raises(VectorDBError):
            client.create_collection("test_collection", 384)


class TestExternalServiceClients:
    """외부 서비스 클라이언트 팩토리 테스트"""
    
    def test_embedding_client_should_be_singleton(self):
        """임베딩 클라이언트는 싱글톤이어야 함"""
        # Given
        factory = ExternalServiceClients()
        
        # When
        client1 = factory.embedding
        client2 = factory.embedding
        
        # Then
        assert client1 is client2
        assert isinstance(client1, EmbeddingClient)
    
    def test_llm_client_should_be_singleton(self):
        """LLM 클라이언트는 싱글톤이어야 함"""
        # Given
        factory = ExternalServiceClients()
        
        # When
        client1 = factory.llm
        client2 = factory.llm
        
        # Then
        assert client1 is client2
        assert isinstance(client1, LLMClient)
    
    def test_vector_client_should_be_singleton(self):
        """벡터 클라이언트는 싱글톤이어야 함"""
        # Given
        factory = ExternalServiceClients()
        
        # When
        client1 = factory.vector
        client2 = factory.vector
        
        # Then
        assert client1 is client2
        assert isinstance(client1, VectorClient)
    
    def test_global_external_clients_should_exist(self):
        """전역 클라이언트 인스턴스가 존재해야 함"""
        # Given & When & Then
        assert external_clients is not None
        assert isinstance(external_clients, ExternalServiceClients)
        assert hasattr(external_clients, 'embedding')
        assert hasattr(external_clients, 'llm')
        assert hasattr(external_clients, 'vector') 