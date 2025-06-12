import pytest
from unittest.mock import Mock, AsyncMock
from app.features.generation.generator import CodeGenerator
from app.features.generation.schema import GenerationRequest, CodeContext

@pytest.fixture
def mock_llm_client():
    client = Mock()
    client.chat_completion = AsyncMock()
    return client

@pytest.fixture
def mock_prompt_manager():
    manager = Mock()
    manager.get_system_prompt = Mock()
    manager.get_user_prompt = Mock()
    return manager

@pytest.mark.asyncio
async def test_code_generator_should_generate_code_with_context(
    mock_llm_client, mock_prompt_manager
):
    """코드 생성기가 컨텍스트를 사용하여 코드를 생성해야 함"""
    # Given
    generator = CodeGenerator(mock_llm_client, mock_prompt_manager)
    
    mock_prompt_manager.get_system_prompt.return_value = "You are a Python expert."
    mock_prompt_manager.get_user_prompt.return_value = "Create a function to calculate sum"
    
    mock_llm_client.chat_completion.return_value = {
        "choices": [
            {
                "message": {
                    "content": "def calculate_sum(a, b):\n    \"\"\"두 수의 합을 계산합니다.\"\"\"\n    return a + b"
                }
            }
        ],
        "usage": {
            "total_tokens": 150
        },
        "model": "gpt-4o-mini"
    }
    
    request = GenerationRequest(query="Create a function to calculate sum")
    contexts = [
        CodeContext(
            function_name="add_numbers",
            code_content="def add_numbers(x, y): return x + y",
            file_path="math_utils.py",
            relevance_score=0.9,
            code_type="function",
            language="python"
        )
    ]
    
    # When
    result = await generator.generate_code(request, contexts)
    
    # Then
    assert result.generated_code == "def calculate_sum(a, b):\n    \"\"\"두 수의 합을 계산합니다.\"\"\"\n    return a + b"
    assert result.tokens_used == 150
    assert result.model_used == "gpt-4o-mini"
    mock_llm_client.chat_completion.assert_called_once()

@pytest.mark.asyncio
async def test_code_generator_should_handle_different_languages(
    mock_llm_client, mock_prompt_manager
):
    """코드 생성기가 다양한 언어를 처리해야 함"""
    # Given
    generator = CodeGenerator(mock_llm_client, mock_prompt_manager)
    
    mock_prompt_manager.get_system_prompt.return_value = "You are a JavaScript expert."
    mock_prompt_manager.get_user_prompt.return_value = "Create a function"
    
    mock_llm_client.chat_completion.return_value = {
        "choices": [{"message": {"content": "function test() { return 'hello'; }"}}],
        "usage": {"total_tokens": 100},
        "model": "gpt-4o-mini"
    }
    
    request = GenerationRequest(query="Create a function", language="javascript")
    
    # When
    result = await generator.generate_code(request, [])
    
    # Then
    assert result.language == "javascript"
    mock_prompt_manager.get_system_prompt.assert_called_with("javascript", False) 