import pytest
from unittest.mock import Mock, AsyncMock
from app.features.generation.service import GenerationService
from app.features.generation.schema import GenerationRequest, GenerationResponse, CodeContext, ValidationResult
from app.features.search.schema import SearchResult, SearchResponse

@pytest.fixture
def mock_search_service():
    service = Mock()
    service.search_code = AsyncMock()
    return service

@pytest.fixture
def mock_generator():
    generator = Mock()
    generator.generate_code = AsyncMock()
    return generator

@pytest.fixture
def mock_validator():
    validator = Mock()
    validator.validate_python_code = Mock()
    validator.validate_javascript_code = Mock()
    return validator

@pytest.mark.asyncio
async def test_generation_service_should_generate_code_with_context(
    mock_search_service, mock_generator, mock_validator
):
    """생성 서비스가 컨텍스트를 사용하여 코드를 생성해야 함"""
    # Given
    service = GenerationService(mock_search_service, mock_generator, mock_validator)
    
    # Mock 검색 결과 (기존 SearchResult 스키마 사용)
    mock_search_results = [
        SearchResult(
            id="1", file_path="test.py", function_name="test_func",
            code_content="def test_func(): pass", code_type="function",
            language="python", line_start=1, line_end=1,
            keywords=["test"], vector_score=0.9,
            keyword_score=0.8, combined_score=0.85
        )
    ]
    
    mock_search_response = SearchResponse(
        query="Create a function",
        results=mock_search_results,
        total_results=1,
        search_time_ms=100,
        vector_results_count=1,
        keyword_results_count=1,
        search_method="weighted"
    )
    mock_search_service.search_code.return_value = mock_search_response
    
    # Mock 생성 결과
    mock_generation_response = GenerationResponse(
        query="Create a function",
        generated_code="def new_func(): return 'hello'",
        contexts_used=[],
        generation_time_ms=500,
        model_used="gpt-4o-mini",
        language="python",
        tokens_used=100,
        search_results_count=1
    )
    mock_generator.generate_code.return_value = mock_generation_response
    
    # Mock 검증 결과
    mock_validator.validate_python_code.return_value = ValidationResult(
        is_valid=True,
        syntax_errors=[],
        warnings=[],
        suggestions=[]
    )
    
    request = GenerationRequest(query="Create a function")
    
    # When
    result = await service.generate_code(request)
    
    # Then
    assert result.generated_code == "def new_func(): return 'hello'"
    assert result.query == "Create a function"
    mock_search_service.search_code.assert_called_once()
    mock_generator.generate_code.assert_called_once()
    mock_validator.validate_python_code.assert_called_once()

@pytest.mark.asyncio
async def test_generation_service_should_handle_invalid_code(
    mock_search_service, mock_generator, mock_validator
):
    """생성 서비스가 유효하지 않은 코드를 처리해야 함"""
    # Given
    service = GenerationService(mock_search_service, mock_generator, mock_validator)
    
    mock_search_service.search_code.return_value = SearchResponse(
        query="test", results=[], total_results=0,
        search_time_ms=10, vector_results_count=0,
        keyword_results_count=0, search_method="weighted"
    )
    
    mock_generator.generate_code.return_value = GenerationResponse(
        query="test", generated_code="def invalid_func(", contexts_used=[],
        generation_time_ms=100, model_used="gpt-4o-mini", language="python",
        tokens_used=50, search_results_count=0
    )
    
    # Mock 검증 실패
    mock_validator.validate_python_code.return_value = ValidationResult(
        is_valid=False,
        syntax_errors=["구문 오류: 잘못된 구문"],
        warnings=[], suggestions=[]
    )
    
    request = GenerationRequest(query="test")
    
    # When & Then
    with pytest.raises(ValueError, match="생성된 코드에 구문 오류가 있습니다"):
        await service.generate_code(request)

@pytest.mark.asyncio
async def test_generation_service_should_convert_search_results_to_contexts(
    mock_search_service, mock_generator, mock_validator
):
    """생성 서비스가 검색 결과를 컨텍스트로 변환해야 함"""
    # Given
    service = GenerationService(mock_search_service, mock_generator, mock_validator)
    
    mock_search_results = [
        SearchResult(
            id="1", file_path="utils.py", function_name="calculate",
            code_content="def calculate(x): return x * 2", code_type="function",
            language="python", line_start=5, line_end=6,
            keywords=["calculate"], vector_score=0.95,
            keyword_score=0.85, combined_score=0.90
        )
    ]
    
    mock_search_service.search_code.return_value = SearchResponse(
        query="test", results=mock_search_results, total_results=1,
        search_time_ms=50, vector_results_count=1,
        keyword_results_count=1, search_method="weighted"
    )
    
    # 생성된 컨텍스트가 올바른지 확인하기 위한 설정
    def check_contexts(request, contexts):
        assert len(contexts) == 1
        assert contexts[0].function_name == "calculate"
        assert contexts[0].code_content == "def calculate(x): return x * 2"
        assert contexts[0].file_path == "utils.py"
        assert contexts[0].relevance_score == 0.90
        return GenerationResponse(
            query="test", generated_code="def test(): pass", contexts_used=contexts,
            generation_time_ms=100, model_used="gpt-4o-mini", language="python",
            tokens_used=50, search_results_count=1
        )
    
    mock_generator.generate_code.side_effect = check_contexts
    mock_validator.validate_python_code.return_value = ValidationResult(
        is_valid=True, syntax_errors=[], warnings=[], suggestions=[]
    )
    
    request = GenerationRequest(query="test")
    
    # When
    await service.generate_code(request)
    
    # Then - 컨텍스트 변환이 올바르게 수행됨 