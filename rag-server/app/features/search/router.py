from fastapi import APIRouter, Depends, HTTPException, status
from .service import SearchService
from .schema import SearchRequest, SearchResponse
from app.core.dependencies import get_search_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["search"])

@router.post("/", response_model=SearchResponse)
async def search_code(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service)
) -> SearchResponse:
    """코드 하이브리드 검색
    
    벡터 검색과 키워드 검색을 결합하여 관련 코드를 찾습니다.
    """
    try:
        logger.info(f"검색 요청: {request.query}")
        result = await service.search_code(request)
        logger.info(f"검색 완료: {result.total_results}개 결과, {result.search_time_ms}ms")
        return result
    except Exception as e:
        logger.error(f"검색 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"검색 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """검색 서비스 헬스체크"""
    return {
        "status": "healthy",
        "service": "search-service"
    } 