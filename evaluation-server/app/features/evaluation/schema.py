from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, validator, field_validator
from enum import Enum
from datetime import datetime


class DifficultyLevel(str, Enum):
    """난이도 레벨"""
    EASY = "하"
    MEDIUM = "중"
    HARD = "상"


class EvaluationOptions(BaseModel):
    """평가 옵션"""
    convert_filepath_to_classpath: bool = True
    ignore_method_names: bool = True
    case_sensitive: bool = False
    java_source_root: str = "src/main/java"
    java_test_root: str = "src/test/java"


class EvaluationQuestion(BaseModel):
    """평가용 질문"""
    difficulty: str
    question: str
    answer: Union[str, List[str]]
    
    @field_validator('answer')
    @classmethod
    def validate_answer(cls, v):
        if isinstance(v, str):
            return v
        elif isinstance(v, list):
            if not v:
                raise ValueError("answer list cannot be empty")
            return v
        else:
            raise ValueError("answer must be string or list of strings")


class RetrievalResult(BaseModel):
    """검색 결과"""
    content: str
    score: float
    filepath: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SystemConfig(BaseModel):
    """RAG 시스템 설정 (기존 호환성)"""
    name: str
    base_url: str
    api_key: Optional[str] = None
    system_type: str = "external"  # external, mock, local, openai_rag, langchain_rag, llamaindex_rag, rag_server


class AdvancedSystemConfig(BaseModel):
    """고급 RAG 시스템 설정"""
    name: str
    system_type: str  # openai_rag, langchain_rag, llamaindex_rag, custom_http, rag_server, mock
    base_url: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    
    # API 엔드포인트 커스터마이징
    search_endpoint: str = "/api/v1/search"
    embed_endpoint: str = "/api/v1/embed"
    health_endpoint: str = "/health"
    
    # 요청 형식 커스터마이징
    query_field: str = "query"
    k_field: str = "k"
    text_field: str = "text"
    
    # 응답 형식 커스터마이징
    results_field: str = "results"
    content_field: str = "content"
    score_field: str = "score"
    filepath_field: str = "filepath"
    metadata_field: str = "metadata"
    embedding_field: str = "embedding"
    
    # 인증 설정
    auth_type: str = "bearer"  # bearer, api_key, basic, none
    auth_header: str = "Authorization"
    
    # 추가 헤더
    custom_headers: Dict[str, str] = {}


class EvaluationRequest(BaseModel):
    """평가 요청"""
    dataset_name: str
    system_config: Union[SystemConfig, AdvancedSystemConfig]
    k_values: List[int] = [1, 3, 5, 10]
    metrics: List[str] = ["recall", "precision", "hit", "mrr", "ndcg"]
    options: EvaluationOptions = EvaluationOptions()
    save_results: bool = True


class EvaluationResponse(BaseModel):
    """평가 응답"""
    dataset_name: str
    system_name: str
    metrics: Dict[str, Dict[str, float]]  # {metric_name: {k: value}}
    execution_time: float
    question_count: int
    k_values: List[int]
    options: EvaluationOptions


class DatasetMetadata(BaseModel):
    """데이터셋 메타데이터"""
    name: str
    description: str
    format: str
    question_count: int
    evaluation_options: EvaluationOptions
    created_at: str
    version: str = "1.0"


class DatasetListResponse(BaseModel):
    """데이터셋 목록 응답"""
    datasets: List[str]


class DatasetInfoResponse(BaseModel):
    """데이터셋 정보 응답"""
    name: str
    metadata: DatasetMetadata
    question_count: int
    sample_questions: List[EvaluationQuestion]


class MetricsInfoResponse(BaseModel):
    """메트릭 정보 응답"""
    metrics: Dict[str, Dict[str, str]]  # {metric_name: {name, description}}


class ClasspathTestRequest(BaseModel):
    """클래스패스 변환 테스트 요청"""
    filepaths: List[str]
    options: EvaluationOptions


class ClasspathTestResponse(BaseModel):
    """클래스패스 변환 테스트 응답"""
    results: Dict[str, str]  # {filepath: converted_classpath}


class EvaluationMetrics(BaseModel):
    """평가 메트릭"""
    total_questions: int = 0
    processed_questions: int = 0
    hit_at_k: Dict[int, float] = {}
    recall_at_k: Dict[int, float] = {}
    precision_at_k: Dict[int, float] = {}
    ndcg_at_k: Dict[int, float] = {}
    mrr: float = 0.0


class QuestionEvaluationResult(BaseModel):
    """질문별 평가 결과"""
    question: str
    difficulty: str
    expected_answers: List[str]
    retrieved_results: List[RetrievalResult]
    converted_classpaths: List[str]
    matches_at_k: Dict[int, bool]
    reciprocal_rank: float


class EvaluationResult(BaseModel):
    """평가 결과 (Legacy)"""
    id: str
    rag_system_id: str
    dataset_name: str
    metrics: EvaluationMetrics
    evaluation_options: EvaluationOptions
    created_at: str
    execution_time_seconds: float


class BaselineComparison(BaseModel):
    """베이스라인 비교 결과"""
    baseline_id: str = Field(..., description="베이스라인 결과 ID")
    current_result_id: str = Field(..., description="현재 결과 ID")
    metric_improvements: Dict[str, float] = Field(default_factory=dict, description="메트릭 개선도")
    is_better: bool = Field(False, description="베이스라인보다 성능이 좋은지")


# Pydantic model config 업데이트
EvaluationRequest.model_rebuild() 