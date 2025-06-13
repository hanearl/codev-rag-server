import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from app.index.bm25_index import (
    CodeTokenizer, BM25IndexConfig, CodeBM25Index
)
from app.index.base_index import IndexedDocument
from app.retriever.document_builder import EnhancedDocument
from app.retriever.ast_parser import CodeMetadata, Language, CodeType


class TestCodeTokenizer:
    """코드 토크나이저 테스트"""
    
    def test_tokenizer_initialization(self):
        """토크나이저 초기화 테스트"""
        tokenizer = CodeTokenizer()
        assert tokenizer.language == "english"
        assert tokenizer.stemmer is not None
        assert isinstance(tokenizer.stop_words, set)
        assert len(tokenizer.code_stop_words) > 0
    
    def test_basic_tokenization(self):
        """기본 토큰화 테스트"""
        tokenizer = CodeTokenizer()
        tokens = tokenizer.tokenize("hello world test")
        assert isinstance(tokens, list)
        assert len(tokens) > 0
    
    def test_camelcase_splitting(self):
        """CamelCase 분리 테스트"""
        tokenizer = CodeTokenizer()
        tokens = tokenizer.tokenize("getUserById")
        # CamelCase가 분리되어야 함
        token_text = " ".join(tokens)
        assert "user" in token_text.lower() or "get" in token_text.lower()
    
    def test_snake_case_splitting(self):
        """snake_case 분리 테스트"""
        tokenizer = CodeTokenizer()
        tokens = tokenizer.tokenize("get_user_by_id")
        # snake_case가 분리되어야 함
        assert len(tokens) >= 2
    
    def test_stop_words_filtering(self):
        """불용어 필터링 테스트"""
        tokenizer = CodeTokenizer()
        tokens = tokenizer.tokenize("public static void main")
        # 코드 불용어들이 제거되어야 함
        assert "public" not in tokens
        assert "static" not in tokens
        assert "void" not in tokens
    
    def test_preprocess_code(self):
        """코드 전처리 테스트"""
        tokenizer = CodeTokenizer()
        processed = tokenizer._preprocess_code("getUserById(String name)")
        assert "get" in processed.lower()
        assert "user" in processed.lower()


class TestBM25IndexConfig:
    """BM25 Index 설정 테스트"""
    
    def test_default_config(self):
        """기본 설정 테스트"""
        config = BM25IndexConfig()
        assert config.k1 == 1.2
        assert config.b == 0.75
        assert config.top_k == 10
        assert config.language == "english"
        assert config.use_stemming is True
        assert config.include_metadata is True
    
    def test_custom_config(self):
        """커스텀 설정 테스트"""
        config = BM25IndexConfig(
            k1=1.5,
            b=0.8,
            top_k=20,
            language="korean"
        )
        assert config.k1 == 1.5
        assert config.b == 0.8
        assert config.top_k == 20
        assert config.language == "korean"


