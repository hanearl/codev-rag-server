import pytest
import torch
from app.features.embedding.model import EmbeddingModel


def test_embedding_model_should_load_model():
    """임베딩 모델이 정상적으로 로드되어야 함"""
    # Given
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    
    # When
    embedding_model = EmbeddingModel(model_name)
    
    # Then
    assert embedding_model.model is not None
    assert embedding_model.tokenizer is not None


def test_encode_should_return_embedding_vector():
    """텍스트 인코딩 시 임베딩 벡터를 반환해야 함"""
    # Given
    model = EmbeddingModel("sentence-transformers/all-MiniLM-L6-v2")
    text = "테스트 텍스트입니다"
    
    # When
    embedding = model.encode(text)
    
    # Then
    assert isinstance(embedding, list)
    assert len(embedding) == 384  # all-MiniLM-L6-v2 차원
    assert all(isinstance(x, float) for x in embedding)


def test_encode_multiple_texts_should_return_multiple_embeddings():
    """여러 텍스트 인코딩 시 여러 임베딩 벡터를 반환해야 함"""
    # Given
    model = EmbeddingModel("sentence-transformers/all-MiniLM-L6-v2")
    texts = ["첫 번째 텍스트", "두 번째 텍스트"]
    
    # When
    embeddings = model.encode(texts)
    
    # Then
    assert isinstance(embeddings, list)
    assert len(embeddings) == 2
    assert all(isinstance(emb, list) for emb in embeddings)
    assert all(len(emb) == 384 for emb in embeddings) 