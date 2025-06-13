import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from app.index.bm25_service import BM25IndexService
from app.index.bm25_index import BM25IndexConfig, CodeBM25Index
from app.retriever.document_builder import EnhancedDocument
from app.retriever.ast_parser import CodeMetadata, Language, CodeType


class TestBM25IndexService:
    """BM25 Index 서비스 테스트"""
    
    @pytest.fixture
    def bm25_config(self):
        """BM25 설정 fixture"""
        return BM25IndexConfig(
            index_path="tests/data/test_bm25_service",
            k1=1.2,
            b=0.75,
            top_k=10
        )
    
    @pytest.fixture
    def bm25_service(self, bm25_config):
        """BM25 Service fixture"""
        return BM25IndexService(bm25_config)
    
    @pytest.fixture
    def sample_enhanced_documents(self):
        """샘플 강화 문서들 fixture"""
        from llama_index.core.schema import TextNode
        from llama_index.core import Document
        
        documents = []
        for i in range(3):
            metadata = CodeMetadata(
                name=f"method{i}",
                code_type=CodeType.METHOD,
                language=Language.JAVA,
                file_path=f"/src/Service{i}.java",
                line_start=10 + i * 10,
                line_end=20 + i * 10,
                keywords=[f"keyword{i}", "test"],
                parameters=[{"name": "param", "type": "String"}],
                return_type="void"
            )
            
            content = f"""
            public void method{i}(String param) {{
                System.out.println("Method {i} execution");
            }}
            """
            
            text_node = TextNode(
                text=content,
                metadata=metadata.model_dump(),
                id_=f"doc_{i}"
            )
            
            document = Document(
                text=content,
                metadata=metadata.model_dump(),
                id_=f"doc_{i}"
            )
            
            enhanced_doc = EnhancedDocument(
                document=document,
                text_node=text_node,
                metadata=metadata,
                enhanced_content=content,
                search_keywords=[f"method{i}", "test", "execution"],
                semantic_tags=["business_logic"],
                relationships={}
            )
            
            documents.append(enhanced_doc)
        
        return documents
    
    def test_service_initialization(self, bm25_service):
        """서비스 초기화 테스트"""
        assert bm25_service.config is not None
        assert bm25_service.index is not None
        assert isinstance(bm25_service.index, CodeBM25Index)
        assert bm25_service._initialized is False
    
    def test_service_initialization_with_default_config(self):
        """기본 설정으로 서비스 초기화 테스트"""
        service = BM25IndexService()
        assert service.config is not None
        assert isinstance(service.config, BM25IndexConfig)
        assert service.index is not None
    
    @pytest.mark.asyncio
    async def test_service_initialize(self, bm25_service):
        """서비스 초기화 테스트"""
        # 초기화 전
        assert bm25_service._initialized is False
        
        # 초기화 실행
        await bm25_service.initialize()
        
        # 초기화 후
        assert bm25_service._initialized is True
        
        # 중복 초기화는 실행되지 않아야 함
        with patch.object(bm25_service.index, 'setup') as mock_setup:
            await bm25_service.initialize()
            mock_setup.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_index_documents_success(self, bm25_service, sample_enhanced_documents):
        """문서 인덱싱 성공 테스트"""
        with patch.object(bm25_service.index, 'add_documents') as mock_add:
            mock_add.return_value = ["doc_0", "doc_1", "doc_2"]
            
            result = await bm25_service.index_documents(sample_enhanced_documents)
            
            assert result["success"] is True
            assert result["indexed_count"] == 3
            assert result["index_type"] == "bm25"
            assert len(result["document_ids"]) == 3
            mock_add.assert_called_once_with(sample_enhanced_documents)
    
    @pytest.mark.asyncio
    async def test_index_documents_failure(self, bm25_service, sample_enhanced_documents):
        """문서 인덱싱 실패 테스트"""
        with patch.object(bm25_service.index, 'add_documents') as mock_add:
            mock_add.side_effect = Exception("인덱싱 실패")
            
            result = await bm25_service.index_documents(sample_enhanced_documents)
            
            assert result["success"] is False
            assert result["indexed_count"] == 0
            assert "error" in result
            assert "인덱싱 실패" in result["error"]
    
    @pytest.mark.asyncio
    async def test_search_keywords(self, bm25_service):
        """키워드 검색 테스트"""
        mock_results = [
            {
                "id": "doc_1",
                "content": "test content",
                "score": 0.8,
                "source": "bm25"
            }
        ]
        
        with patch.object(bm25_service.index, 'search_with_scores') as mock_search:
            mock_search.return_value = mock_results
            
            results = await bm25_service.search_keywords("test query", limit=5)
            
            assert results == mock_results
            mock_search.assert_called_once_with("test query", 5, None)
    
    @pytest.mark.asyncio
    async def test_search_keywords_with_filters(self, bm25_service):
        """필터가 있는 키워드 검색 테스트"""
        filters = {"language": "java", "type": "method"}
        
        with patch.object(bm25_service.index, 'search_with_scores') as mock_search:
            mock_search.return_value = []
            
            await bm25_service.search_keywords("test", limit=10, filters=filters)
            
            mock_search.assert_called_once_with("test", 10, filters)
    
    @pytest.mark.asyncio
    async def test_update_document(self, bm25_service):
        """문서 업데이트 테스트"""
        doc_data = {
            "content": "updated content",
            "metadata": {"name": "updatedMethod"}
        }
        
        with patch.object(bm25_service.index, 'update_document') as mock_update:
            mock_update.return_value = True
            
            result = await bm25_service.update_document("doc_1", doc_data)
            
            assert result is True
            mock_update.assert_called_once_with("doc_1", doc_data)
    
    @pytest.mark.asyncio
    async def test_delete_document(self, bm25_service):
        """문서 삭제 테스트"""
        with patch.object(bm25_service.index, 'delete_document') as mock_delete:
            mock_delete.return_value = True
            
            result = await bm25_service.delete_document("doc_1")
            
            assert result is True
            mock_delete.assert_called_once_with("doc_1")
    
    @pytest.mark.asyncio
    async def test_get_index_stats(self, bm25_service):
        """인덱스 통계 조회 테스트"""
        mock_stats = {
            "total_documents": 5,
            "total_tokens": 1000,
            "average_tokens_per_doc": 200.0,
            "language_distribution": {"java": 3, "python": 2}
        }
        
        with patch.object(bm25_service.index, 'get_stats') as mock_stats_method:
            mock_stats_method.return_value = mock_stats
            
            result = await bm25_service.get_index_stats()
            
            assert result == mock_stats
            mock_stats_method.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rebuild_index_success(self, bm25_service, sample_enhanced_documents):
        """인덱스 재구성 성공 테스트"""
        with patch.object(bm25_service, 'index_documents') as mock_index:
            mock_index.return_value = {
                "success": True,
                "indexed_count": 3
            }
            
            result = await bm25_service.rebuild_index(sample_enhanced_documents)
            
            assert result["success"] is True
            assert result["indexed_count"] == 3
            
            # 기존 데이터가 초기화되었는지 확인
            assert bm25_service.index.nodes == []
            assert bm25_service.index.documents_map == {}
    
    @pytest.mark.asyncio
    async def test_rebuild_index_failure(self, bm25_service, sample_enhanced_documents):
        """인덱스 재구성 실패 테스트"""
        with patch.object(bm25_service, 'index_documents') as mock_index:
            mock_index.side_effect = Exception("재구성 실패")
            
            result = await bm25_service.rebuild_index(sample_enhanced_documents)
            
            assert result["success"] is False
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, bm25_service):
        """헬스 체크 - 정상 상태 테스트"""
        mock_stats = {
            "total_documents": 10,
            "total_tokens": 2000
        }
        
        with patch.object(bm25_service, 'get_index_stats') as mock_stats_method:
            mock_stats_method.return_value = mock_stats
            
            result = await bm25_service.health_check()
            
            assert result["status"] == "healthy"
            assert result["index_type"] == "bm25"
            assert result["document_count"] == 10
            assert result["total_tokens"] == 2000
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, bm25_service):
        """헬스 체크 - 비정상 상태 테스트"""
        with patch.object(bm25_service, 'initialize') as mock_init:
            mock_init.side_effect = Exception("초기화 실패")
            
            result = await bm25_service.health_check()
            
            assert result["status"] == "unhealthy"
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_automatic_initialization_on_methods(self, bm25_service):
        """메서드 호출 시 자동 초기화 테스트"""
        with patch.object(bm25_service, 'initialize') as mock_init:
            mock_init.return_value = None
            
            with patch.object(bm25_service.index, 'search_with_scores') as mock_search:
                mock_search.return_value = []
                
                await bm25_service.search_keywords("test")
                
                # initialize가 호출되었는지 확인
                mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_service_with_real_index_operations(self, bm25_service, sample_enhanced_documents):
        """실제 인덱스 작업과 연동 테스트"""
        # 실제 BM25Index와 연동하여 테스트
        await bm25_service.initialize()
        
        # 문서 인덱싱
        result = await bm25_service.index_documents(sample_enhanced_documents)
        assert result["success"] is True
        assert result["indexed_count"] == 3
        
        # 검색 테스트
        search_results = await bm25_service.search_keywords("method", limit=5)
        assert isinstance(search_results, list)
        
        # 통계 조회
        stats = await bm25_service.get_index_stats()
        assert stats["total_documents"] == 3
        assert stats["total_tokens"] > 0
        
        # 헬스 체크
        health = await bm25_service.health_check()
        assert health["status"] == "healthy" 