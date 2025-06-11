import pytest
from unittest.mock import Mock, AsyncMock
from app.features.llm.service import LLMService
from app.features.llm.schema import (
    ChatCompletionRequest, ChatCompletionResponse, ChatMessage, Role,
    CompletionRequest, CompletionResponse
)


@pytest.fixture
def mock_openai_client():
    mock_client = Mock()
    mock_client.create_chat_completion = AsyncMock()
    mock_client.create_completion = AsyncMock()
    return mock_client


@pytest.mark.asyncio
async def test_llm_service_should_create_chat_completion(mock_openai_client):
    """LLM 서비스가 채팅 완성을 생성해야 함"""
    # Given
    service = LLMService(mock_openai_client)
    mock_response = ChatCompletionResponse(
        id="test-id",
        object="chat.completion",
        created=1234567890,
        model="gpt-4o-mini",
        choices=[],
        usage=None
    )
    mock_openai_client.create_chat_completion.return_value = mock_response
    
    request = ChatCompletionRequest(
        messages=[ChatMessage(role=Role.USER, content="안녕하세요")],
        model="gpt-4o-mini"
    )
    
    # When
    response = await service.create_chat_completion(request)
    
    # Then
    assert response.model == "gpt-4o-mini"
    assert response.id == "test-id"
    mock_openai_client.create_chat_completion.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_llm_service_should_create_completion(mock_openai_client):
    """LLM 서비스가 텍스트 완성을 생성해야 함"""
    # Given
    service = LLMService(mock_openai_client)
    mock_response = CompletionResponse(
        id="test-id",
        object="text_completion",
        created=1234567890,
        model="gpt-4o-mini",
        choices=[],
        usage=None
    )
    mock_openai_client.create_completion.return_value = mock_response
    
    request = CompletionRequest(
        prompt="테스트 프롬프트",
        model="gpt-4o-mini"
    )
    
    # When
    response = await service.create_completion(request)
    
    # Then
    assert response.model == "gpt-4o-mini"
    assert response.id == "test-id"
    mock_openai_client.create_completion.assert_called_once_with(request)


@pytest.mark.asyncio
async def test_llm_service_should_handle_service_error(mock_openai_client):
    """LLM 서비스가 서비스 오류를 처리해야 함"""
    # Given
    service = LLMService(mock_openai_client)
    mock_openai_client.create_chat_completion.side_effect = Exception("서비스 오류")
    
    request = ChatCompletionRequest(
        messages=[ChatMessage(role=Role.USER, content="안녕하세요")],
        model="gpt-4o-mini"
    )
    
    # When & Then
    with pytest.raises(Exception) as exc_info:
        await service.create_chat_completion(request)
    
    assert "LLM 서비스 오류" in str(exc_info.value) 