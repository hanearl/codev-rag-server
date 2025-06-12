import pytest
from unittest.mock import Mock, AsyncMock
from app.features.search.retriever import HybridRetriever

@pytest.fixture
def mock_embedding_client():
    client = Mock()
    client.embed_single = AsyncMock()
    return client

@pytest.fixture
def mock_vector_client():
    client = Mock()
    client.hybrid_search = Mock()
    return client

@pytest.mark.asyncio
async def test_hybrid_retriever_should_combine_results(
    mock_embedding_client, mock_vector_client
):
    """하이브리드 검색기가 벡터와 키워드 결과를 결합해야 함"""
    # Given
    retriever = HybridRetriever(mock_embedding_client, mock_vector_client)
    
    mock_embedding_client.embed_single.return_value = {
        "embedding": [0.1, 0.2, 0.3]
    }
    
    mock_vector_client.hybrid_search.return_value = [
        {
            "id": "1", 
            "vector_score": 0.9, 
            "keyword_score": 0.7,
            "file_path": "test.py",
            "code_content": "def test(): pass",
            "code_type": "function",
            "language": "python",
            "line_start": 1,
            "line_end": 1,
            "keywords": ["test"]
        }
    ]
    
    # When
    results = await retriever.search(
        query="test function",
        keywords=["test"],
        limit=10,
        collection_name="code_chunks"
    )
    
    # Then
    assert len(results) == 1
    assert results[0]["id"] == "1"
    assert "vector_score" in results[0]
    assert "keyword_score" in results[0]
    mock_embedding_client.embed_single.assert_called_once_with({"text": "test function"})
    mock_vector_client.hybrid_search.assert_called_once()

@pytest.mark.asyncio
async def test_hybrid_retriever_should_handle_empty_results(
    mock_embedding_client, mock_vector_client
):
    """하이브리드 검색기가 빈 결과를 처리해야 함"""
    # Given
    retriever = HybridRetriever(mock_embedding_client, mock_vector_client)
    
    mock_embedding_client.embed_single.return_value = {
        "embedding": [0.1, 0.2, 0.3]
    }
    
    mock_vector_client.hybrid_search.return_value = []
    
    # When
    results = await retriever.search(
        query="non existent query",
        limit=10
    )
    
    # Then
    assert len(results) == 0

@pytest.mark.asyncio
async def test_hybrid_retriever_should_handle_embedding_error(
    mock_embedding_client, mock_vector_client
):
    """하이브리드 검색기가 임베딩 오류를 처리해야 함"""
    # Given
    retriever = HybridRetriever(mock_embedding_client, mock_vector_client)
    
    mock_embedding_client.embed_single.side_effect = Exception("Embedding error")
    
    # When & Then
    with pytest.raises(Exception):
        await retriever.search(query="test query") 