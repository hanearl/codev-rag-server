from fastapi import APIRouter, Depends, HTTPException
from app.features.embedding.service import EmbeddingService
from app.features.embedding.schema import (
    EmbeddingRequest, EmbeddingResponse,
    BulkEmbeddingRequest, BulkEmbeddingResponse
)
from app.core.dependencies import get_embedding_service

router = APIRouter(prefix="/embedding", tags=["embedding"])


@router.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "healthy", "service": "embedding-server"}


@router.post("/embed", response_model=EmbeddingResponse)
async def embed_text(
    request: EmbeddingRequest,
    service: EmbeddingService = Depends(get_embedding_service)
):
    """단일 텍스트 임베딩"""
    try:
        return service.embed_single(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"임베딩 생성 실패: {str(e)}")


@router.post("/embed/bulk", response_model=BulkEmbeddingResponse)
async def embed_bulk_texts(
    request: BulkEmbeddingRequest,
    service: EmbeddingService = Depends(get_embedding_service)
):
    """벌크 텍스트 임베딩"""
    try:
        if not request.texts:
            raise HTTPException(status_code=400, detail="텍스트 리스트가 비어있습니다")
        
        return service.embed_bulk(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"벌크 임베딩 생성 실패: {str(e)}") 