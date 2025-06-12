from fastapi import APIRouter, Depends, HTTPException, status
from .service import GenerationService
from .schema import GenerationRequest, GenerationResponse
from app.core.dependencies import get_generation_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/generate", tags=["generation"])

@router.post("/", response_model=GenerationResponse)
async def generate_code(
    request: GenerationRequest,
    service: GenerationService = Depends(get_generation_service)
) -> GenerationResponse:
    """RAG 기반 코드 생성
    
    검색된 관련 코드를 컨텍스트로 활용하여 고품질 코드를 생성합니다.
    """
    try:
        logger.info(f"코드 생성 요청: {request.query} ({request.language})")
        result = await service.generate_code(request)
        logger.info(f"코드 생성 완료: {result.tokens_used} 토큰, {result.generation_time_ms}ms")
        return result
    except ValueError as e:
        logger.error(f"코드 검증 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"코드 생성 중 검증 오류가 발생했습니다: {str(e)}"
        )
    except Exception as e:
        logger.error(f"코드 생성 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"코드 생성 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """생성 서비스 헬스체크"""
    return {
        "status": "healthy",
        "service": "generation-service"
    }

@router.get("/languages")
async def get_supported_languages():
    """지원하는 프로그래밍 언어 목록"""
    return {
        "languages": [
            {"code": "python", "name": "Python", "description": "Python 3.6+"},
            {"code": "javascript", "name": "JavaScript", "description": "ES6+"},
            {"code": "typescript", "name": "TypeScript", "description": "TypeScript 4.0+"},
            {"code": "java", "name": "Java", "description": "Java 11+"},
            {"code": "go", "name": "Go", "description": "Go 1.18+"}
        ]
    } 