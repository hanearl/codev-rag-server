from pydantic import BaseModel
from typing import List


class EmbeddingRequest(BaseModel):
    """단일 텍스트 임베딩 요청"""
    text: str


class EmbeddingResponse(BaseModel):
    """단일 텍스트 임베딩 응답"""
    text: str
    embedding: List[float]
    model: str


class BulkEmbeddingRequest(BaseModel):
    """벌크 텍스트 임베딩 요청"""
    texts: List[str]


class BulkEmbeddingResponse(BaseModel):
    """벌크 텍스트 임베딩 응답"""
    embeddings: List[EmbeddingResponse]
    count: int 