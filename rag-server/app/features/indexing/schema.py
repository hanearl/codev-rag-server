"""
하이브리드 인덱싱 API 스키마
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


class ChunkingStrategy(str, Enum):
    """청킹 전략"""
    METHOD_LEVEL = "method_level"
    CLASS_LEVEL = "class_level"
    FILE_LEVEL = "file_level"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


# 파싱 관련 스키마
class ParseRequest(BaseModel):
    """코드 파싱 요청"""
    code: str = Field(..., description="파싱할 코드 내용", min_length=1)
    language: Language = Field(Language.JAVA, description="프로그래밍 언어")
    file_path: Optional[str] = Field(None, description="파일 경로")
    extract_methods: bool = Field(True, description="메서드 추출 여부")
    extract_classes: bool = Field(True, description="클래스 추출 여부")
    extract_functions: bool = Field(True, description="함수 추출 여부")
    extract_imports: bool = Field(True, description="import 추출 여부")


class ParseResponse(BaseModel):
    """코드 파싱 응답"""
    success: bool
    ast_info: Optional[Dict[str, Any]] = None
    parse_time_ms: Optional[int] = None
    file_path: Optional[str] = None
    language: Optional[Language] = None
    error_message: Optional[str] = None


class ParseFileResponse(BaseModel):
    """파일 파싱 응답"""
    filename: str
    success: bool
    ast_info: Optional[Dict[str, Any]] = None
    parse_time_ms: Optional[int] = None
    error_message: Optional[str] = None


# 문서 빌드 관련 스키마
class DocumentBuildRequest(BaseModel):
    """문서 빌드 요청"""
    ast_info_list: List[Dict[str, Any]] = Field(..., description="AST 파싱 결과들")
    chunking_strategy: ChunkingStrategy = Field(ChunkingStrategy.METHOD_LEVEL, description="청킹 전략")
    chunk_size: int = Field(1000, description="청크 크기", gt=0, le=10000)
    chunk_overlap: int = Field(200, description="청크 오버랩", ge=0)
    include_metadata: bool = Field(True, description="메타데이터 포함 여부")

    @validator('chunk_overlap')
    def validate_chunk_overlap(cls, v, values):
        if 'chunk_size' in values and v >= values['chunk_size']:
            raise ValueError('chunk_overlap은 chunk_size보다 작아야 합니다')
        return v


class DocumentBuildResponse(BaseModel):
    """문서 빌드 응답"""
    success: bool
    documents: Optional[List[Dict[str, Any]]] = None
    total_documents: int = 0
    build_time_ms: Optional[int] = None
    chunking_strategy: Optional[ChunkingStrategy] = None
    error_message: Optional[str] = None


# 인덱싱 관련 스키마
class IndexingRequest(BaseModel):
    """인덱싱 요청"""
    documents: List[Dict[str, Any]] = Field(..., description="인덱싱할 문서들", min_items=1)
    collection_name: str = Field(..., description="컬렉션/인덱스 이름", min_length=1)
    vector_dimension: Optional[int] = Field(768, description="벡터 차원")
    distance_metric: Optional[str] = Field("cosine", description="거리 메트릭")
    language: Optional[str] = Field("korean", description="언어")

    @validator('collection_name')
    def validate_collection_name(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('컬렉션 이름은 영문자, 숫자, _, -만 사용 가능합니다')
        return v


class IndexingResponse(BaseModel):
    """인덱싱 응답"""
    success: bool
    indexed_count: int = 0
    collection_name: Optional[str] = None
    index_time_ms: Optional[int] = None
    error_message: Optional[str] = None


class IndexStatsResponse(BaseModel):
    """인덱스 통계 응답"""
    vector_index_stats: Optional[Dict[str, Any]] = None
    bm25_index_stats: Optional[Dict[str, Any]] = None
    total_documents: int = 0
    error_message: Optional[str] = None


# 헬스체크 관련 스키마
class ComponentStatus(BaseModel):
    """컴포넌트 상태"""
    ast_parser: bool
    document_builder: bool
    vector_index: bool
    bm25_index: bool


class HealthCheckResponse(BaseModel):
    """헬스체크 응답"""
    status: str = Field(..., description="서비스 상태", pattern="^(healthy|degraded|unhealthy)$")
    service: str
    components: ComponentStatus
    error: Optional[str] = None


# 에러 응답 스키마
class ErrorResponse(BaseModel):
    """에러 응답"""
    detail: str
    error_code: Optional[str] = None
    timestamp: Optional[str] = None


# 일괄 처리 관련 스키마
class BulkParseRequest(BaseModel):
    """일괄 파싱 요청"""
    language: Language = Field(Language.JAVA, description="프로그래밍 언어")
    extract_methods: bool = Field(True, description="메서드 추출 여부")
    extract_classes: bool = Field(True, description="클래스 추출 여부")
    extract_functions: bool = Field(True, description="함수 추출 여부")
    extract_imports: bool = Field(True, description="import 추출 여부")


class BulkParseResponse(BaseModel):
    """일괄 파싱 응답"""
    total_files: int
    successful_files: int
    failed_files: int
    results: List[ParseResponse]
    total_time_ms: int


# 파일 삭제 응답
class DeleteResponse(BaseModel):
    """삭제 응답"""
    message: str
    collection_name: Optional[str] = None
    index_name: Optional[str] = None 