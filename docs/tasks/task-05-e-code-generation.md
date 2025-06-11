# Task 05-E: 코드 생성 서비스 구현

## 🎯 목표
검색된 컨텍스트를 활용하여 고품질 코드를 생성하는 RAG 기반 서비스를 TDD 방식으로 구현합니다.

## 📋 MVP 범위
- RAG 기반 코드 생성 엔진
- 검색된 컨텍스트를 활용한 생성
- 코드 생성 REST API
- 언어별 코드 생성 최적화

## 🏗️ 기술 스택
- **웹 프레임워크**: FastAPI
- **LLM**: OpenAI GPT-4o-mini
- **RAG 파이프라인**: 커스텀 구현
- **테스트**: pytest, httpx

## 📁 프로젝트 구조

```
rag-server/
├── app/
│   ├── features/
│   │   └── generation/
│   │       ├── __init__.py
│   │       ├── router.py        ← 생성 API
│   │       ├── service.py       ← 생성 비즈니스 로직
│   │       ├── schema.py        ← 생성 스키마
│   │       ├── generator.py     ← 코드 생성기
│   │       └── validator.py     ← 코드 검증기
│   └── main.py
├── tests/
│   ├── unit/
│   │   └── features/
│   │       └── generation/
│   │           ├── test_service.py
│   │           ├── test_generator.py
│   │           ├── test_validator.py
│   │           └── test_router.py
│   └── integration/
│       └── test_generation_api.py
├── requirements.txt
└── pytest.ini
```

## 🧪 TDD 구현 순서

### 1단계: 생성 스키마 정의 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/generation/test_schema.py
import pytest
from pydantic import ValidationError
from app.features.generation.schema import GenerationRequest, GenerationResponse

def test_generation_request_should_validate_required_fields():
    """생성 요청이 필수 필드를 검증해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        GenerationRequest()  # query 필드 누락
    
    # Valid request
    request = GenerationRequest(query="Create a function")
    assert request.query == "Create a function"
    assert request.context_limit == 3  # 기본값
    assert request.language == "python"  # 기본값
    assert request.include_tests == False  # 기본값

def test_generation_request_should_validate_context_limit():
    """생성 요청이 컨텍스트 제한을 검증해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        GenerationRequest(query="test", context_limit=0)  # 최소값 미만
    
    with pytest.raises(ValidationError):
        GenerationRequest(query="test", context_limit=11)  # 최대값 초과

def test_generation_request_should_validate_language():
    """생성 요청이 지원하는 언어를 검증해야 함"""
    # Given & When & Then
    valid_languages = ["python", "javascript", "typescript", "java", "go"]
    
    for lang in valid_languages:
        request = GenerationRequest(query="test", language=lang)
        assert request.language == lang
    
    with pytest.raises(ValidationError):
        GenerationRequest(query="test", language="unsupported")
```

**🟢 최소 구현**
```python
# app/features/generation/schema.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum

class SupportedLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"

class GenerationRequest(BaseModel):
    query: str = Field(..., description="코드 생성 요청")
    context_limit: int = Field(default=3, min=1, max=10, description="컨텍스트 개수")
    language: SupportedLanguage = Field(default=SupportedLanguage.PYTHON, description="생성할 코드 언어")
    include_tests: bool = Field(default=False, description="테스트 코드 포함 여부")
    max_tokens: int = Field(default=2000, min=100, max=4000, description="최대 토큰 수")

class CodeContext(BaseModel):
    function_name: str
    code_content: str
    file_path: str
    relevance_score: float

class GenerationResponse(BaseModel):
    query: str
    generated_code: str
    contexts_used: List[CodeContext]
    generation_time_ms: int
    model_used: str
    language: str
    tokens_used: int

class ValidationResult(BaseModel):
    is_valid: bool
    syntax_errors: List[str]
    warnings: List[str]
    suggestions: List[str]
