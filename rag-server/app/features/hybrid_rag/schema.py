from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class HybridSearchRequest(BaseModel):
    """하이브리드 검색 요청"""
    query: str = Field(..., description="검색 쿼리")
    limit: int = Field(default=10, ge=1, le=50, description="검색 결과 수")
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="벡터 검색 가중치")
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="키워드 검색 가중치")
    use_rrf: bool = Field(default=True, description="RRF 사용 여부")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="검색 필터")

class HybridSearchResult(BaseModel):
    """하이브리드 검색 결과"""
    id: str
    content: str
    file_path: Optional[str] = None
    function_name: Optional[str] = None
    language: Optional[str] = None
    vector_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0
    metadata: Dict[str, Any] = {}

class HybridSearchResponse(BaseModel):
    """하이브리드 검색 응답"""
    query: str
    results: List[HybridSearchResult]
    total_results: int
    search_time_ms: int
    search_metadata: Dict[str, Any] = {}

class ExplainRequest(BaseModel):
    """코드 설명 요청"""
    query: str = Field(..., description="설명 요청 질문")
    search_results: Optional[List[HybridSearchResult]] = Field(default=None, description="검색 결과")
    include_context: bool = Field(default=True, description="컨텍스트 포함 여부")
    language_preference: str = Field(default="korean", description="응답 언어")

class ExplainResponse(BaseModel):
    """코드 설명 응답"""
    query: str
    explanation: str
    context_used: List[str] = []
    processing_time_ms: int = 0
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = {} 