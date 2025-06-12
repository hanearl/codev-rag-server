import pytest
from unittest.mock import Mock, patch
from app.features.generation.prompt_manager import PromptManager
from app.features.generation.schema import CodeContext

@pytest.fixture
def mock_prompt_repository():
    """Mock 프롬프트 리포지토리"""
    repository = Mock()
    repository.get_template_by_name = Mock(return_value=None)  # 템플릿 없음 시뮬레이션
    return repository

@pytest.fixture
def prompt_manager(mock_prompt_repository):
    """기존 prompts 모듈과 연동된 프롬프트 매니저"""
    return PromptManager(repository=mock_prompt_repository)

def test_prompt_manager_should_get_system_prompt_for_python(prompt_manager):
    """프롬프트 매니저가 Python용 시스템 프롬프트를 반환해야 함"""
    # When (기존 템플릿 시스템이 동작하지 않을 때 fallback 테스트)
    system_prompt = prompt_manager.get_system_prompt("python", False)
    
    # Then
    assert "PYTHON" in system_prompt  # 대문자로 변환됨
    assert "전문가" in system_prompt
    assert "코딩 표준" in system_prompt

def test_prompt_manager_should_get_system_prompt_with_tests(prompt_manager):
    """프롬프트 매니저가 테스트 포함 시스템 프롬프트를 반환해야 함"""
    # When
    system_prompt = prompt_manager.get_system_prompt("python", True)
    
    # Then
    assert "테스트" in system_prompt
    assert "pytest" in system_prompt

def test_prompt_manager_should_create_user_prompt_with_context(prompt_manager):
    """프롬프트 매니저가 컨텍스트가 포함된 사용자 프롬프트를 생성해야 함"""
    # Given
    query = "Create a function to calculate sum"
    contexts = [
        CodeContext(
            function_name="add_numbers",
            code_content="def add_numbers(a, b): return a + b",
            file_path="math.py",
            relevance_score=0.9,
            code_type="function",
            language="python"
        )
    ]
    
    # When
    user_prompt = prompt_manager.get_user_prompt(query, contexts, "python")
    
    # Then
    assert query in user_prompt
    assert "add_numbers" in user_prompt
    assert "참고 코드" in user_prompt

def test_prompt_manager_should_create_user_prompt_without_context(prompt_manager):
    """프롬프트 매니저가 컨텍스트 없이도 사용자 프롬프트를 생성해야 함"""
    # Given
    query = "Create a new function"
    
    # When
    user_prompt = prompt_manager.get_user_prompt(query, [], "python")
    
    # Then
    assert query in user_prompt
    assert "참고할 코드" not in user_prompt

@patch('app.features.prompts.manager.PromptManager')
def test_prompt_manager_should_use_existing_templates_when_available(mock_base_manager_class, mock_prompt_repository):
    """기존 템플릿이 있을 때 해당 템플릿을 사용해야 함"""
    # Given
    mock_base_manager = Mock()
    mock_base_manager.get_system_prompt.return_value = "Expert Python template from database"
    mock_base_manager_class.return_value = mock_base_manager
    
    prompt_manager = PromptManager(repository=mock_prompt_repository)
    
    # When
    result = prompt_manager.get_system_prompt("python", False)
    
    # Then
    assert result == "Expert Python template from database"
    mock_base_manager.get_system_prompt.assert_called_once_with("python", False)

def test_prompt_manager_should_convert_contexts_correctly(prompt_manager):
    """CodeContext를 PromptCodeContext로 올바르게 변환해야 함"""
    # Given
    contexts = [
        CodeContext(
            function_name="test_func",
            code_content="def test(): pass",
            file_path="test.py",
            relevance_score=0.8,
            code_type="function",
            language="python"
        )
    ]
    
    # When
    converted_contexts = prompt_manager._convert_contexts(contexts)
    
    # Then
    assert len(converted_contexts) == 1
    assert converted_contexts[0].function_name == "test_func"
    assert converted_contexts[0].code_content == "def test(): pass"
    assert converted_contexts[0].file_path == "test.py"
    assert converted_contexts[0].relevance_score == 0.8 