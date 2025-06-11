import pytest
from unittest.mock import Mock, AsyncMock
from app.features.prompts.service import PromptService
from app.features.prompts.schema import PromptTemplate, PromptRequest, PromptResponse, PromptCategory

@pytest.fixture
def mock_manager():
    manager = Mock()
    manager.get_system_prompt = Mock()
    manager.get_user_prompt = Mock()
    return manager

@pytest.fixture
def mock_repository():
    repo = Mock()
    repo.get_template_by_name = Mock()
    repo.save_template = Mock()
    repo.get_all_templates = Mock()
    return repo

@pytest.fixture
def prompt_service(mock_manager, mock_repository):
    return PromptService(mock_manager, mock_repository)

def test_prompt_service_should_generate_prompt_response(prompt_service, mock_manager):
    """프롬프트 서비스가 프롬프트 응답을 생성해야 함"""
    # Given
    request = PromptRequest(
        template_name="python_system",
        parameters={"language": "python", "include_tests": True}
    )
    
    mock_manager.get_system_prompt.return_value = "You are a Python expert. Include test code."
    
    # When
    response = prompt_service.generate_prompt(request)
    
    # Then
    assert isinstance(response, PromptResponse)
    assert response.rendered_prompt == "You are a Python expert. Include test code."
    assert response.template_used == "python_system"
    assert response.parameters == {"language": "python", "include_tests": True}
    mock_manager.get_system_prompt.assert_called_once()

def test_prompt_service_should_create_template(prompt_service, mock_repository):
    """프롬프트 서비스가 템플릿을 생성해야 함"""
    # Given
    template = PromptTemplate(
        name="custom_template",
        category=PromptCategory.SYSTEM,
        language="python",
        template="Custom template content"
    )
    
    mock_repository.save_template.return_value = template
    
    # When
    result = prompt_service.create_template(template)
    
    # Then
    assert result == template
    mock_repository.save_template.assert_called_once_with(template)

def test_prompt_service_should_get_template_by_name(prompt_service, mock_repository):
    """프롬프트 서비스가 이름으로 템플릿을 조회해야 함"""
    # Given
    template = PromptTemplate(
        name="test_template",
        category=PromptCategory.SYSTEM,
        language="python",
        template="Test template"
    )
    
    mock_repository.get_template_by_name.return_value = template
    
    # When
    result = prompt_service.get_template("test_template")
    
    # Then
    assert result == template
    mock_repository.get_template_by_name.assert_called_once_with("test_template")

def test_prompt_service_should_list_all_templates(prompt_service, mock_repository):
    """프롬프트 서비스가 모든 템플릿을 조회해야 함"""
    # Given
    templates = [
        PromptTemplate(name="template1", category=PromptCategory.SYSTEM, language="python", template="content1"),
        PromptTemplate(name="template2", category=PromptCategory.USER, language="javascript", template="content2")
    ]
    
    mock_repository.get_all_templates.return_value = templates
    
    # When
    result = prompt_service.list_templates()
    
    # Then
    assert result == templates
    assert len(result) == 2
    mock_repository.get_all_templates.assert_called_once() 