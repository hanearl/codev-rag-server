# Task 05-F: 프롬프트 관리 서비스 구현

## 🎯 목표
코드 생성 품질 향상을 위한 체계적인 프롬프트 관리 시스템을 TDD 방식으로 구현합니다.

## 📋 MVP 범위
- 프롬프트 템플릿 관리
- 언어별/도메인별 프롬프트 최적화
- 프롬프트 버전 관리
- A/B 테스트 지원

## 🏗️ 기술 스택
- **웹 프레임워크**: FastAPI
- **템플릿 엔진**: Jinja2
- **데이터베이스**: SQLite/PostgreSQL
- **테스트**: pytest, httpx

## 📁 프로젝트 구조

```
rag-server/
├── app/
│   ├── features/
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── router.py        ← 프롬프트 관리 API
│   │       ├── service.py       ← 프롬프트 비즈니스 로직
│   │       ├── schema.py        ← 프롬프트 스키마
│   │       ├── manager.py       ← 프롬프트 매니저
│   │       ├── repository.py    ← 프롬프트 DB 접근
│   │       ├── model.py         ← 프롬프트 ORM 모델
│   │       └── templates/       ← 기본 템플릿들
│   │           ├── python.j2
│   │           ├── javascript.j2
│   │           └── system.j2
│   │
│   └── main.py
├── tests/
│   ├── unit/
│   │   └── features/
│   │       └── prompts/
│   │           ├── test_service.py
│   │           ├── test_manager.py
│   │           ├── test_repository.py
│   │           └── test_router.py
│   └── integration/
│       └── test_prompt_api.py
├── requirements.txt
└── pytest.ini
```

## 🧪 TDD 구현 순서

### 1단계: 프롬프트 스키마 정의 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/prompts/test_schema.py
import pytest
from pydantic import ValidationError
from app.features.prompts.schema import PromptTemplate, PromptRequest

def test_prompt_template_should_validate_required_fields():
    """프롬프트 템플릿이 필수 필드를 검증해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        PromptTemplate()  # name 필드 누락
    
    # Valid template
    template = PromptTemplate(
        name="python_system",
        category="system",
        language="python",
        template="You are a Python expert."
    )
    assert template.name == "python_system"
    assert template.version == 1  # 기본값
    assert template.is_active == True  # 기본값

def test_prompt_request_should_validate_parameters():
    """프롬프트 요청이 매개변수를 검증해야 함"""
    # Given & When & Then
    request = PromptRequest(
        template_name="python_system",
        parameters={"language": "python", "include_tests": True}
    )
    assert request.template_name == "python_system"
    assert request.parameters["language"] == "python"
```

**🟢 최소 구현**
```python
# app/features/prompts/schema.py
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
```

### 2단계: 프롬프트 매니저 구현 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/prompts/test_manager.py
import pytest
from unittest.mock import Mock
from app.features.prompts.manager import PromptManager
from app.features.prompts.schema import PromptTemplate, CodeContext

@pytest.fixture
def mock_repository():
    repo = Mock()
    repo.get_template_by_name = Mock()
    return repo

def test_prompt_manager_should_render_system_prompt():
    """프롬프트 매니저가 시스템 프롬프트를 렌더링해야 함"""
    # Given
    manager = PromptManager(mock_repository)
    
    template = PromptTemplate(
        name="python_system",
        category="system",
        language="python",
        template="You are a {{language}} expert. {{extra_instruction}}"
    )
    mock_repository.get_template_by_name.return_value = template
    
    # When
    result = manager.get_system_prompt("python", include_tests=True)
    
    # Then
    assert "Python expert" in result
    assert "test" in result.lower()

def test_prompt_manager_should_render_user_prompt_with_context():
    """프롬프트 매니저가 컨텍스트와 함께 사용자 프롬프트를 렌더링해야 함"""
    # Given
    manager = PromptManager(mock_repository)
    
    template = PromptTemplate(
        name="python_user",
        category="user", 
        language="python",
        template="Request: {{query}}\n\nExamples:\n{% for ctx in contexts %}{{ctx.code_content}}\n{% endfor %}"
    )
    mock_repository.get_template_by_name.return_value = template
    
    contexts = [
        CodeContext(
            function_name="test_func",
            code_content="def test(): pass",
            file_path="test.py",
            relevance_score=0.9
        )
    ]
    
    # When
    result = manager.get_user_prompt("Create a function", contexts)
    
    # Then
    assert "Create a function" in result
    assert "def test(): pass" in result
```

**🟢 최소 구현**
```python
# app/features/prompts/manager.py
from typing import List, Dict, Any
from jinja2 import Template, Environment, FileSystemLoader
from .schema import PromptTemplate, CodeContext
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
            template = self._get_default_system_template(language)
        
        return self._render_template(template.template, {
            "language": language.title(),
            "include_tests": include_tests,
            "extra_instruction": "Include test code." if include_tests else ""
        })
    
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
            category="system",
            language=language,
            template=f"You are a {language.title()} expert. Write clean, efficient code."
        )
    
    def _get_default_user_template(self) -> PromptTemplate:
        """기본 사용자 템플릿"""
        return PromptTemplate(
            name="user_with_context",
            category="user",
            language="general",
            template="Request: {{query}}\n\nRelevant examples:\n{% for ctx in contexts %}{{ctx.code_content}}\n\n{% endfor %}"
        )
```

## 📊 성공 기준
1. **템플릿 관리**: 10개 이상의 언어별 템플릿
2. **렌더링 성능**: 템플릿 렌더링 100ms 이내
3. **버전 관리**: 템플릿 버전 추적 및 롤백 지원
4. **A/B 테스트**: 2개 이상 템플릿 동시 실행 지원
5. **품질 향상**: 프롬프트 최적화로 코드 품질 10% 향상

## 📈 다음 단계
- 전체 RAG 시스템 통합 테스트
- 프롬프트 성능 분석 및 최적화
- 더 많은 언어 및 도메인 템플릿 추가

## 🔄 TDD 사이클 요약
1. **Red**: 프롬프트 관리 기능별 테스트 작성 → 실패
2. **Green**: 템플릿 시스템 구현 → 테스트 통과  
3. **Refactor**: 프롬프트 품질 최적화, 코드 정리

이 Task는 RAG 시스템의 코드 생성 품질을 결정하는 핵심 프롬프트 관리 기능을 완성합니다. 