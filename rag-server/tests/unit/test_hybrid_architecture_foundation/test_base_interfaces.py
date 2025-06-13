"""
하이브리드 아키텍처 기본 인터페이스 테스트
"""
import pytest
from abc import ABC
from typing import get_type_hints

from app.retriever.base_retriever import BaseRetriever, RetrievalResult
from app.index.base_index import BaseIndex, IndexedDocument
from app.llm.base_chain import BaseChain, ChainInput, ChainOutput


class TestBaseInterfaces:
    """기본 인터페이스 테스트"""
    
    def test_base_retriever_is_abstract_class(self):
        """BaseRetriever가 추상 클래스인지 테스트"""
        assert issubclass(BaseRetriever, ABC)
        
        # 직접 인스턴스화 시 TypeError 발생해야 함
        with pytest.raises(TypeError):
            BaseRetriever()
    
    def test_base_retriever_has_required_methods(self):
        """BaseRetriever가 필수 메서드들을 가지고 있는지 테스트"""
        required_methods = ['retrieve', 'setup', 'teardown']
        
        for method_name in required_methods:
            assert hasattr(BaseRetriever, method_name)
            method = getattr(BaseRetriever, method_name)
            assert callable(method)
    
    def test_base_index_is_abstract_class(self):
        """BaseIndex가 추상 클래스인지 테스트"""
        assert issubclass(BaseIndex, ABC)
        
        # 직접 인스턴스화 시 TypeError 발생해야 함
        with pytest.raises(TypeError):
            BaseIndex()
    
    def test_base_index_has_required_methods(self):
        """BaseIndex가 필수 메서드들을 가지고 있는지 테스트"""
        required_methods = ['add_documents', 'update_document', 'delete_document', 'search', 'get_stats']
        
        for method_name in required_methods:
            assert hasattr(BaseIndex, method_name)
            method = getattr(BaseIndex, method_name)
            assert callable(method)
    
    def test_base_chain_is_abstract_class(self):
        """BaseChain이 추상 클래스인지 테스트"""
        assert issubclass(BaseChain, ABC)
        
        # 직접 인스턴스화 시 TypeError 발생해야 함
        with pytest.raises(TypeError):
            BaseChain()
    
    def test_base_chain_has_required_methods(self):
        """BaseChain이 필수 메서드들을 가지고 있는지 테스트"""
        required_methods = ['run', 'setup', 'teardown']
        
        for method_name in required_methods:
            assert hasattr(BaseChain, method_name)
            method = getattr(BaseChain, method_name)
            assert callable(method)


class TestModelClasses:
    """모델 클래스 테스트"""
    
    def test_retrieval_result_model(self):
        """RetrievalResult 모델 테스트"""
        result = RetrievalResult(
            id="test_id",
            content="test content",
            metadata={"key": "value"},
            score=0.85
        )
        
        assert result.id == "test_id"
        assert result.content == "test content"
        assert result.metadata == {"key": "value"}
        assert result.score == 0.85
        assert result.source == "unknown"  # 기본값
    
    def test_indexed_document_model(self):
        """IndexedDocument 모델 테스트"""
        doc = IndexedDocument(
            id="doc_id",
            content="document content",
            metadata={"author": "test"},
            indexed_at="2024-01-01T00:00:00Z"
        )
        
        assert doc.id == "doc_id"
        assert doc.content == "document content"
        assert doc.metadata == {"author": "test"}
        assert doc.indexed_at == "2024-01-01T00:00:00Z"
    
    def test_chain_input_model(self):
        """ChainInput 모델 테스트"""
        chain_input = ChainInput(
            query="test query",
            context=[{"key": "value"}],
            parameters={"param": "value"}
        )
        
        assert chain_input.query == "test query"
        assert chain_input.context == [{"key": "value"}]
        assert chain_input.parameters == {"param": "value"}
    
    def test_chain_output_model(self):
        """ChainOutput 모델 테스트"""
        chain_output = ChainOutput(
            response="test response",
            metadata={"key": "value"},
            processing_time_ms=100
        )
        
        assert chain_output.response == "test response"
        assert chain_output.metadata == {"key": "value"}
        assert chain_output.processing_time_ms == 100 