```

### 2단계: 코드 생성기 구현 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/generation/test_generator.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.features.generation.generator import CodeGenerator
from app.features.generation.schema import GenerationRequest, CodeContext

@pytest.fixture
def mock_llm_client():
    client = Mock()
    client.chat_completion = AsyncMock()
    return client

@pytest.fixture
def mock_prompt_manager():
    manager = Mock()
    manager.get_system_prompt = Mock()
    manager.get_user_prompt = Mock()
    return manager

@pytest.mark.asyncio
async def test_code_generator_should_generate_code_with_context(
    mock_llm_client, mock_prompt_manager
):
    """코드 생성기가 컨텍스트를 사용하여 코드를 생성해야 함"""
    # Given
    generator = CodeGenerator(mock_llm_client, mock_prompt_manager)
    
    mock_prompt_manager.get_system_prompt.return_value = "You are a Python expert."
    mock_prompt_manager.get_user_prompt.return_value = "Create a function to calculate sum"
    
    mock_llm_client.chat_completion.return_value = {
        "choices": [
            {
                "message": {
                    "content": "def calculate_sum(a, b):\n    \"\"\"두 수의 합을 계산합니다.\"\"\"\n    return a + b"
                }
            }
        ],
        "usage": {
            "total_tokens": 150
        }
    }
    
    request = GenerationRequest(query="Create a function to calculate sum")
    contexts = [
        CodeContext(
            function_name="add_numbers",
            code_content="def add_numbers(x, y): return x + y",
            file_path="math_utils.py",
            relevance_score=0.9
        )
    ]
    
    # When
    result = await generator.generate_code(request, contexts)
    
    # Then
    assert result.generated_code == "def calculate_sum(a, b):\n    \"\"\"두 수의 합을 계산합니다.\"\"\"\n    return a + b"
    assert result.tokens_used == 150
    assert result.model_used == "gpt-4o-mini"
    mock_llm_client.chat_completion.assert_called_once()

@pytest.mark.asyncio
async def test_code_generator_should_handle_different_languages(
    mock_llm_client, mock_prompt_manager
):
    """코드 생성기가 다양한 언어를 처리해야 함"""
    # Given
    generator = CodeGenerator(mock_llm_client, mock_prompt_manager)
    
    mock_prompt_manager.get_system_prompt.return_value = "You are a JavaScript expert."
    mock_prompt_manager.get_user_prompt.return_value = "Create a function"
    
    mock_llm_client.chat_completion.return_value = {
        "choices": [{"message": {"content": "function test() { return 'hello'; }"}}],
        "usage": {"total_tokens": 100}
    }
    
    request = GenerationRequest(query="Create a function", language="javascript")
    
    # When
    result = await generator.generate_code(request, [])
    
    # Then
    assert result.language == "javascript"
    mock_prompt_manager.get_system_prompt.assert_called_with("javascript", False)

@pytest.mark.asyncio
async def test_code_generator_should_handle_empty_context(
    mock_llm_client, mock_prompt_manager
):
    """코드 생성기가 빈 컨텍스트를 처리해야 함"""
    # Given
    generator = CodeGenerator(mock_llm_client, mock_prompt_manager)
    
    mock_prompt_manager.get_system_prompt.return_value = "You are a Python expert."
    mock_prompt_manager.get_user_prompt.return_value = "Create a function"
    
    mock_llm_client.chat_completion.return_value = {
        "choices": [{"message": {"content": "def new_function(): pass"}}],
        "usage": {"total_tokens": 50}
    }
    
    request = GenerationRequest(query="Create a new function")
    
    # When
    result = await generator.generate_code(request, [])
    
    # Then
    assert result.generated_code == "def new_function(): pass"
    assert len(result.contexts_used) == 0
```

### 3단계: 코드 검증기 구현 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/generation/test_validator.py
import pytest
from app.features.generation.validator import CodeValidator
from app.features.generation.schema import ValidationResult

