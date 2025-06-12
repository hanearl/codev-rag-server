import pytest
from pydantic import ValidationError
from app.features.generation.schema import GenerationRequest, GenerationResponse

def test_generation_request_should_validate_required_fields():
    """생성 요청이 필수 필드를 검증해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        GenerationRequest()  # query 필드 누락
    
    # Valid request
    request = GenerationRequest(query="Create a function")
    assert request.query == "Create a function"
    assert request.context_limit == 3  # 기본값
    assert request.language == "python"  # 기본값
    assert request.include_tests == False  # 기본값

def test_generation_request_should_validate_context_limit():
    """생성 요청이 컨텍스트 제한을 검증해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        GenerationRequest(query="test", context_limit=0)  # 최소값 미만
    
    with pytest.raises(ValidationError):
        GenerationRequest(query="test", context_limit=11)  # 최대값 초과

def test_generation_request_should_validate_language():
    """생성 요청이 지원하는 언어를 검증해야 함"""
    # Given & When & Then
    valid_languages = ["python", "javascript", "typescript", "java", "go"]
    
    for lang in valid_languages:
        request = GenerationRequest(query="test", language=lang)
        assert request.language == lang
    
    with pytest.raises(ValidationError):
        GenerationRequest(query="test", language="unsupported") 