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
    """RAG 시스템 설정"""
    name: str
    base_url: str
    api_key: Optional[str] = None
    system_type: str = "external"  # external, mock, local


class EvaluationRequest(BaseModel):
    """평가 요청"""
    dataset_name: str
    system_config: SystemConfig
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