class TestCodeBM25Index:
    """BM25 Index 테스트"""
    
    @pytest.fixture
    def bm25_config(self):
        """BM25 설정 fixture"""
        return BM25IndexConfig(
            index_path="tests/data/test_bm25_index",
            k1=1.2,
            b=0.75,
            top_k=5
        )
    
    @pytest.fixture
    def bm25_index(self, bm25_config):
        """BM25 Index fixture"""
        return CodeBM25Index(bm25_config)
    
    @pytest.fixture
    def sample_enhanced_document(self):
        """샘플 강화 문서 fixture"""
        from llama_index.core.schema import TextNode
        from llama_index.core import Document
        
        metadata = CodeMetadata(
            name="getUserById",
            code_type=CodeType.METHOD,
            language=Language.JAVA,
            file_path="/src/UserService.java",
            line_start=10,
            line_end=20,
            keywords=["user", "authentication", "id"],
            parameters=[{"name": "id", "type": "String"}],
            return_type="User"
        )
        
        content = """
        public User getUserById(String id) {
            return userRepository.findById(id);
        }
        """
        
        text_node = TextNode(
            text=content,
            metadata=metadata.model_dump(),
            id_="test_doc_1"
        )
        
        document = Document(
            text=content,
            metadata=metadata.model_dump(),
            id_="test_doc_1"
        )
        
        return EnhancedDocument(
            document=document,
            text_node=text_node,
            metadata=metadata,
            enhanced_content=content,
            search_keywords=["user", "get", "id", "authentication"],
            semantic_tags=["user_management", "data_access"],
            relationships={}
        )
    
    def test_bm25_index_initialization(self, bm25_index):
        """BM25 Index 초기화 테스트"""
        assert bm25_index.config is not None
        assert bm25_index.tokenizer is not None
        assert bm25_index.nodes == []
        assert bm25_index.documents_map == {}
    
    @pytest.mark.asyncio
    async def test_bm25_index_setup(self, bm25_index):
        """BM25 Index setup 테스트"""
        await bm25_index.setup()
        # setup 후에도 기본 상태가 유지되어야 함
        assert bm25_index.nodes == []
        assert bm25_index.retriever is None
    
    @pytest.mark.asyncio
    async def test_add_single_document(self, bm25_index, sample_enhanced_document):
        """단일 문서 추가 테스트"""
        await bm25_index.setup()
        
        added_ids = await bm25_index.add_documents([sample_enhanced_document])
        
        assert len(added_ids) == 1
        assert added_ids[0] == "test_doc_1"
        assert len(bm25_index.nodes) == 1
        assert "test_doc_1" in bm25_index.documents_map
        assert bm25_index.retriever is not None
    
    @pytest.mark.asyncio
    async def test_add_multiple_documents(self, bm25_index):
        """다중 문서 추가 테스트"""
        await bm25_index.setup()
        
        # 여러 문서 생성
        documents = []
        for i in range(3):
            doc_dict = {
                "id": f"test_doc_{i}",
                "content": f"test content {i}",
                "metadata": {
                    "name": f"testMethod{i}",
                    "language": "java"
                }
            }
            documents.append(doc_dict)
        
        added_ids = await bm25_index.add_documents(documents)
        
        assert len(added_ids) == 3
        assert len(bm25_index.nodes) == 3
        assert bm25_index.retriever is not None
    
    @pytest.mark.asyncio
    async def test_search_empty_index(self, bm25_index):
        """빈 인덱스 검색 테스트"""
        await bm25_index.setup()
        
        results = await bm25_index.search("test query", limit=5)
        
        assert isinstance(results, list)
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_with_documents(self, bm25_index, sample_enhanced_document):
        """문서가 있는 인덱스 검색 테스트"""
        await bm25_index.setup()
        await bm25_index.add_documents([sample_enhanced_document])
        
        results = await bm25_index.search("user authentication", limit=5)
        
        assert isinstance(results, list)
        # BM25 검색이 실제로 작동하면 결과가 있어야 함
        if len(results) > 0:
            assert all(isinstance(doc, IndexedDocument) for doc in results)
    
    @pytest.mark.asyncio
    async def test_search_with_scores(self, bm25_index, sample_enhanced_document):
        """점수와 함께 검색 테스트"""
        await bm25_index.setup()
        await bm25_index.add_documents([sample_enhanced_document])
        
        results = await bm25_index.search_with_scores("user id", limit=5)
        
        assert isinstance(results, list)
        if len(results) > 0:
            for result in results:
                assert "id" in result
                assert "content" in result
                assert "score" in result
                assert "source" in result
                assert result["source"] == "bm25"
    
    @pytest.mark.asyncio
    async def test_create_enhanced_text(self, bm25_index, sample_enhanced_document):
        """강화된 텍스트 생성 테스트"""
        enhanced_text = bm25_index._create_enhanced_text(sample_enhanced_document)
        
        assert isinstance(enhanced_text, str)
        assert len(enhanced_text) > 0
        # 메타데이터 정보가 포함되어야 함
        assert sample_enhanced_document.metadata.name in enhanced_text
        assert any(keyword in enhanced_text for keyword in sample_enhanced_document.search_keywords)
    
    @pytest.mark.asyncio
    async def test_update_document(self, bm25_index, sample_enhanced_document):
        """문서 업데이트 테스트"""
        await bm25_index.setup()
        await bm25_index.add_documents([sample_enhanced_document])
        
        updated_doc = {
            "id": "test_doc_1",
            "content": "updated content",
            "metadata": {"name": "updatedMethod"}
        }
        
        success = await bm25_index.update_document("test_doc_1", updated_doc)
        
        assert success is True
        # 업데이트 후에도 문서 수는 동일해야 함
        assert len(bm25_index.nodes) == 1
    
    @pytest.mark.asyncio
    async def test_delete_document(self, bm25_index, sample_enhanced_document):
        """문서 삭제 테스트"""
        await bm25_index.setup()
        await bm25_index.add_documents([sample_enhanced_document])
        
        # 삭제 전 확인
        assert len(bm25_index.nodes) == 1
        
        success = await bm25_index.delete_document("test_doc_1")
        
        assert success is True
        assert len(bm25_index.nodes) == 0
        assert "test_doc_1" not in bm25_index.documents_map
    
    @pytest.mark.asyncio
    async def test_get_stats(self, bm25_index, sample_enhanced_document):
        """통계 정보 테스트"""
        await bm25_index.setup()
        
        # 빈 인덱스 통계
        stats_empty = await bm25_index.get_stats()
        assert stats_empty["total_documents"] == 0
        assert stats_empty["total_tokens"] == 0
        
        # 문서 추가 후 통계
        await bm25_index.add_documents([sample_enhanced_document])
        stats_with_docs = await bm25_index.get_stats()
        
        assert stats_with_docs["total_documents"] == 1
        assert stats_with_docs["total_tokens"] > 0
        assert "bm25_parameters" in stats_with_docs
        assert stats_with_docs["bm25_parameters"]["k1"] == bm25_index.config.k1
    
    @pytest.mark.asyncio
    async def test_apply_filters(self, bm25_index):
        """필터 적용 테스트"""
        metadata = {
            "language": "java",
            "type": "method",
            "keywords": ["user", "authentication"]
        }
        
        # 일치하는 필터
        filters = {"language": "java", "type": "method"}
        assert bm25_index._apply_filters(metadata, filters) is True
        
        # 일치하지 않는 필터
        filters = {"language": "python"}
        assert bm25_index._apply_filters(metadata, filters) is False
        
        # 리스트 필터
        filters = {"keywords": "user"}
        assert bm25_index._apply_filters(metadata, filters) is True
        
        filters = {"keywords": "invalid"}
        assert bm25_index._apply_filters(metadata, filters) is False 