def test_python_validator_should_validate_syntax():
    """Python 검증기가 구문을 검증해야 함"""
    # Given
    validator = CodeValidator()
    
    valid_code = "def test_func():\n    return 'hello'"
    invalid_code = "def test_func(\n    return 'hello'"
    
    # When
    valid_result = validator.validate_python_code(valid_code)
    invalid_result = validator.validate_python_code(invalid_code)
    
    # Then
    assert valid_result.is_valid == True
    assert len(valid_result.syntax_errors) == 0
    
    assert invalid_result.is_valid == False
    assert len(invalid_result.syntax_errors) > 0

def test_python_validator_should_check_best_practices():
    """Python 검증기가 베스트 프랙티스를 확인해야 함"""
    # Given
    validator = CodeValidator()
    
    # 타입 힌트가 없는 코드
    code_without_hints = "def add(a, b):\n    return a + b"
    
    # 독스트링이 없는 코드
    code_without_docstring = "def complex_function(data):\n    return data.process()"
    
    # When
    result1 = validator.validate_python_code(code_without_hints)
    result2 = validator.validate_python_code(code_without_docstring)
    
    # Then
    assert result1.is_valid == True
    assert any("타입 힌트" in warning for warning in result1.warnings)
    
    assert result2.is_valid == True
    assert any("독스트링" in warning for warning in result2.warnings)

def test_validator_should_provide_suggestions():
    """검증기가 개선 제안을 제공해야 함"""
    # Given
    validator = CodeValidator()
    
    code = "def func():\n    x = 1\n    y = 2\n    return x + y"
    
    # When
    result = validator.validate_python_code(code)
    
    # Then
    assert result.is_valid == True
    assert len(result.suggestions) > 0
```

**🟢 최소 구현**
```python
# app/features/generation/validator.py
import ast
import re
from typing import List
from .schema import ValidationResult

