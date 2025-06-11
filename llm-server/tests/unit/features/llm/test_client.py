import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.features.llm.client import OpenAIClient
from app.features.llm.schema import ChatCompletionRequest, ChatMessage, Role


@pytest.fixture
def mock_openai_client():
    mock_client = Mock()
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = AsyncMock()
    return mock_client


@pytest.mark.asyncio
async def test_openai_client_should_create_chat_completion(mock_openai_client):
    """OpenAI 클라이언트가 채팅 완성을 생성해야 함"""
    # Given
    client = OpenAIClient("test-api-key")
    client._client = mock_openai_client
    
    mock_response = Mock()
    mock_response.id = "test-id"
    mock_response.object = "chat.completion"
    mock_response.created = 1234567890
    mock_response.model = "gpt-4o-mini"
    mock_response.choices = [Mock()]
    mock_response.choices[0].index = 0
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.role = "assistant"
    mock_response.choices[0].message.content = "테스트 응답"
    mock_response.choices[0].finish_reason = "stop"
    mock_response.usage = Mock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    mock_response.usage.total_tokens = 15
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    request = ChatCompletionRequest(
        messages=[ChatMessage(role=Role.USER, content="안녕하세요")],
        model="gpt-4o-mini"
    )
    
    # When
    response = await client.create_chat_completion(request)
    
    # Then
    assert response.id == "test-id"
    assert response.model == "gpt-4o-mini"
    assert len(response.choices) == 1
    assert response.choices[0].message.content == "테스트 응답"
    mock_openai_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_openai_client_should_handle_api_error():
    """OpenAI 클라이언트가 API 오류를 처리해야 함"""
    # Given
    client = OpenAIClient("test-api-key")
    client._client = mock_openai_client
    
    mock_openai_client.chat.completions.create.side_effect = Exception("API 오류")
    
    request = ChatCompletionRequest(
        messages=[ChatMessage(role=Role.USER, content="안녕하세요")],
        model="gpt-4o-mini"
    )
    
    # When & Then
    with pytest.raises(Exception) as exc_info:
        await client.create_chat_completion(request)
    
    assert "OpenAI API 호출 실패" in str(exc_info.value) 