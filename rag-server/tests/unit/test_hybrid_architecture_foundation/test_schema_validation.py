"""
하이브리드 아키텍처 스키마 검증 테스트
"""
import pytest
from pydantic import ValidationError

from app.features.hybrid_rag.schema import (
    HybridSearchRequest, HybridSearchResult, HybridSearchResponse,
    ExplainRequest, ExplainResponse
)


class TestHybridSearchRequest:
    """하이브리드 검색 요청 스키마 테스트"""
    
    def test_valid_hybrid_search_request(self):
        """유효한 하이브리드 검색 요청 테스트"""
        request = HybridSearchRequest(
            query="test query",
            limit=5,
            vector_weight=0.8,
            keyword_weight=0.2,
            use_rrf=True,
            filters={"language": "python"}
        )
        
        assert request.query == "test query"
        assert request.limit == 5
        assert request.vector_weight == 0.8
        assert request.keyword_weight == 0.2
        assert request.use_rrf is True
        assert request.filters == {"language": "python"}
    
    def test_hybrid_search_request_with_defaults(self):
        """기본값이 설정된 하이브리드 검색 요청 테스트"""
        request = HybridSearchRequest(query="test query")
        
        assert request.query == "test query"
        assert request.limit == 10  # 기본값
        assert request.vector_weight == 0.7  # 기본값
        assert request.keyword_weight == 0.3  # 기본값
        assert request.use_rrf is True  # 기본값
        assert request.filters is None  # 기본값
    
    def test_hybrid_search_request_limit_validation(self):
        """검색 결과 수 제한 검증 테스트"""
        # 유효한 범위
        request = HybridSearchRequest(query="test", limit=1)
        assert request.limit == 1
        
        request = HybridSearchRequest(query="test", limit=50)
        assert request.limit == 50
        
        # 무효한 범위 - 0 이하
        with pytest.raises(ValidationError):
            HybridSearchRequest(query="test", limit=0)
        
        # 무효한 범위 - 50 초과
        with pytest.raises(ValidationError):
            HybridSearchRequest(query="test", limit=51)
    
    def test_hybrid_search_request_weight_validation(self):
        """가중치 검증 테스트"""
        # 유효한 범위 (0.0 ~ 1.0)
        request = HybridSearchRequest(
            query="test",
            vector_weight=0.0,
            keyword_weight=1.0
        )
        assert request.vector_weight == 0.0
        assert request.keyword_weight == 1.0
        
        # 무효한 범위 - 음수
        with pytest.raises(ValidationError):
            HybridSearchRequest(query="test", vector_weight=-0.1)
        
        # 무효한 범위 - 1.0 초과
        with pytest.raises(ValidationError):
            HybridSearchRequest(query="test", keyword_weight=1.1)
    
    def test_hybrid_search_request_missing_query(self):
        """필수 필드 누락 테스트"""
        with pytest.raises(ValidationError):
            HybridSearchRequest()


class TestHybridSearchResult:
    """하이브리드 검색 결과 스키마 테스트"""
    
    def test_valid_hybrid_search_result(self):
        """유효한 하이브리드 검색 결과 테스트"""
        result = HybridSearchResult(
            id="result_1",
            content="test content",
            file_path="/path/to/file.py",
            function_name="test_function",
            language="python",
            vector_score=0.85,
            keyword_score=0.75,
            combined_score=0.80,
            metadata={"author": "test"}
        )
        
        assert result.id == "result_1"
        assert result.content == "test content"
        assert result.file_path == "/path/to/file.py"
        assert result.function_name == "test_function"
        assert result.language == "python"
        assert result.vector_score == 0.85
        assert result.keyword_score == 0.75
        assert result.combined_score == 0.80
        assert result.metadata == {"author": "test"}
    
    def test_hybrid_search_result_with_defaults(self):
        """기본값이 설정된 하이브리드 검색 결과 테스트"""
        result = HybridSearchResult(
            id="result_1",
            content="test content"
        )
        
        assert result.id == "result_1"
        assert result.content == "test content"
        assert result.file_path is None
        assert result.function_name is None
        assert result.language is None
        assert result.vector_score == 0.0
        assert result.keyword_score == 0.0
        assert result.combined_score == 0.0
        assert result.metadata == {}


class TestHybridSearchResponse:
    """하이브리드 검색 응답 스키마 테스트"""
    
    def test_valid_hybrid_search_response(self):
        """유효한 하이브리드 검색 응답 테스트"""
        results = [
            HybridSearchResult(id="1", content="content 1"),
            HybridSearchResult(id="2", content="content 2")
        ]
        
        response = HybridSearchResponse(
            query="test query",
            results=results,
            total_results=2,
            search_time_ms=150,
            search_metadata={"method": "hybrid"}
        )
        
        assert response.query == "test query"
        assert len(response.results) == 2
        assert response.total_results == 2
        assert response.search_time_ms == 150
        assert response.search_metadata == {"method": "hybrid"}


class TestExplainRequest:
    """코드 설명 요청 스키마 테스트"""
    
    def test_valid_explain_request(self):
        """유효한 코드 설명 요청 테스트"""
        search_results = [
            HybridSearchResult(id="1", content="content 1")
        ]
        
        request = ExplainRequest(
            query="Explain this code",
            search_results=search_results,
            include_context=False,
            language_preference="english"
        )
        
        assert request.query == "Explain this code"
        assert len(request.search_results) == 1
        assert request.include_context is False
        assert request.language_preference == "english"
    
    def test_explain_request_with_defaults(self):
        """기본값이 설정된 코드 설명 요청 테스트"""
        request = ExplainRequest(query="Explain this code")
        
        assert request.query == "Explain this code"
        assert request.search_results is None
        assert request.include_context is True
        assert request.language_preference == "korean"


class TestExplainResponse:
    """코드 설명 응답 스키마 테스트"""
    
    def test_valid_explain_response(self):
        """유효한 코드 설명 응답 테스트"""
        response = ExplainResponse(
            query="Explain this code",
            explanation="This code does...",
            context_used=["context1", "context2"],
            processing_time_ms=500,
            confidence_score=0.9,
            metadata={"model": "gpt-4"}
        )
        
        assert response.query == "Explain this code"
        assert response.explanation == "This code does..."
        assert response.context_used == ["context1", "context2"]
        assert response.processing_time_ms == 500
        assert response.confidence_score == 0.9
        assert response.metadata == {"model": "gpt-4"}
    
    def test_explain_response_with_defaults(self):
        """기본값이 설정된 코드 설명 응답 테스트"""
        response = ExplainResponse(
            query="Explain this code",
            explanation="This code does..."
        )
        
        assert response.query == "Explain this code"
        assert response.explanation == "This code does..."
        assert response.context_used == []
        assert response.processing_time_ms == 0
        assert response.confidence_score == 0.0
        assert response.metadata == {} 