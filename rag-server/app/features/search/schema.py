from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class SearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리")
    keywords: Optional[List[str]] = Field(default=None, description="키워드 필터")
    limit: int = Field(default=10, min=1, max=50, description="결과 개수")
    vector_weight: float = Field(default=0.7, min=0.0, max=1.0, description="벡터 가중치")
    keyword_weight: float = Field(default=0.3, min=0.0, max=1.0, description="키워드 가중치")
    collection_name: str = Field(default="code_chunks", description="검색할 컬렉션")
    
    # RRF 옵션 추가
    use_rrf: bool = Field(default=False, description="RRF (Reciprocal Rank Fusion) 사용 여부")
    rrf_k: int = Field(default=60, min=1, max=1000, description="RRF k 상수 (작을수록 상위 결과에 더 큰 가중치)")
    
    @validator('vector_weight', 'keyword_weight')
    def validate_weights(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('가중치는 0.0과 1.0 사이여야 합니다')
        return v

class SearchResult(BaseModel):
    id: str
    file_path: str
    function_name: Optional[str] = None
    code_content: str
    code_type: str
    language: str
    line_start: int
    line_end: int
    keywords: List[str]
    vector_score: float
    keyword_score: float
    combined_score: float

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
    vector_results_count: int
    keyword_results_count: int
    
    # 사용된 검색 방법 정보 추가
    search_method: str = Field(default="weighted", description="사용된 검색 방법 (weighted/rrf)")
    rrf_k: Optional[int] = Field(default=None, description="사용된 RRF k 값") 