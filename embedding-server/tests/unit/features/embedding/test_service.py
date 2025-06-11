import pytest
from unittest.mock import Mock, patch
from app.features.embedding.service import EmbeddingService
from app.features.embedding.schema import EmbeddingRequest, BulkEmbeddingRequest


@pytest.fixture
def mock_embedding_model():
    mock_model = Mock()
    mock_model.model_name = "test-model"
    mock_model.encode.return_value = [0.1, 0.2, 0.3]
    return mock_model


def test_embed_single_text_should_return_embedding(mock_embedding_model):
    """단일 텍스트 임베딩 시 임베딩 벡터를 반환해야 함"""
    # Given
    service = EmbeddingService(mock_embedding_model)
    request = EmbeddingRequest(text="테스트 텍스트")
    
    # When
    result = service.embed_single(request)
    
    # Then
    assert result.embedding == [0.1, 0.2, 0.3]
    assert result.text == "테스트 텍스트"
    assert result.model == "test-model"
    mock_embedding_model.encode.assert_called_once_with("테스트 텍스트")


def test_embed_bulk_texts_should_return_multiple_embeddings(mock_embedding_model):
    """벌크 텍스트 임베딩 시 여러 임베딩 벡터를 반환해야 함"""
    # Given
    service = EmbeddingService(mock_embedding_model)
    mock_embedding_model.encode.return_value = [[0.1, 0.2], [0.3, 0.4]]
    request = BulkEmbeddingRequest(texts=["텍스트1", "텍스트2"])
    
    # When
    result = service.embed_bulk(request)
    
    # Then
    assert len(result.embeddings) == 2
    assert result.embeddings[0].embedding == [0.1, 0.2]
    assert result.embeddings[1].embedding == [0.3, 0.4]
    assert result.embeddings[0].text == "텍스트1"
    assert result.embeddings[1].text == "텍스트2"
    assert result.count == 2
    mock_embedding_model.encode.assert_called_once_with(["텍스트1", "텍스트2"]) 