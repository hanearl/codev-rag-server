from typing import List, Optional
from .schema import PromptTemplate, PromptRequest, PromptResponse
from .manager import PromptManager
from .repository import PromptRepository
import logging

logger = logging.getLogger(__name__)

class PromptService:
    def __init__(self, manager: PromptManager, repository: PromptRepository):
        self.manager = manager
        self.repository = repository
    
    def generate_prompt(self, request: PromptRequest) -> PromptResponse:
        """프롬프트 요청에 대한 응답 생성"""
        try:
            # 템플릿 이름에서 언어와 카테고리 추출
            template_name = request.template_name
            language = request.language or self._extract_language_from_template_name(template_name)
            
            # 매개변수 준비
            params = request.parameters.copy()
            if 'language' not in params:
                params['language'] = language
            
            # 시스템 프롬프트 생성 (기본값)
            if 'system' in template_name.lower():
                rendered_prompt = self.manager.get_system_prompt(
                    language=language,
                    include_tests=params.get('include_tests', False)
                )
            else:
                # 다른 타입의 프롬프트도 처리 가능하도록 확장 가능
                rendered_prompt = self.manager.get_system_prompt(language=language)
            
            return PromptResponse(
                rendered_prompt=rendered_prompt,
                template_used=template_name,
                version=1,
                parameters=params
            )
        except Exception as e:
            logger.error(f"프롬프트 생성 실패: {e}")
            raise
    
    def create_template(self, template: PromptTemplate) -> PromptTemplate:
        """새 템플릿 생성"""
        return self.repository.save_template(template)
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """템플릿 조회"""
        return self.repository.get_template_by_name(name)
    
    def list_templates(self) -> List[PromptTemplate]:
        """모든 템플릿 조회"""
        return self.repository.get_all_templates()
    
    def update_template(self, name: str, template: PromptTemplate) -> Optional[PromptTemplate]:
        """템플릿 업데이트"""
        existing = self.repository.get_template_by_name(name)
        if existing:
            template.name = name  # 이름 보존
            return self.repository.save_template(template)
        return None
    
    def delete_template(self, name: str) -> bool:
        """템플릿 삭제"""
        return self.repository.delete_template(name)
    
    def _extract_language_from_template_name(self, template_name: str) -> str:
        """템플릿 이름에서 언어 추출"""
        # 간단한 구현: template_name이 "python_system" 형태라고 가정
        if '_' in template_name:
            return template_name.split('_')[0]
        return 'general' 