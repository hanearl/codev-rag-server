from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from .schema import PromptTemplate, PromptRequest, PromptResponse
from .service import PromptService
from .manager import PromptManager
from .repository import PromptRepository

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])

def get_prompt_service() -> PromptService:
    """프롬프트 서비스 의존성 주입"""
    repository = PromptRepository()
    manager = PromptManager(repository)
    return PromptService(manager, repository)

@router.post("/generate", response_model=PromptResponse)
async def generate_prompt(
    request: PromptRequest,
    service: PromptService = Depends(get_prompt_service)
) -> PromptResponse:
    """
    프롬프트 생성
    
    - **template_name**: 사용할 템플릿 이름
    - **parameters**: 템플릿 매개변수
    - **language**: 언어 오버라이드 (선택사항)
    """
    try:
        return service.generate_prompt(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"프롬프트 생성 실패: {str(e)}"
        )

@router.post("/templates", response_model=PromptTemplate, status_code=201)
async def create_template(
    template: PromptTemplate,
    service: PromptService = Depends(get_prompt_service)
) -> PromptTemplate:
    """
    새 프롬프트 템플릿 생성
    
    - **name**: 템플릿 이름 (유니크)
    - **category**: 템플릿 카테고리
    - **language**: 대상 언어
    - **template**: Jinja2 템플릿 내용
    """
    try:
        return service.create_template(template)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"템플릿 생성 실패: {str(e)}"
        )

@router.get("/templates/{template_name}", response_model=PromptTemplate)
async def get_template(
    template_name: str,
    service: PromptService = Depends(get_prompt_service)
) -> PromptTemplate:
    """
    템플릿 조회
    
    - **template_name**: 조회할 템플릿 이름
    """
    template = service.get_template(template_name)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"템플릿을 찾을 수 없습니다: {template_name}"
        )
    return template

@router.get("/templates", response_model=List[PromptTemplate])
async def list_templates(
    service: PromptService = Depends(get_prompt_service)
) -> List[PromptTemplate]:
    """
    모든 템플릿 목록 조회
    """
    return service.list_templates()

@router.put("/templates/{template_name}", response_model=PromptTemplate)
async def update_template(
    template_name: str,
    template: PromptTemplate,
    service: PromptService = Depends(get_prompt_service)
) -> PromptTemplate:
    """
    템플릿 업데이트
    
    - **template_name**: 업데이트할 템플릿 이름
    """
    updated = service.update_template(template_name, template)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"템플릿을 찾을 수 없습니다: {template_name}"
        )
    return updated

@router.delete("/templates/{template_name}")
async def delete_template(
    template_name: str,
    service: PromptService = Depends(get_prompt_service)
):
    """
    템플릿 삭제
    
    - **template_name**: 삭제할 템플릿 이름
    """
    success = service.delete_template(template_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"템플릿을 찾을 수 없습니다: {template_name}"
        )
    return {"message": f"템플릿이 삭제되었습니다: {template_name}"} 