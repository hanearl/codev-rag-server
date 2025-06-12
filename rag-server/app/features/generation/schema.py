from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum

# 기존 search 스키마 재활용
from app.features.search.schema import SearchResult

class SupportedLanguage(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"

class SpringBootFeature(str, Enum):
    """Spring Boot 기능 옵션"""
    WEB = "web"
    DATA_JPA = "data-jpa"
    SECURITY = "security"
    ACTUATOR = "actuator"
    VALIDATION = "validation"
    TEST = "test"

class GenerationRequest(BaseModel):
    query: str = Field(..., description="코드 생성 요청")
    context_limit: int = Field(default=3, min=1, max=10, description="컨텍스트 개수")
    language: SupportedLanguage = Field(default=SupportedLanguage.PYTHON, description="생성할 코드 언어")
    include_tests: bool = Field(default=False, description="테스트 코드 포함 여부")
    max_tokens: int = Field(default=2000, min=100, max=4000, description="최대 토큰 수")
    
    # Spring Boot 관련 옵션
    spring_boot_features: List[SpringBootFeature] = Field(
        default=[], 
        description="Spring Boot 기능 (Java 선택 시 적용)"
    )
    java_version: Optional[str] = Field(default="11", description="Java 버전 (8, 11, 17, 21)")
    spring_boot_version: Optional[str] = Field(default="3.2", description="Spring Boot 버전")
    
    # Search 관련 파라미터 (기존 SearchRequest와 호환)
    vector_weight: float = Field(default=0.7, min=0.0, max=1.0, description="벡터 가중치")
    keyword_weight: float = Field(default=0.3, min=0.0, max=1.0, description="키워드 가중치")
    use_rrf: bool = Field(default=False, description="RRF 사용 여부")

class CodeContext(BaseModel):
    """검색된 코드 컨텍스트 (SearchResult 기반)"""
    function_name: Optional[str]
    code_content: str
    file_path: str
    relevance_score: float
    code_type: str
    language: str

class GenerationResponse(BaseModel):
    query: str
    generated_code: str
    contexts_used: List[CodeContext]
    generation_time_ms: int
    model_used: str
    language: str
    tokens_used: int
    search_results_count: int
    
    # Spring Boot 관련 응답 정보
    spring_boot_features_used: List[str] = Field(default=[], description="사용된 Spring Boot 기능")
    java_version_used: Optional[str] = Field(default=None, description="사용된 Java 버전")

class ValidationResult(BaseModel):
    is_valid: bool
    syntax_errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    
    # Spring Boot 관련 검증 결과
    spring_boot_recommendations: List[str] = Field(default=[], description="Spring Boot 추천사항") 