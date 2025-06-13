"""
하이브리드 아키텍처 예외 클래스 테스트
"""
import pytest

from app.retriever.exceptions import (
    RetrieverError, RetrieverSetupError, 
    RetrieverQueryError, RetrieverConnectionError
)
from app.index.exceptions import (
    IndexError, IndexBuildError, 
    IndexQueryError, IndexUpdateError
)
from app.llm.exceptions import (
    LLMError, LLMConfigError, 
    LLMProcessingError, LLMConnectionError
)
from app.features.hybrid_rag.exceptions import (
    HybridRAGError, HybridRAGConfigError,
    HybridRAGProcessingError, HybridRAGSearchError
)


class TestRetrieverExceptions:
    """리트리버 예외 클래스 테스트"""
    
    def test_retriever_error_inheritance(self):
        """RetrieverError가 기본 Exception을 상속하는지 테스트"""
        assert issubclass(RetrieverError, Exception)
    
    def test_retriever_specific_exceptions_inheritance(self):
        """리트리버 특정 예외들이 RetrieverError를 상속하는지 테스트"""
        exceptions = [
            RetrieverSetupError,
            RetrieverQueryError,
            RetrieverConnectionError
        ]
        
        for exception_class in exceptions:
            assert issubclass(exception_class, RetrieverError)
            assert issubclass(exception_class, Exception)
    
    def test_retriever_exception_instantiation(self):
        """리트리버 예외들이 정상적으로 인스턴스화되는지 테스트"""
        error_msg = "Test error message"
        
        # 기본 예외
        base_error = RetrieverError(error_msg)
        assert str(base_error) == error_msg
        
        # 특정 예외들
        setup_error = RetrieverSetupError(error_msg)
        assert str(setup_error) == error_msg
        
        query_error = RetrieverQueryError(error_msg)
        assert str(query_error) == error_msg
        
        connection_error = RetrieverConnectionError(error_msg)
        assert str(connection_error) == error_msg


class TestIndexExceptions:
    """인덱스 예외 클래스 테스트"""
    
    def test_index_error_inheritance(self):
        """IndexError가 기본 Exception을 상속하는지 테스트"""
        assert issubclass(IndexError, Exception)
    
    def test_index_specific_exceptions_inheritance(self):
        """인덱스 특정 예외들이 IndexError를 상속하는지 테스트"""
        exceptions = [
            IndexBuildError,
            IndexQueryError,
            IndexUpdateError
        ]
        
        for exception_class in exceptions:
            assert issubclass(exception_class, IndexError)
            assert issubclass(exception_class, Exception)
    
    def test_index_exception_instantiation(self):
        """인덱스 예외들이 정상적으로 인스턴스화되는지 테스트"""
        error_msg = "Test error message"
        
        # 기본 예외
        base_error = IndexError(error_msg)
        assert str(base_error) == error_msg
        
        # 특정 예외들
        build_error = IndexBuildError(error_msg)
        assert str(build_error) == error_msg
        
        query_error = IndexQueryError(error_msg)
        assert str(query_error) == error_msg
        
        update_error = IndexUpdateError(error_msg)
        assert str(update_error) == error_msg


class TestLLMExceptions:
    """LLM 예외 클래스 테스트"""
    
    def test_llm_error_inheritance(self):
        """LLMError가 기본 Exception을 상속하는지 테스트"""
        assert issubclass(LLMError, Exception)
    
    def test_llm_specific_exceptions_inheritance(self):
        """LLM 특정 예외들이 LLMError를 상속하는지 테스트"""
        exceptions = [
            LLMConfigError,
            LLMProcessingError,
            LLMConnectionError
        ]
        
        for exception_class in exceptions:
            assert issubclass(exception_class, LLMError)
            assert issubclass(exception_class, Exception)
    
    def test_llm_exception_instantiation(self):
        """LLM 예외들이 정상적으로 인스턴스화되는지 테스트"""
        error_msg = "Test error message"
        
        # 기본 예외
        base_error = LLMError(error_msg)
        assert str(base_error) == error_msg
        
        # 특정 예외들
        config_error = LLMConfigError(error_msg)
        assert str(config_error) == error_msg
        
        processing_error = LLMProcessingError(error_msg)
        assert str(processing_error) == error_msg
        
        connection_error = LLMConnectionError(error_msg)
        assert str(connection_error) == error_msg


class TestHybridRAGExceptions:
    """하이브리드 RAG 예외 클래스 테스트"""
    
    def test_hybrid_rag_error_inheritance(self):
        """HybridRAGError가 기본 Exception을 상속하는지 테스트"""
        assert issubclass(HybridRAGError, Exception)
    
    def test_hybrid_rag_specific_exceptions_inheritance(self):
        """하이브리드 RAG 특정 예외들이 HybridRAGError를 상속하는지 테스트"""
        exceptions = [
            HybridRAGConfigError,
            HybridRAGProcessingError,
            HybridRAGSearchError
        ]
        
        for exception_class in exceptions:
            assert issubclass(exception_class, HybridRAGError)
            assert issubclass(exception_class, Exception)
    
    def test_hybrid_rag_exception_instantiation(self):
        """하이브리드 RAG 예외들이 정상적으로 인스턴스화되는지 테스트"""
        error_msg = "Test error message"
        
        # 기본 예외
        base_error = HybridRAGError(error_msg)
        assert str(base_error) == error_msg
        
        # 특정 예외들
        config_error = HybridRAGConfigError(error_msg)
        assert str(config_error) == error_msg
        
        processing_error = HybridRAGProcessingError(error_msg)
        assert str(processing_error) == error_msg
        
        search_error = HybridRAGSearchError(error_msg)
        assert str(search_error) == error_msg 