class CodeValidator:
    def validate_python_code(self, code: str) -> ValidationResult:
        """Python 코드 검증"""
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # 구문 검사
            ast.parse(code)
            
            # 베스트 프랙티스 검사
            warnings.extend(self._check_python_best_practices(code))
            
            # 개선 제안
            suggestions.extend(self._get_python_suggestions(code))
            
            return ValidationResult(
                is_valid=True,
                syntax_errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
            
        except SyntaxError as e:
            errors.append(f"구문 오류 (라인 {e.lineno}): {e.msg}")
            return ValidationResult(
                is_valid=False,
                syntax_errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
    
    def _check_python_best_practices(self, code: str) -> List[str]:
        """Python 베스트 프랙티스 검사"""
        warnings = []
        
        # 타입 힌트 확인
        if re.search(r'def\s+\w+\([^)]*\)\s*:', code) and '->' not in code:
            if ':' not in code.split('def')[1].split(')')[0]:
                warnings.append("타입 힌트 사용을 권장합니다")
        
        # 독스트링 확인
        if 'def ' in code and '"""' not in code and "'''" not in code:
            warnings.append("함수에 독스트링 추가를 권장합니다")
        
        # 네이밍 컨벤션 확인
        if re.search(r'def\s+[A-Z]', code):
            warnings.append("함수명은 snake_case를 사용하는 것이 좋습니다")
        
        return warnings
    
    def _get_python_suggestions(self, code: str) -> List[str]:
        """Python 코드 개선 제안"""
        suggestions = []
        
        # 에러 핸들링 제안
        if 'try:' not in code and ('open(' in code or 'requests.' in code):
            suggestions.append("파일 또는 네트워크 작업에 예외 처리를 추가하세요")
        
        # 리스트 컴프리헨션 제안
        if 'for ' in code and 'append(' in code:
            suggestions.append("리스트 컴프리헨션 사용을 고려해보세요")
        
        return suggestions
    
    def validate_javascript_code(self, code: str) -> ValidationResult:
        """JavaScript 코드 검증 (기본 구현)"""
        # 기본적인 구문 검사만 수행
        errors = []
        warnings = []
        suggestions = []
        
        # 기본 구문 오류 검사
        if code.count('{') != code.count('}'):
            errors.append("중괄호 개수가 맞지 않습니다")
        
        if code.count('(') != code.count(')'):
            errors.append("괄호 개수가 맞지 않습니다")
        
        # ES6+ 문법 제안
        if 'var ' in code:
            suggestions.append("let 또는 const 사용을 권장합니다")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            syntax_errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
```

### 4단계: 생성 서비스 구현 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/generation/test_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.features.generation.service import GenerationService
from app.features.generation.schema import GenerationRequest, GenerationResponse
from app.features.search.schema import SearchResult

@pytest.fixture
def mock_search_service():
    service = Mock()
    service.search_code = AsyncMock()
    return service

@pytest.fixture
def mock_generator():
    generator = Mock()
    generator.generate_code = AsyncMock()
    return generator

@pytest.fixture
def mock_validator():
    validator = Mock()
    validator.validate_python_code = Mock()
    return validator

@pytest.mark.asyncio
async def test_generation_service_should_generate_code_with_context(
    mock_search_service, mock_generator, mock_validator
):
    """생성 서비스가 컨텍스트를 사용하여 코드를 생성해야 함"""
    # Given
    service = GenerationService(mock_search_service, mock_generator, mock_validator)
    
    # Mock 검색 결과
    mock_search_results = [
        SearchResult(
            id="1", file_path="test.py", function_name="test_func",
            code_content="def test_func(): pass", code_type="function",
            language="python", line_start=1, line_end=1,
            keywords=["test"], vector_score=0.9,
            keyword_score=0.8, combined_score=0.85
        )
    ]
    
    mock_search_response = Mock()
    mock_search_response.results = mock_search_results
    mock_search_service.search_code.return_value = mock_search_response
    
    # Mock 생성 결과
    mock_generation_response = GenerationResponse(
        query="Create a function",
        generated_code="def new_func(): return 'hello'",
        contexts_used=[],
        generation_time_ms=500,
        model_used="gpt-4o-mini",
        language="python",
        tokens_used=100
    )
    mock_generator.generate_code.return_value = mock_generation_response
    
    request = GenerationRequest(query="Create a function")
    
    # When
    result = await service.generate_code(request)
    
    # Then
    assert result.generated_code == "def new_func(): return 'hello'"
    assert result.query == "Create a function"
    mock_search_service.search_code.assert_called_once()
    mock_generator.generate_code.assert_called_once()

@pytest.mark.asyncio
async def test_generation_service_should_validate_generated_code(
    mock_search_service, mock_generator, mock_validator
):
    """생성 서비스가 생성된 코드를 검증해야 함"""
    # Given
    service = GenerationService(mock_search_service, mock_generator, mock_validator)
    
    mock_search_service.search_code.return_value.results = []
    
    mock_generation_response = GenerationResponse(
        query="Create a function",
        generated_code="def invalid_func(\n    pass",  # 잘못된 구문
        contexts_used=[],
        generation_time_ms=500,
        model_used="gpt-4o-mini",
        language="python",
        tokens_used=100
    )
    mock_generator.generate_code.return_value = mock_generation_response
    
    # Mock 검증 결과 (실패)
    from app.features.generation.schema import ValidationResult
    mock_validation_result = ValidationResult(
        is_valid=False,
        syntax_errors=["구문 오류: 잘못된 함수 정의"],
        warnings=[],
        suggestions=[]
    )
    mock_validator.validate_python_code.return_value = mock_validation_result
    
    request = GenerationRequest(query="Create a function")
    
    # When & Then
    with pytest.raises(ValueError, match="생성된 코드에 구문 오류가 있습니다"):
        await service.generate_code(request)
```

**🟢 최소 구현**
```python
# app/features/generation/service.py
from typing import List
from .schema import GenerationRequest, GenerationResponse, CodeContext
from .generator import CodeGenerator
from .validator import CodeValidator
from app.features.search.service import SearchService
from app.features.search.schema import SearchRequest
import logging

logger = logging.getLogger(__name__)

class GenerationService:
    def __init__(
        self, 
        search_service: SearchService,
        generator: CodeGenerator,
        validator: CodeValidator
    ):
        self.search_service = search_service
        self.generator = generator
        self.validator = validator
    
    async def generate_code(self, request: GenerationRequest) -> GenerationResponse:
        """컨텍스트 기반 코드 생성"""
        try:
            # 관련 코드 검색
            contexts = await self._get_contexts(request)
            
            # 코드 생성
            generation_result = await self.generator.generate_code(request, contexts)
            
            # 코드 검증
            await self._validate_generated_code(generation_result)
            
            logger.info(f"코드 생성 완료: {len(generation_result.generated_code)}자, "
                       f"{generation_result.generation_time_ms}ms")
            
            return generation_result
            
        except Exception as e:
            logger.error(f"코드 생성 실패: {e}")
            raise
    
    async def _get_contexts(self, request: GenerationRequest) -> List[CodeContext]:
        """관련 컨텍스트 수집"""
        search_request = SearchRequest(
            query=request.query,
            limit=request.context_limit
        )
        
        search_response = await self.search_service.search_code(search_request)
        
        contexts = []
        for result in search_response.results:
            context = CodeContext(
                function_name=result.function_name,
                code_content=result.code_content,
                file_path=result.file_path,
                relevance_score=result.combined_score
            )
            contexts.append(context)
        
        return contexts
    
    async def _validate_generated_code(self, generation_result: GenerationResponse) -> None:
        """생성된 코드 검증"""
        if generation_result.language == "python":
            validation_result = self.validator.validate_python_code(
                generation_result.generated_code
            )
        elif generation_result.language == "javascript":
            validation_result = self.validator.validate_javascript_code(
                generation_result.generated_code
            )
        else:
            # 다른 언어는 기본 검증만 수행
            return
        
        if not validation_result.is_valid:
            error_msg = f"생성된 코드에 구문 오류가 있습니다: {', '.join(validation_result.syntax_errors)}"
            raise ValueError(error_msg)
        
        # 경고사항 로깅
        if validation_result.warnings:
            logger.warning(f"코드 품질 경고: {', '.join(validation_result.warnings)}")
```

### 5단계: API 라우터 구현 (TDD)

**🔴 테스트 작성**
```python
# tests/unit/features/generation/test_router.py
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.features.generation.service import GenerationService

def test_generation_endpoint_should_return_generated_code():
    """생성 엔드포인트가 생성된 코드를 반환해야 함"""
    # Given
    from app.features.generation.schema import GenerationResponse
    mock_response = GenerationResponse(
        query="Create a function",
        generated_code="def test_func():\n    return 'hello'",
        contexts_used=[],
        generation_time_ms=1000,
        model_used="gpt-4o-mini",
        language="python",
        tokens_used=150
    )
    
    # Mock dependency
    mock_service = Mock()
    mock_service.generate_code = AsyncMock(return_value=mock_response)
    
    app.dependency_overrides[GenerationService] = lambda: mock_service
    client = TestClient(app)
    
    # When
    response = client.post("/api/v1/generate", json={
        "query": "Create a function",
        "language": "python"
    })
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["generated_code"] == "def test_func():\n    return 'hello'"
    assert data["generation_time_ms"] == 1000
    assert data["tokens_used"] == 150
    
    # Cleanup
    del app.dependency_overrides[GenerationService]

def test_generation_endpoint_should_validate_request():
    """생성 엔드포인트가 요청을 검증해야 함"""
    # Given
    client = TestClient(app)
    
    # When: 잘못된 요청
    response = client.post("/api/v1/generate", json={
        "context_limit": 5  # query 누락
    })
    
    # Then
    assert response.status_code == 422  # Validation Error

def test_generation_endpoint_should_handle_unsupported_language():
    """생성 엔드포인트가 지원하지 않는 언어를 처리해야 함"""
    # Given
    client = TestClient(app)
    
    # When: 지원하지 않는 언어
    response = client.post("/api/v1/generate", json={
        "query": "Create a function",
        "language": "unsupported"
    })
    
    # Then
    assert response.status_code == 422  # Validation Error
```

**🟢 최소 구현**
```python
# app/features/generation/router.py
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
        "service": "generation-service",
        "timestamp": "2024-01-15T10:00:00Z"
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
```

## 🧪 Integration 테스트

```python
# tests/integration/test_generation_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.integration
def test_generation_api_integration():
    """생성 API 통합 테스트"""
    client = TestClient(app)
    
    # When: 코드 생성 수행
    response = client.post("/api/v1/generate", json={
        "query": "Create a function to calculate fibonacci sequence",
        "context_limit": 3,
        "language": "python",
        "include_tests": False
    })
    
    # Then: 성공적인 응답
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "generated_code" in data
    assert "contexts_used" in data
    assert "generation_time_ms" in data
    assert data["generation_time_ms"] < 60000  # 1분 이내

@pytest.mark.integration
def test_generation_with_different_languages():
    """다양한 언어로 코드 생성 테스트"""
    client = TestClient(app)
    
    languages = ["python", "javascript", "typescript"]
    
    for language in languages:
        # When: 언어별 코드 생성
        response = client.post("/api/v1/generate", json={
            "query": "Create a simple calculator function",
            "language": language,
            "context_limit": 2
        })
        
        # Then: 성공적인 생성
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == language
        assert data["generated_code"]
        assert data["tokens_used"] > 0

@pytest.mark.integration
def test_generation_with_tests():
    """테스트 포함 코드 생성 테스트"""
    client = TestClient(app)
    
    # When: 테스트 포함 생성
    response = client.post("/api/v1/generate", json={
        "query": "Create a function to validate email",
        "language": "python",
        "include_tests": True,
        "context_limit": 2
    })
    
    # Then: 테스트가 포함된 코드 생성
    assert response.status_code == 200
    data = response.json()
    assert "test" in data["generated_code"].lower() or "assert" in data["generated_code"]

@pytest.mark.integration
def test_generation_performance():
    """생성 성능 테스트"""
    client = TestClient(app)
    
    # When: 복잡한 요청으로 생성
    response = client.post("/api/v1/generate", json={
        "query": "Create a complete REST API class with CRUD operations",
        "language": "python",
        "context_limit": 5,
        "max_tokens": 3000
    })
    
    # Then: 성능 기준 충족
    assert response.status_code == 200
    data = response.json()
    assert data["generation_time_ms"] < 60000  # 1분 이내
    assert len(data["generated_code"]) > 100  # 충분한 길이의 코드
```

## 📊 성공 기준
1. **생성 품질**: 생성된 코드가 구문적으로 올바름 (95% 이상)
2. **응답 속도**: 코드 생성 60초 이내
3. **컨텍스트 활용**: 관련 코드 패턴 반영도 80% 이상
4. **언어 지원**: 5개 언어 이상 지원
5. **검증 정확도**: 코드 검증 90% 이상 정확도

## 📈 다음 단계
- Task 05-F: 프롬프트 관리 서비스 구현
- 생성 품질 개선 및 최적화
- 더 많은 프로그래밍 언어 지원 추가

## 🔄 TDD 사이클 요약
1. **Red**: 코드 생성 기능별 테스트 작성 → 실패
2. **Green**: RAG 기반 생성 구현 → 테스트 통과  
3. **Refactor**: 생성 품질 최적화, 코드 정리

이 Task는 검색된 컨텍스트를 활용하여 실용적인 코드를 생성하는 핵심 기능을 완성합니다. 