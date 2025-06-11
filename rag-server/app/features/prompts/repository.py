from typing import Optional, List
from app.features.prompts.schema import PromptTemplate

class PromptRepository:
    def __init__(self, db_session=None):
        self.db_session = db_session
        # 임시로 메모리에 템플릿 저장
        self._templates = {}
    
    def get_template_by_name(self, name: str) -> Optional[PromptTemplate]:
        """템플릿 이름으로 조회"""
        return self._templates.get(name)
    
    def save_template(self, template: PromptTemplate) -> PromptTemplate:
        """템플릿 저장"""
        self._templates[template.name] = template
        return template
    
    def get_all_templates(self) -> List[PromptTemplate]:
        """모든 템플릿 조회"""
        return list(self._templates.values())
    
    def delete_template(self, name: str) -> bool:
        """템플릿 삭제"""
        if name in self._templates:
            del self._templates[name]
            return True
        return False 