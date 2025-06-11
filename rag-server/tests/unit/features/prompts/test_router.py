import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from app.features.prompts.router import router
from app.features.prompts.schema import PromptTemplate, PromptRequest, PromptResponse, PromptCategory
from fastapi import FastAPI

@pytest.fixture
def mock_service():
    service = Mock()
    service.generate_prompt = Mock()
    service.create_template = Mock()
    service.get_template = Mock()
    service.list_templates = Mock()
    service.update_template = Mock()
    service.delete_template = Mock()
    return service

@pytest.fixture
def test_app(mock_service):
    app = FastAPI()
    app.include_router(router)
    
    # 의존성 오버라이드
    from app.features.prompts.router import get_prompt_service
    app.dependency_overrides[get_prompt_service] = lambda: mock_service
    
    return app

@pytest.fixture
def client(test_app):
    return TestClient(test_app)

def test_generate_prompt_endpoint(client, mock_service):
    """프롬프트 생성 엔드포인트 테스트"""
    # Given
    request_data = {
        "template_name": "python_system",
        "parameters": {"language": "python", "include_tests": True}
    }
    
    response_data = PromptResponse(
        rendered_prompt="You are a Python expert. Include test code.",
        template_used="python_system",
        version=1,
        parameters={"language": "python", "include_tests": True}
    )
    
    mock_service.generate_prompt.return_value = response_data
    
    # When
    response = client.post("/api/v1/prompts/generate", json=request_data)
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["rendered_prompt"] == "You are a Python expert. Include test code."
    assert data["template_used"] == "python_system"
    mock_service.generate_prompt.assert_called_once()

def test_create_template_endpoint(client, mock_service):
    """템플릿 생성 엔드포인트 테스트"""
    # Given
    template_data = {
        "name": "custom_template",
        "category": "system",
        "language": "python",
        "template": "Custom template content"
    }
    
    created_template = PromptTemplate(**template_data)
    mock_service.create_template.return_value = created_template
    
    # When
    response = client.post("/api/v1/prompts/templates", json=template_data)
    
    # Then
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "custom_template"
    assert data["category"] == "system"
    mock_service.create_template.assert_called_once()

def test_get_template_endpoint(client, mock_service):
    """템플릿 조회 엔드포인트 테스트"""
    # Given
    template = PromptTemplate(
        name="test_template",
        category=PromptCategory.SYSTEM,
        language="python",
        template="Test template"
    )
    
    mock_service.get_template.return_value = template
    
    # When
    response = client.get("/api/v1/prompts/templates/test_template")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test_template"
    mock_service.get_template.assert_called_once_with("test_template")

def test_get_template_not_found(client, mock_service):
    """존재하지 않는 템플릿 조회 테스트"""
    # Given
    mock_service.get_template.return_value = None
    
    # When
    response = client.get("/api/v1/prompts/templates/nonexistent")
    
    # Then
    assert response.status_code == 404

def test_list_templates_endpoint(client, mock_service):
    """템플릿 목록 조회 엔드포인트 테스트"""
    # Given
    templates = [
        PromptTemplate(name="template1", category=PromptCategory.SYSTEM, language="python", template="content1"),
        PromptTemplate(name="template2", category=PromptCategory.USER, language="javascript", template="content2")
    ]
    
    mock_service.list_templates.return_value = templates
    
    # When
    response = client.get("/api/v1/prompts/templates")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "template1"
    assert data[1]["name"] == "template2"
    mock_service.list_templates.assert_called_once() 