from typing import List
from .model import EmbeddingModel
from .schema import (
    EmbeddingRequest, EmbeddingResponse,
    BulkEmbeddingRequest, BulkEmbeddingResponse
)


class EmbeddingService:
    def __init__(self, embedding_model: EmbeddingModel):
        self.embedding_model = embedding_model
    
    def embed_single(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """단일 텍스트 임베딩"""
        embedding = self.embedding_model.encode(request.text)
        return EmbeddingResponse(
            text=request.text,
            embedding=embedding,
            model=self.embedding_model.model_name
        )
    
    def embed_bulk(self, request: BulkEmbeddingRequest) -> BulkEmbeddingResponse:
        """벌크 텍스트 임베딩"""
        embeddings = self.embedding_model.encode(request.texts)
        
        embedding_responses = []
        for text, embedding in zip(request.texts, embeddings):
            embedding_responses.append(EmbeddingResponse(
                text=text,
                embedding=embedding,
                model=self.embedding_model.model_name
            ))
        
        return BulkEmbeddingResponse(
            embeddings=embedding_responses,
            count=len(embedding_responses)
        ) 