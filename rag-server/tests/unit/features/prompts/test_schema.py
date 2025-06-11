import pytest
from pydantic import ValidationError
from app.features.prompts.schema import PromptTemplate, PromptRequest, PromptResponse, PromptCategory

def test_prompt_template_should_validate_required_fields():
    """프롬프트 템플릿이 필수 필드를 검증해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        PromptTemplate()  # name 필드 누락
    
    # Valid template
    template = PromptTemplate(
        name="python_system",
        category="system",
        language="python",
        template="You are a Python expert."
    )
    assert template.name == "python_system"
    assert template.version == 1  # 기본값
    assert template.is_active == True  # 기본값

def test_prompt_request_should_validate_parameters():
    """프롬프트 요청이 매개변수를 검증해야 함"""
    # Given & When & Then
    request = PromptRequest(
        template_name="python_system",
        parameters={"language": "python", "include_tests": True}
    )
    assert request.template_name == "python_system"
    assert request.parameters["language"] == "python"

def test_prompt_category_should_have_valid_enum_values():
    """프롬프트 카테고리가 유효한 enum 값을 가져야 함"""
    # Given & When & Then
    assert PromptCategory.SYSTEM == "system"
    assert PromptCategory.USER == "user"
    assert PromptCategory.CONTEXT == "context"
    assert PromptCategory.TEST == "test"

def test_prompt_response_should_include_rendered_content():
    """프롬프트 응답이 렌더링된 내용을 포함해야 함"""
    # Given & When & Then
    response = PromptResponse(
        rendered_prompt="You are a Python expert.",
        template_used="python_system",
        version=1,
        parameters={"language": "python"}
    )
    assert response.rendered_prompt == "You are a Python expert."
    assert response.template_used == "python_system"
    assert response.version == 1 