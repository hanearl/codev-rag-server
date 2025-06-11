import pytest
from unittest.mock import Mock
from app.features.prompts.manager import PromptManager
from app.features.prompts.schema import PromptTemplate, CodeContext, PromptCategory

@pytest.fixture
def mock_repository():
    repo = Mock()
    repo.get_template_by_name = Mock()
    return repo

@pytest.fixture
def prompt_manager(mock_repository):
    return PromptManager(mock_repository)

def test_prompt_manager_should_render_system_prompt(prompt_manager, mock_repository):
    """프롬프트 매니저가 시스템 프롬프트를 렌더링해야 함"""
    # Given
    template = PromptTemplate(
        name="python_system",
        category=PromptCategory.SYSTEM,
        language="python",
        template="You are a {{language}} expert. {{extra_instruction}}"
    )
    mock_repository.get_template_by_name.return_value = template
    
    # When
    result = prompt_manager.get_system_prompt("python", include_tests=True)
    
    # Then
    assert "Python expert" in result
    assert "test" in result.lower()
    mock_repository.get_template_by_name.assert_called_with("python_system")

def test_prompt_manager_should_render_user_prompt_with_context(prompt_manager, mock_repository):
    """프롬프트 매니저가 컨텍스트와 함께 사용자 프롬프트를 렌더링해야 함"""
    # Given
    template = PromptTemplate(
        name="user_with_context",
        category=PromptCategory.USER,
        language="general",
        template="Request: {{query}}\n\nExamples:\n{% for ctx in contexts %}{{ctx.code_content}}\n{% endfor %}"
    )
    mock_repository.get_template_by_name.return_value = template
    
    contexts = [
        CodeContext(
            function_name="test_func",
            code_content="def test(): pass",
            file_path="test.py",
            relevance_score=0.9
        )
    ]
    
    # When
    result = prompt_manager.get_user_prompt("Create a function", contexts)
    
    # Then
    assert "Create a function" in result
    assert "def test(): pass" in result
    mock_repository.get_template_by_name.assert_called_with("user_with_context")

def test_prompt_manager_should_use_default_template_when_not_found(prompt_manager, mock_repository):
    """프롬프트 매니저가 템플릿을 찾지 못할 때 기본 템플릿을 사용해야 함"""
    # Given
    mock_repository.get_template_by_name.return_value = None
    
    # When
    result = prompt_manager.get_system_prompt("python")
    
    # Then
    assert "Python expert" in result
    assert "clean, efficient code" in result

def test_prompt_manager_should_handle_template_rendering_error(prompt_manager, mock_repository):
    """프롬프트 매니저가 템플릿 렌더링 에러를 처리해야 함"""
    # Given
    template = PromptTemplate(
        name="invalid_template",
        category=PromptCategory.SYSTEM,
        language="python",
        template="{% invalid_syntax %}"  # 잘못된 Jinja2 문법
    )
    mock_repository.get_template_by_name.return_value = template
    
    # When & Then
    with pytest.raises(Exception):  # 렌더링 에러 발생 예상
        prompt_manager.get_system_prompt("python") 