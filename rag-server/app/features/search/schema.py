"""
하이브리드 검색 API 스키마
"""
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from enum import Enum


class Language(str, Enum):
    """지원 언어"""
    JAVA = "java"
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


# 검색 결과 스키마
class SearchResult(BaseModel):
    """검색 결과"""
    content: str = Field(..., description="검색된 코드 내용")
    score: float = Field(..., description="유사도 점수", ge=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")
    document_id: Optional[str] = Field(None, description="문서 ID")


# 벡터 검색 관련 스키마
class VectorSearchRequest(BaseModel):
    """벡터 검색 요청"""
    query: str = Field(..., description="검색 쿼리", min_length=1)
    collection_name: str = Field(..., description="컬렉션 이름", min_length=1)
    top_k: int = Field(10, description="반환할 결과 수", gt=0, le=100)
    score_threshold: float = Field(0.0, description="최소 유사도 점수", ge=0.0, le=1.0)
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="메타데이터 필터")

    @validator('collection_name')
    def validate_collection_name(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('컬렉션 이름은 영문자, 숫자, _, -만 사용 가능합니다')
        return v


class VectorSearchResponse(BaseModel):
    """벡터 검색 응답"""
    success: bool
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
    collection_name: str
    error: Optional[str] = None


# BM25 검색 관련 스키마
class BM25SearchRequest(BaseModel):
    """BM25 검색 요청"""
    query: str = Field(..., description="검색 쿼리", min_length=1)
    index_name: str = Field(..., description="인덱스 이름", min_length=1)
    top_k: int = Field(10, description="반환할 결과 수", gt=0, le=100)
    filter_language: Optional[Language] = Field(None, description="언어 필터")

    @validator('index_name')
    def validate_index_name(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('인덱스 이름은 영문자, 숫자, _, -만 사용 가능합니다')
        return v


class BM25SearchResponse(BaseModel):
    """BM25 검색 응답"""
    success: bool
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
    index_name: str
    error: Optional[str] = None


# 하이브리드 검색 관련 스키마
class HybridSearchRequest(BaseModel):
    """하이브리드 검색 요청"""
    query: str = Field(..., description="검색 쿼리", min_length=1)
    collection_name: str = Field(..., description="벡터 컬렉션 이름", min_length=1)
    index_name: str = Field(..., description="BM25 인덱스 이름", min_length=1)
    top_k: int = Field(10, description="반환할 결과 수", gt=0, le=100)
    vector_weight: float = Field(0.7, description="벡터 검색 가중치", ge=0.0, le=1.0)
    bm25_weight: float = Field(0.3, description="BM25 검색 가중치", ge=0.0, le=1.0)
    use_rrf: bool = Field(True, description="RRF 사용 여부")
    rrf_k: int = Field(60, description="RRF 파라미터 k", gt=0)
    score_threshold: float = Field(0.0, description="최소 점수 임계값", ge=0.0, le=1.0)
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="메타데이터 필터")
    filter_language: Optional[Language] = Field(None, description="언어 필터")

    @validator('vector_weight', 'bm25_weight')
    def validate_weights(cls, v, values):
        if v < 0.0 or v > 1.0:
            raise ValueError('가중치는 0.0과 1.0 사이의 값이어야 합니다')
        return v

    @validator('bm25_weight')
    def validate_weight_sum(cls, v, values):
        if 'vector_weight' in values:
            total_weight = values['vector_weight'] + v
            if not (0.8 <= total_weight <= 1.2):  # 약간의 오차 허용
                raise ValueError('vector_weight와 bm25_weight의 합은 1.0에 가까워야 합니다')
        return v

    @validator('collection_name', 'index_name')
    def validate_names(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('이름은 영문자, 숫자, _, -만 사용 가능합니다')
        return v


class HybridSearchResponse(BaseModel):
    """하이브리드 검색 응답"""
    success: bool
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
    vector_results_count: int
    bm25_results_count: int
    fusion_method: str
    weights_used: Dict[str, float]
    error: Optional[str] = None


# 헬스체크 관련 스키마
class SearchComponentStatus(BaseModel):
    """검색 컴포넌트 상태"""
    vector_index: bool
    bm25_index: bool
    hybrid_retriever: bool


class SearchHealthCheckResponse(BaseModel):
    """검색 헬스체크 응답"""
    status: str = Field(..., description="서비스 상태", pattern="^(healthy|degraded|unhealthy)$")
    service: str
    components: SearchComponentStatus
    error: Optional[str] = None


# 검색 통계 스키마
class SearchStatsResponse(BaseModel):
    """검색 통계 응답"""
    total_queries: int
    avg_search_time_ms: float
    vector_search_count: int
    bm25_search_count: int
    hybrid_search_count: int
    top_queries: List[str]
    performance_metrics: Dict[str, Any]


# 에러 응답 스키마
class SearchErrorResponse(BaseModel):
    """검색 에러 응답"""
    detail: str
    error_code: Optional[str] = None
    query: Optional[str] = None
    timestamp: Optional[str] = None


# 검색 설정 스키마
class SearchConfig(BaseModel):
    """검색 설정"""
    default_top_k: int = Field(10, gt=0, le=100)
    default_vector_weight: float = Field(0.7, ge=0.0, le=1.0)
    default_bm25_weight: float = Field(0.3, ge=0.0, le=1.0)
    default_score_threshold: float = Field(0.0, ge=0.0, le=1.0)
    max_query_length: int = Field(1000, gt=0)
    enable_query_cache: bool = Field(True)
    cache_ttl_seconds: int = Field(300, gt=0)


# 검색 로그 스키마
class SearchLog(BaseModel):
    """검색 로그"""
    query: str
    search_type: str = Field(..., pattern="^(vector|bm25|hybrid)$")
    results_count: int
    search_time_ms: int
    success: bool
    error_message: Optional[str] = None
    timestamp: str
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None 