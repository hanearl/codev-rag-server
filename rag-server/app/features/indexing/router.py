from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from pydantic import ValidationError
from .service import IndexingService
from .schema import (
    IndexingRequest, IndexingResponse, BatchIndexingRequest, BatchIndexingResponse,
    ChunkQueryRequest, ChunkQueryResponse, JsonIndexingRequest, JsonBatchIndexingRequest
)
from app.core.dependencies import get_indexing_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/indexing", tags=["indexing"])

@router.post("/file", response_model=IndexingResponse)
async def index_file(
    request: IndexingRequest,
    service: IndexingService = Depends(get_indexing_service)
) -> IndexingResponse:
    """단일 파일 인덱싱"""
    try:
        return await service.index_file(request)
    except FileNotFoundError as e:
        logger.warning(f"파일 없음: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"인덱싱 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인덱싱 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/batch", response_model=BatchIndexingResponse)
async def index_batch(
    request: BatchIndexingRequest,
    service: IndexingService = Depends(get_indexing_service)
) -> BatchIndexingResponse:
    """배치 파일 인덱싱"""
    try:
        return await service.index_batch(request)
    except Exception as e:
        logger.error(f"배치 인덱싱 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"배치 인덱싱 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/chunks", response_model=ChunkQueryResponse)
async def query_chunks(
    file_path: Optional[str] = None,
    code_type: Optional[str] = None,
    language: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    service: IndexingService = Depends(get_indexing_service)
) -> ChunkQueryResponse:
    """인덱싱된 코드 청크 조회"""
    try:
        request = ChunkQueryRequest(
            file_path=file_path,
            code_type=code_type,
            language=language,
            keyword=keyword,
            page=page,
            size=size
        )
        return await service.query_chunks(request)
    except ValidationError as e:
        logger.warning(f"청크 조회 파라미터 검증 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"청크 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"청크 조회 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("/json", response_model=IndexingResponse, status_code=201)
async def index_from_json(
    request: JsonIndexingRequest,
    service: IndexingService = Depends(get_indexing_service)
) -> IndexingResponse:
    """JSON 분석 데이터를 통한 단일 파일 인덱싱
    
    - **analysis_data**: 분석된 코드 데이터 (JSON 형식)
    - **force_update**: 기존 데이터 강제 업데이트 여부
    """
    try:
        return await service.index_from_json(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"JSON 인덱싱 중 오류가 발생했습니다: {e}")
        raise HTTPException(status_code=500, detail=f"인덱싱 중 오류가 발생했습니다: {e}")


@router.post("/json/batch", response_model=BatchIndexingResponse, status_code=201)
async def index_batch_from_json(
    request: JsonBatchIndexingRequest,
    service: IndexingService = Depends(get_indexing_service)
) -> BatchIndexingResponse:
    """JSON 분석 데이터를 통한 배치 파일 인덱싱
    
    - **analysis_data_list**: 분석된 코드 데이터 목록
    - **force_update**: 기존 데이터 강제 업데이트 여부
    """
    try:
        return await service.index_batch_from_json(request)
    except Exception as e:
        logger.error(f"배치 JSON 인덱싱 중 오류가 발생했습니다: {e}")
        raise HTTPException(status_code=500, detail=f"배치 인덱싱 중 오류가 발생했습니다: {e}")


@router.get("/health")
async def health_check():
    """인덱싱 서비스 헬스체크"""
    return {"status": "healthy", "service": "indexing"} 