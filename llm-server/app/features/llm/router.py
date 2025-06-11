from fastapi import APIRouter, Depends, HTTPException
from app.features.llm.service import LLMService
from app.features.llm.schema import (
    ChatCompletionRequest, ChatCompletionResponse,
    CompletionRequest, CompletionResponse
)
from app.core.dependencies import get_llm_service

router = APIRouter(tags=["llm"])


@router.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "healthy", "service": "llm-server"}


@router.get("/v1/models")
async def list_models(service: LLMService = Depends(get_llm_service)):
    """사용 가능한 모델 목록 조회 (vLLM 호환)"""
    return await service.get_models()


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: ChatCompletionRequest,
    service: LLMService = Depends(get_llm_service)
):
    """채팅 완성 생성 (vLLM 호환)"""
    try:
        return await service.create_chat_completion(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"채팅 완성 생성 실패: {str(e)}")


@router.post("/v1/completions", response_model=CompletionResponse)
async def create_completion(
    request: CompletionRequest,
    service: LLMService = Depends(get_llm_service)
):
    """텍스트 완성 생성 (vLLM 호환)"""
    try:
        return await service.create_completion(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"텍스트 완성 생성 실패: {str(e)}")


# OpenAI 호환 엔드포인트 (별칭)
@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion_openai_compat(
    request: ChatCompletionRequest,
    service: LLMService = Depends(get_llm_service)
):
    """채팅 완성 생성 (OpenAI 호환)"""
    return await create_chat_completion(request, service)


@router.post("/completions", response_model=CompletionResponse)
async def create_completion_openai_compat(
    request: CompletionRequest,
    service: LLMService = Depends(get_llm_service)
):
    """텍스트 완성 생성 (OpenAI 호환)"""
    return await create_completion(request, service) 