from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class IndexingRequest(BaseModel):
    file_path: str = Field(..., description="인덱싱할 파일 경로")
    force_update: bool = Field(default=False, description="강제 업데이트 여부")

class BatchIndexingRequest(BaseModel):
    file_paths: List[str] = Field(..., description="인덱싱할 파일 경로 목록")
    force_update: bool = Field(default=False, description="강제 업데이트 여부")

class IndexingResponse(BaseModel):
    file_path: str
    chunks_count: int
    message: str
    indexed_at: datetime

class BatchIndexingResponse(BaseModel):
    total_files: int
    successful_files: int
    failed_files: int
    total_chunks: int
    results: List[IndexingResponse]
    errors: List[str]

class ChunkQueryRequest(BaseModel):
    file_path: Optional[str] = Field(None, description="특정 파일의 청크만 조회")
    code_type: Optional[str] = Field(None, description="코드 타입 필터 (function, class, method)")
    language: Optional[str] = Field(None, description="언어 타입 필터 (python, java, javascript)")
    keyword: Optional[str] = Field(None, description="키워드 검색")
    page: int = Field(1, ge=1, description="페이지 번호")
    size: int = Field(10, ge=1, le=100, description="페이지 크기")

class CodeChunkResponse(BaseModel):
    id: str
    file_path: str
    function_name: Optional[str]
    code_content: str
    code_type: str
    language: str
    line_start: int
    line_end: int
    keywords: List[str]
    indexed_at: datetime

class ChunkQueryResponse(BaseModel):
    chunks: List[CodeChunkResponse]
    total: int
    page: int
    size: int
    total_pages: int

# JSON 기반 인덱싱 스키마
class AnalyzedMethod(BaseModel):
    name: str
    returnType: Optional[str]
    params: List[str]

class AnalyzedClass(BaseModel):
    name: str
    methods: List[AnalyzedMethod]

class CodeAnalysisData(BaseModel):
    filePath: str = Field(..., description="원본 파일 경로")
    language: str = Field(..., description="언어 타입 (java, python, javascript)")
    framework: Optional[str] = Field(None, description="프레임워크 (spring-boot 등)")
    module: Optional[str] = Field(None, description="모듈 타입 (controller, service, dto 등)")
    code: str = Field(..., description="실제 소스 코드")
    classes: Optional[List[AnalyzedClass]] = Field(None, description="파싱된 클래스 정보")
    references: Optional[List[str]] = Field(None, description="참조된 클래스/모듈 목록")
    analysis_timestamp: Optional[str] = Field(None, description="분석 시점")

class JsonIndexingRequest(BaseModel):
    analysis_data: CodeAnalysisData = Field(..., description="분석된 코드 데이터")
    force_update: bool = Field(default=False, description="강제 업데이트 여부")

class JsonBatchIndexingRequest(BaseModel):
    analysis_data_list: List[CodeAnalysisData] = Field(..., description="분석된 코드 데이터 목록")
    force_update: bool = Field(default=False, description="강제 업데이트 여부")