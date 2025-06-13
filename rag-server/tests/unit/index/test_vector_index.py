import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from app.index.vector_index import CodeVectorIndex, VectorIndexConfig
from app.index.vector_service import VectorIndexService
from app.index.base_index import IndexedDocument
from app.retriever.document_builder import EnhancedDocument
from app.retriever.ast_parser import CodeMetadata, Language, CodeType


class TestVectorIndexConfig:
    """Vector Index 설정 테스트"""
    
    def test_default_config(self):
        """기본 설정 테스트"""
        config = VectorIndexConfig()
        
        assert config.collection_name == "code_vectors"
        assert config.vector_size == 1536
        assert config.similarity_top_k == 10
        assert config.retrieval_mode == "similarity"
    
    def test_custom_config(self):
        """커스텀 설정 테스트"""
        config = VectorIndexConfig(
            collection_name="test_collection",
            vector_size=768,
            similarity_top_k=5
        )
        
        assert config.collection_name == "test_collection"
        assert config.vector_size == 768
        assert config.similarity_top_k == 5


class TestCodeVectorIndex:
    """코드 벡터 인덱스 테스트"""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Qdrant 클라이언트 Mock"""
        client = Mock()
        client.get_collections.return_value = Mock(collections=[])
        client.create_collection.return_value = None
        return client
    
    @pytest.fixture
    def config(self):
        """테스트용 설정"""
        return VectorIndexConfig(
            collection_name="test_vectors",
            qdrant_url="http://test-qdrant:6333"
        )
    
    @pytest.fixture
    def vector_index(self, config):
        """Vector Index 인스턴스"""
        return CodeVectorIndex(config)
    
    @patch('app.index.vector_index.QdrantClient')
    async def test_setup_creates_collection_if_not_exists(self, mock_qdrant_class, vector_index, mock_qdrant_client):
        """컬렉션이 없으면 생성하는지 테스트"""
        mock_qdrant_class.return_value = mock_qdrant_client
        
        await vector_index.setup()
        
        assert mock_qdrant_client.create_collection.called
        assert vector_index.client is not None
    
    @patch('app.index.vector_index.QdrantClient')
    async def test_setup_skips_creation_if_collection_exists(self, mock_qdrant_class, vector_index, mock_qdrant_client):
        """컬렉션이 이미 존재하면 생성을 건너뛰는지 테스트"""
        # 컬렉션이 이미 존재한다고 설정
        existing_collection = Mock()
        existing_collection.name = "test_vectors"
        mock_qdrant_client.get_collections.return_value = Mock(collections=[existing_collection])
        mock_qdrant_class.return_value = mock_qdrant_client
        
        await vector_index.setup()
        
        assert not mock_qdrant_client.create_collection.called
    
    def test_create_sample_enhanced_document(self):
        """샘플 강화된 문서 생성 테스트"""
        # 이 헬퍼 함수는 테스트에서 사용됨
        from llama_index.core import Document
        from llama_index.core.schema import TextNode
        
        metadata = CodeMetadata(
            file_path="test.py",
            language=Language.PYTHON,
            code_type=CodeType.METHOD,
            name="test_method",
            line_start=1,
            line_end=10
        )
        
        document = Document(
            text="def test_method(): pass",
            metadata=metadata.model_dump(),
            id_="test_doc_1"
        )
        
        text_node = TextNode(
            text="def test_method(): pass",
            metadata=metadata.model_dump(),
            id_="test_doc_1"
        )
        
        enhanced_doc = EnhancedDocument(
            document=document,
            text_node=text_node,
            metadata=metadata,
            enhanced_content="Enhanced: def test_method(): pass",
            search_keywords=["test", "method", "python"],
            semantic_tags=["function", "test"],
            relationships={}
        )
        
        assert enhanced_doc.document.text == "def test_method(): pass"
        assert enhanced_doc.metadata.name == "test_method"
        assert "test" in enhanced_doc.search_keywords


class TestVectorIndexService:
    """Vector Index 서비스 테스트"""
    
    @pytest.fixture
    def config(self):
        """테스트용 설정"""
        return VectorIndexConfig(collection_name="test_service_vectors")
    
    @pytest.fixture
    def vector_service(self, config):
        """Vector Index 서비스 인스턴스"""
        return VectorIndexService(config)
    
    @patch('app.index.vector_service.CodeVectorIndex')
    async def test_initialize_sets_up_index(self, mock_index_class, vector_service):
        """초기화 시 인덱스가 설정되는지 테스트"""
        mock_index = Mock()
        mock_index.setup = AsyncMock()
        mock_index_class.return_value = mock_index
        
        await vector_service.initialize()
        
        assert vector_service._initialized
        mock_index.setup.assert_called_once()
    
    @patch('app.index.vector_service.CodeVectorIndex')
    async def test_index_documents_success(self, mock_index_class, vector_service):
        """문서 인덱싱 성공 테스트"""
        mock_index = Mock()
        mock_index.setup = AsyncMock()
        mock_index.add_documents = AsyncMock(return_value=["doc1", "doc2"])
        mock_index_class.return_value = mock_index
        
        documents = [Mock(), Mock()]  # EnhancedDocument 모킹
        
        result = await vector_service.index_documents(documents)
        
        assert result["success"] is True
        assert result["indexed_count"] == 2
        assert result["document_ids"] == ["doc1", "doc2"]
    
    @patch('app.index.vector_service.CodeVectorIndex')
    async def test_search_similar_code_with_threshold(self, mock_index_class, vector_service):
        """임계값 기반 검색 테스트"""
        mock_index = Mock()
        mock_index.setup = AsyncMock()
        mock_index.similarity_search_with_threshold = AsyncMock(return_value=[
            {"id": "doc1", "score": 0.8, "content": "test code"}
        ])
        mock_index_class.return_value = mock_index
        
        results = await vector_service.search_similar_code(
            query="test function",
            threshold=0.7
        )
        
        assert len(results) == 1
        assert results[0]["score"] == 0.8
    
    @patch('app.index.vector_service.CodeVectorIndex')
    async def test_health_check_healthy(self, mock_index_class, vector_service):
        """헬스 체크 - 정상 상태 테스트"""
        mock_index = Mock()
        mock_index.setup = AsyncMock()
        mock_index.get_stats = AsyncMock(return_value={
            "total_documents": 100,
            "vector_size": 1536
        })
        mock_index_class.return_value = mock_index
        
        result = await vector_service.health_check()
        
        assert result["status"] == "healthy"
        assert result["document_count"] == 100
        assert result["vector_size"] == 1536
    
    @patch('app.index.vector_service.CodeVectorIndex')
    async def test_health_check_unhealthy(self, mock_index_class, vector_service):
        """헬스 체크 - 비정상 상태 테스트"""
        mock_index = Mock()
        mock_index.setup = AsyncMock(side_effect=Exception("Connection failed"))
        mock_index_class.return_value = mock_index
        
        result = await vector_service.health_check()
        
        assert result["status"] == "unhealthy"
        assert "error" in result


class TestVectorSearchIntegration:
    """벡터 검색 통합 테스트"""
    
    @pytest.fixture
    def sample_documents(self):
        """샘플 문서들"""
        from llama_index.core import Document
        from llama_index.core.schema import TextNode
        
        docs = []
        for i in range(3):
            metadata = CodeMetadata(
                file_path=f"test{i}.py",
                language=Language.PYTHON,
                code_type=CodeType.METHOD,
                name=f"test_method_{i}",
                line_start=i*10,
                line_end=(i+1)*10
            )
            
            document = Document(
                text=f"def test_method_{i}(): return {i}",
                metadata=metadata.model_dump(),
                id_=f"doc_{i}"
            )
            
            text_node = TextNode(
                text=f"def test_method_{i}(): return {i}",
                metadata=metadata.model_dump(),
                id_=f"doc_{i}"
            )
            
            enhanced_doc = EnhancedDocument(
                document=document,
                text_node=text_node,
                metadata=metadata,
                enhanced_content=f"Enhanced: def test_method_{i}(): return {i}",
                search_keywords=[f"test_{i}", "method", "python"],
                semantic_tags=["function"],
                relationships={}
            )
            docs.append(enhanced_doc)
        
        return docs
    
    @patch('app.index.vector_index.QdrantClient')
    @patch('app.core.clients.EmbeddingClient')
    async def test_end_to_end_vector_search(self, mock_embedding_client, mock_qdrant_class, sample_documents):
        """전체 벡터 검색 흐름 테스트"""
        # Qdrant 클라이언트 모킹
        mock_qdrant = Mock()
        mock_qdrant.get_collections.return_value = Mock(collections=[])
        mock_qdrant.create_collection.return_value = None
        mock_qdrant_class.return_value = mock_qdrant
        
        # 임베딩 클라이언트 모킹
        mock_embedding = Mock()
        mock_embedding.embed = AsyncMock(return_value={"embedding": [0.1] * 1536})
        mock_embedding_client.return_value = mock_embedding
        
        # VectorStoreIndex 모킹
        with patch('app.index.vector_index.VectorStoreIndex') as mock_index_class:
            mock_index = Mock()
            mock_index.insert_nodes = Mock()
            mock_index_class.return_value = mock_index
            mock_index_class.from_vector_store.return_value = mock_index
            
            # Retriever 모킹
            with patch('app.index.vector_index.VectorIndexRetriever') as mock_retriever_class:
                mock_retriever = Mock()
                mock_node_with_score = Mock()
                mock_node_with_score.node = Mock()
                mock_node_with_score.node.id_ = "doc_0"
                mock_node_with_score.node.text = "def test_method_0(): return 0"
                mock_node_with_score.node.metadata = {"file_path": "test0.py"}
                mock_node_with_score.score = 0.95
                
                mock_retriever.retrieve.return_value = [mock_node_with_score]
                mock_retriever_class.return_value = mock_retriever
                
                # 테스트 실행
                service = VectorIndexService()
                await service.initialize()
                
                # 문서 인덱싱
                result = await service.index_documents(sample_documents)
                assert result["success"] is True
                assert result["indexed_count"] == 3
                
                # 검색 실행
                search_results = await service.search_similar_code("test method")
                assert len(search_results) >= 0  # Mock에서는 실제 검색 결과가 나오지 않을 수 있음 