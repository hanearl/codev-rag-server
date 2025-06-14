"""
하이브리드 인덱싱 API 라우터

AST 파싱, 문서 빌드, 벡터/BM25 인덱싱 기능을 REST API로 제공
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import List, Dict, Any
import logging

from .service import hybrid_indexing_service
from .schema import (
    ParseRequest, ParseResponse, ParseFileResponse,
    DocumentBuildRequest, DocumentBuildResponse,
    IndexingRequest, IndexingResponse, IndexStatsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/indexing", tags=["indexing"])


@router.post("/parse", response_model=ParseResponse)
async def parse_code(request: ParseRequest):
    """
    코드 파싱 API
    
    주어진 코드를 AST로 파싱하여 메서드, 클래스, 함수, 임포트 등을 추출합니다.
    """
    try:
        result = await hybrid_indexing_service.parse_code(request)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"코드 파싱 실패: {e}")
        raise HTTPException(status_code=500, detail=f"코드 파싱 중 오류가 발생했습니다: {str(e)}")


@router.post("/parse/files", response_model=List[ParseFileResponse])
async def parse_files(
    files: List[UploadFile] = File(...),
    language: str = Form(...)
):
    """
    여러 파일 일괄 파싱 API
    
    업로드된 여러 파일을 일괄적으로 파싱합니다.
    """
    try:
        # 파일 읽기
        file_contents = []
        for file in files:
            content = await file.read()
            file_contents.append((file.filename, content))
        
        results = await hybrid_indexing_service.parse_files(file_contents, language)
        return results
    except Exception as e:
        logger.error(f"파일 파싱 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 파싱 중 오류가 발생했습니다: {str(e)}")


@router.post("/documents/build", response_model=DocumentBuildResponse)
async def build_documents(request: DocumentBuildRequest):
    """
    문서 빌드 API
    
    파싱된 AST 정보를 기반으로 문서를 빌드합니다.
    """
    try:
        result = await hybrid_indexing_service.build_documents(request)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"문서 빌드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문서 빌드 중 오류가 발생했습니다: {str(e)}")


@router.post("/vector/index", response_model=IndexingResponse)
async def create_vector_index(request: IndexingRequest):
    """
    벡터 인덱스 생성 API
    
    문서들을 벡터화하여 벡터 데이터베이스에 인덱싱합니다.
    """
    try:
        result = await hybrid_indexing_service.create_vector_index(request)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"벡터 인덱싱 실패: {e}")
        raise HTTPException(status_code=500, detail=f"벡터 인덱싱 중 오류가 발생했습니다: {str(e)}")


@router.post("/bm25/index", response_model=IndexingResponse)
async def create_bm25_index(request: IndexingRequest):
    """
    BM25 인덱스 생성 API
    
    문서들을 BM25 알고리즘으로 인덱싱합니다.
    """
    try:
        result = await hybrid_indexing_service.create_bm25_index(request)
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"BM25 인덱싱 실패: {e}")
        raise HTTPException(status_code=500, detail=f"BM25 인덱싱 중 오류가 발생했습니다: {str(e)}")


@router.get("/stats")
async def get_index_stats():
    """
    인덱스 통계 조회
    
    벡터 인덱스와 BM25 인덱스의 통계 정보를 반환합니다.
    """
    try:
        result = await hybrid_indexing_service.get_stats()
        return result
    except Exception as e:
        logger.error(f"인덱스 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"인덱스 통계 조회 중 오류가 발생했습니다: {str(e)}")


@router.delete("/vector/{collection_name}")
async def delete_vector_collection(collection_name: str):
    """
    벡터 컬렉션 삭제 API
    
    지정된 벡터 컬렉션을 삭제합니다.
    """
    try:
        result = await hybrid_indexing_service.delete_vector_collection(collection_name)
        return result
    except Exception as e:
        logger.error(f"벡터 컬렉션 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"벡터 컬렉션 삭제 중 오류가 발생했습니다: {str(e)}")


@router.delete("/bm25/{index_name}")
async def delete_bm25_index(index_name: str):
    """
    BM25 인덱스 삭제 API
    
    지정된 BM25 인덱스를 삭제합니다.
    """
    try:
        result = await hybrid_indexing_service.delete_bm25_index(index_name)
        return result
    except Exception as e:
        logger.error(f"BM25 인덱스 삭제 실패: {e}")
        raise HTTPException(status_code=500, detail=f"BM25 인덱스 삭제 중 오류가 발생했습니다: {str(e)}")


@router.get("/health")
async def health_check():
    """
    인덱싱 서비스 헬스체크 API
    
    인덱싱 서비스 및 관련 컴포넌트들의 상태를 확인합니다.
    """
    try:
        result = await hybrid_indexing_service.health_check()
        status_code = 200 if result["status"] == "healthy" else 503
        return result
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return {
            "status": "unhealthy",
            "service": "indexing",
            "error": str(e)
        } 