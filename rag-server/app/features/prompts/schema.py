from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime

class PromptCategory(str, Enum):
    SYSTEM = "system"
    USER = "user"
    CONTEXT = "context"
    TEST = "test"

class PromptTemplate(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., description="프롬프트 템플릿 이름")
    category: PromptCategory = Field(..., description="프롬프트 카테고리")
    language: str = Field(..., description="대상 프로그래밍 언어")
    template: str = Field(..., description="Jinja2 템플릿 내용")
    description: Optional[str] = Field(None, description="템플릿 설명")
    version: int = Field(default=1, description="템플릿 버전")
    is_active: bool = Field(default=True, description="활성화 상태")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class PromptRequest(BaseModel):
    template_name: str = Field(..., description="템플릿 이름")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="템플릿 매개변수")
    language: Optional[str] = Field(None, description="언어 오버라이드")

class PromptResponse(BaseModel):
    rendered_prompt: str
    template_used: str
    version: int
    parameters: Dict[str, Any]

class PromptMetrics(BaseModel):
    template_name: str
    usage_count: int
    success_rate: float
    avg_generation_time: float
    last_used: datetime

class CodeContext(BaseModel):
    function_name: str
    code_content: str
    file_path: str
    relevance_score: float 