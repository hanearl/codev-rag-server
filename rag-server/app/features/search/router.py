"""
하이브리드 검색 API 라우터

벡터 검색, BM25 검색, 하이브리드 검색 기능을 REST API로 제공
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging

from .service import hybrid_search_service
from .schema import (
    VectorSearchRequest, VectorSearchResponse,
    BM25SearchRequest, BM25SearchResponse,
    HybridSearchRequest, HybridSearchResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.post("/vector", response_model=VectorSearchResponse)
async def vector_search(request: VectorSearchRequest):
    """
    벡터 검색 API
    
    임베딩 기반으로 코드 문서를 검색합니다.
    """
    try:
        result = await hybrid_search_service.vector_search(request)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        return result
    except Exception as e:
        logger.error(f"벡터 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"벡터 검색 실패: {str(e)}")


@router.post("/bm25", response_model=BM25SearchResponse)
async def bm25_search(request: BM25SearchRequest):
    """
    BM25 검색 API
    
    키워드 기반 BM25 알고리즘으로 코드 문서를 검색합니다.
    """
    try:
        result = await hybrid_search_service.bm25_search(request)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        return result
    except Exception as e:
        logger.error(f"BM25 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"BM25 검색 실패: {str(e)}")


@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(request: HybridSearchRequest):
    """
    하이브리드 검색 API
    
    벡터 검색과 BM25 검색을 결합하여 더 정확한 검색 결과를 제공합니다.
    """
    try:
        result = await hybrid_search_service.hybrid_search(request)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        return result
    except Exception as e:
        logger.error(f"하이브리드 검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"하이브리드 검색 실패: {str(e)}")


@router.get("/collections")
async def get_collections():
    """
    벡터 컬렉션 목록 조회 API
    
    사용 가능한 벡터 컬렉션 목록을 반환합니다.
    """
    try:
        result = await hybrid_search_service.get_collections()
        return result
    except Exception as e:
        logger.error(f"컬렉션 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"컬렉션 목록 조회 실패: {str(e)}")


@router.get("/indexes")
async def get_indexes():
    """
    BM25 인덱스 목록 조회 API
    
    사용 가능한 BM25 인덱스 목록을 반환합니다.
    """
    try:
        result = await hybrid_search_service.get_indexes()
        return result
    except Exception as e:
        logger.error(f"인덱스 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"인덱스 목록 조회 실패: {str(e)}")


@router.get("/health")
async def health_check():
    """
    검색 서비스 헬스체크 API
    
    검색 서비스 및 관련 컴포넌트들의 상태를 확인합니다.
    """
    try:
        result = await hybrid_search_service.health_check()
        status_code = 200 if result["status"] == "healthy" else 503
        return result
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return {
            "status": "unhealthy",
            "service": "search",
            "error": str(e)
        } 