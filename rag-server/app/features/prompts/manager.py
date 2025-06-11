from typing import List, Dict, Any, Optional
from jinja2 import Template, Environment, FileSystemLoader, TemplateNotFound
from .schema import PromptTemplate, CodeContext, PromptCategory
from .repository import PromptRepository
import logging

logger = logging.getLogger(__name__)

class PromptManager:
    def __init__(self, repository: PromptRepository):
        self.repository = repository
        self.env = Environment(loader=FileSystemLoader('app/features/prompts/templates'))
    
    def get_system_prompt(self, language: str, include_tests: bool = False) -> str:
        """시스템 프롬프트 생성"""
        template_name = f"{language}_system"
        template = self.repository.get_template_by_name(template_name)
        
        if not template:
            # 1. 먼저 파일 시스템에서 템플릿 파일 확인
            try:
                file_template = self.env.get_template(f"{language}.j2")
                template_content = file_template.render(
                    include_tests=include_tests,
                    contexts=[],
                    language=language.title()
                )
                return template_content
            except TemplateNotFound:
                # 2. 시스템 템플릿 파일 확인
                try:
                    system_template = self.env.get_template("system.j2")
                    template_content = system_template.render(
                        language=language.title(),
                        include_tests=include_tests,
                        extra_instruction="Include test code." if include_tests else ""
                    )
                    return template_content
                except TemplateNotFound:
                    # 3. 마지막으로 기본 템플릿 사용
                    template = self._get_default_system_template(language)
        
        if template:
            return self._render_template(template.template, {
                "language": language.title(),
                "include_tests": include_tests,
                "extra_instruction": "Include test code." if include_tests else ""
            })
        
        # 최후의 수단
        return f"You are a {language.title()} expert. Write clean, efficient code."
    
    def get_user_prompt(
        self, 
        query: str, 
        contexts: List[CodeContext], 
        include_tests: bool = False
    ) -> str:
        """사용자 프롬프트 생성"""
        template_name = "user_with_context"
        template = self.repository.get_template_by_name(template_name)
        
        if not template:
            template = self._get_default_user_template()
        
        return self._render_template(template.template, {
            "query": query,
            "contexts": contexts,
            "include_tests": include_tests
        })
    
    def _render_template(self, template_str: str, params: Dict[str, Any]) -> str:
        """템플릿 렌더링"""
        try:
            template = Template(template_str)
            return template.render(**params)
        except Exception as e:
            logger.error(f"템플릿 렌더링 실패: {e}")
            raise
    
    def _get_default_system_template(self, language: str) -> PromptTemplate:
        """기본 시스템 템플릿"""
        return PromptTemplate(
            name=f"{language}_system",
            category=PromptCategory.SYSTEM,
            language=language,
            template=f"You are a {language.title()} expert. Write clean, efficient code."
        )
    
    def _get_default_user_template(self) -> PromptTemplate:
        """기본 사용자 템플릿"""
        return PromptTemplate(
            name="user_with_context",
            category=PromptCategory.USER,
            language="general",
            template="Request: {{query}}\n\nRelevant examples:\n{% for ctx in contexts %}{{ctx.code_content}}\n\n{% endfor %}"
        ) 