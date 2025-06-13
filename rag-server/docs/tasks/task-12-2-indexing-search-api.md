# Task 16-1: 인덱싱 및 검색 API 구현

## 📋 작업 개요
Task 8-12에서 구현된 인덱싱 및 검색 기능들에 대한 API 엔드포인트를 구현합니다. AST 파싱, 문서 빌더, 벡터 인덱스, BM25 인덱스, 하이브리드 검색 기능을 위한 RESTful API를 제공합니다.

## 🎯 작업 목표
- 인덱싱 관련 API 엔드포인트 구현
- 검색 관련 API 엔드포인트 구현  
- 파일 업로드 및 처리 API 구현
- API 문서 자동 생성 및 유지보수성 향상

## 🔗 의존성
- **선행 Task**: Task 8 (AST Parser), Task 9 (Document Builder), Task 10 (Vector Index), Task 11 (BM25 Index), Task 12 (Hybrid Retriever)
- **후속 Task**: Task 16-2 (RAG 서비스 통합 API)

## 🔧 구현 사항

### 1. 인덱싱 API 라우터

```python
# app/features/indexing/router.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
import logging

from app.index.ast_parser import ASTParserService
from app.index.document_builder import DocumentBuilderService  
from app.index.vector_index import VectorIndexService
from app.index.bm25_index import BM25IndexService
from .schema import (
    ParseRequest, ParseResponse, DocumentBuildRequest, DocumentBuildResponse,
    IndexingRequest, IndexingResponse, IndexStatsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/indexing", tags=["Indexing"])

# 서비스 인스턴스들
ast_parser = ASTParserService()
document_builder = DocumentBuilderService()
vector_index = VectorIndexService()
bm25_index = BM25IndexService()

@router.post("/parse", response_model=ParseResponse, status_code=200)
async def parse_code(
    request: ParseRequest,
    background_tasks: BackgroundTasks
) -> ParseResponse:
    """
    코드 파싱 및 AST 생성
    
    - **code**: 파싱할 코드 내용
    - **language**: 프로그래밍 언어 (java, python, javascript 등)
    - **file_path**: 파일 경로 (선택사항)
    - **extract_methods**: 메서드 추출 여부
    - **extract_classes**: 클래스 추출 여부
    
    Returns:
        파싱된 AST 정보 및 추출된 코드 요소들
    """
    try:
        result = await ast_parser.parse_code(
            code=request.code,
            language=request.language,
            file_path=request.file_path,
            extract_methods=request.extract_methods,
            extract_classes=request.extract_classes,
            extract_functions=request.extract_functions,
            extract_imports=request.extract_imports
        )
        
        response = ParseResponse(
            success=True,
            ast_info=result.ast_info,
            methods=result.methods,
            classes=result.classes,
            functions=result.functions,
            imports=result.imports,
            file_info=result.file_info,
            parse_time_ms=result.parse_time_ms
        )
        
        # 백그라운드에서 파싱 통계 로깅
        background_tasks.add_task(
            log_parse_stats, 
            request.language, 
            len(request.code),
            result.parse_time_ms
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"코드 파싱 파라미터 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"잘못된 요청: {str(e)}"
        )
    except Exception as e:
        logger.error(f"코드 파싱 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="코드 파싱 중 오류가 발생했습니다"
        )

@router.post("/documents/build", response_model=DocumentBuildResponse)
async def build_documents(
    request: DocumentBuildRequest,
    background_tasks: BackgroundTasks
) -> DocumentBuildResponse:
    """
    문서 빌드
    
    파싱된 코드 정보를 기반으로 검색 가능한 문서를 생성합니다.
    """
    try:
        result = await document_builder.build_documents(
            ast_results=request.ast_results,
            chunking_strategy=request.chunking_strategy,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            include_metadata=request.include_metadata,
            enhance_content=request.enhance_content
        )
        
        response = DocumentBuildResponse(
            success=True,
            documents=result.documents,
            document_count=len(result.documents),
            total_chunks=result.total_chunks,
            build_time_ms=result.build_time_ms,
            metadata=result.metadata
        )
        
        return response
        
    except Exception as e:
        logger.error(f"문서 빌드 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 빌드 실패: {str(e)}"
        )

@router.post("/vector/index", response_model=IndexingResponse)
async def create_vector_index(
    request: IndexingRequest,
    background_tasks: BackgroundTasks
) -> IndexingResponse:
    """
    벡터 인덱스 생성
    
    문서들을 벡터화하여 인덱스에 저장합니다.
    """
    try:
        result = await vector_index.index_documents(
            documents=request.documents,
            collection_name=request.collection_name,
            batch_size=request.batch_size,
            update_existing=request.update_existing
        )
        
        response = IndexingResponse(
            success=result.success,
            indexed_count=result.indexed_count,
            failed_count=result.failed_count,
            collection_name=result.collection_name,
            index_time_ms=result.index_time_ms,
            errors=result.errors
        )
        
        return response
        
    except Exception as e:
        logger.error(f"벡터 인덱싱 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"벡터 인덱싱 실패: {str(e)}"
        )

@router.post("/bm25/index", response_model=IndexingResponse)
async def create_bm25_index(
    request: IndexingRequest,
    background_tasks: BackgroundTasks
) -> IndexingResponse:
    """
    BM25 인덱스 생성
    
    문서들을 BM25 인덱스에 저장합니다.
    """
    try:
        result = await bm25_index.index_documents(
            documents=request.documents,
            index_name=request.collection_name,
            update_existing=request.update_existing
        )
        
        response = IndexingResponse(
            success=result.success,
            indexed_count=result.indexed_count,
            failed_count=result.failed_count,
            collection_name=result.index_name,
            index_time_ms=result.index_time_ms,
            errors=result.errors
        )
        
        return response
        
    except Exception as e:
        logger.error(f"BM25 인덱싱 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BM25 인덱싱 실패: {str(e)}"
        )

@router.get("/health")
async def indexing_health_check() -> Dict[str, Any]:
    """인덱싱 서비스 헬스 체크"""
    try:
        return {
            "status": "healthy",
            "service": "indexing",
            "components": {
                "ast_parser": True,
                "document_builder": True,
                "vector_index": True,
                "bm25_index": True
            }
        }
    except Exception as e:
        logger.error(f"인덱싱 헬스 체크 실패: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "indexing"
        }

# 헬퍼 함수들
async def log_parse_stats(language: str, code_length: int, parse_time: int):
    """파싱 통계 로깅"""
    logger.info(f"Code parsed: language={language}, length={code_length}, time={parse_time}ms")
```

### 2. 검색 API 라우터

```python
# app/features/search/router.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import logging

from app.retriever.hybrid_retriever import HybridRetriever
from .schema import (
    VectorSearchRequest, VectorSearchResponse,
    BM25SearchRequest, BM25SearchResponse, 
    HybridSearchRequest, HybridSearchResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["Search"])

# 검색 서비스 인스턴스
hybrid_retriever = HybridRetriever()

@router.post("/vector", response_model=VectorSearchResponse)
async def vector_search(
    request: VectorSearchRequest
) -> VectorSearchResponse:
    """
    벡터 검색
    
    - **query**: 검색 쿼리
    - **collection_name**: 검색할 컬렉션 이름
    - **top_k**: 반환할 결과 수
    - **score_threshold**: 최소 유사도 점수
    
    Returns:
        벡터 검색 결과
    """
    try:
        results = await hybrid_retriever.vector_search(
            query=request.query,
            collection_name=request.collection_name,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            filter_metadata=request.filter_metadata
        )
        
        return VectorSearchResponse(
            success=True,
            results=results.results,
            total_results=len(results.results),
            search_time_ms=results.search_time_ms,
            collection_name=request.collection_name
        )
        
    except Exception as e:
        logger.error(f"벡터 검색 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"벡터 검색 실패: {str(e)}"
        )

@router.post("/bm25", response_model=BM25SearchResponse)
async def bm25_search(
    request: BM25SearchRequest
) -> BM25SearchResponse:
    """
    BM25 검색
    
    - **query**: 검색 쿼리
    - **index_name**: 검색할 인덱스 이름
    - **top_k**: 반환할 결과 수
    
    Returns:
        BM25 검색 결과
    """
    try:
        results = await hybrid_retriever.bm25_search(
            query=request.query,
            index_name=request.index_name,
            top_k=request.top_k,
            filter_language=request.filter_language
        )
        
        return BM25SearchResponse(
            success=True,
            results=results.results,
            total_results=len(results.results),
            search_time_ms=results.search_time_ms,
            index_name=request.index_name
        )
        
    except Exception as e:
        logger.error(f"BM25 검색 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BM25 검색 실패: {str(e)}"
        )

@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(
    request: HybridSearchRequest
) -> HybridSearchResponse:
    """
    하이브리드 검색
    
    벡터 검색과 BM25 검색을 결합한 하이브리드 검색을 수행합니다.
    """
    try:
        results = await hybrid_retriever.hybrid_search(
            query=request.query,
            collection_name=request.collection_name,
            index_name=request.index_name,
            top_k=request.top_k,
            vector_weight=request.vector_weight,
            bm25_weight=request.bm25_weight,
            use_rrf=request.use_rrf,
            rrf_k=request.rrf_k,
            score_threshold=request.score_threshold,
            filter_metadata=request.filter_metadata,
            filter_language=request.filter_language
        )
        
        return HybridSearchResponse(
            success=True,
            results=results.results,
            total_results=len(results.results),
            search_time_ms=results.search_time_ms,
            vector_results_count=results.vector_results_count,
            bm25_results_count=results.bm25_results_count,
            fusion_method=results.fusion_method,
            weights_used=results.weights_used
        )
        
    except Exception as e:
        logger.error(f"하이브리드 검색 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"하이브리드 검색 실패: {str(e)}"
        )

@router.get("/health")
async def search_health_check() -> Dict[str, Any]:
    """검색 서비스 헬스 체크"""
    try:
        health_status = await hybrid_retriever.health_check()
        return {
            "status": "healthy" if health_status["vector_index"] and health_status["bm25_index"] else "degraded",
            "components": health_status,
            "service": "search"
        }
    except Exception as e:
        logger.error(f"검색 헬스 체크 실패: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "search"
        }
```

### 3. 스키마 정의

```python
# app/features/indexing/schema.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ParseRequest(BaseModel):
    code: str = Field(..., description="파싱할 코드 내용")
    language: str = Field("java", description="프로그래밍 언어")
    file_path: Optional[str] = Field(None, description="파일 경로")
    extract_methods: bool = Field(True, description="메서드 추출 여부")
    extract_classes: bool = Field(True, description="클래스 추출 여부")
    extract_functions: bool = Field(True, description="함수 추출 여부")
    extract_imports: bool = Field(True, description="import 추출 여부")

class ParseResponse(BaseModel):
    success: bool
    ast_info: Optional[Dict[str, Any]] = None
    methods: Optional[List[Dict[str, Any]]] = None
    classes: Optional[List[Dict[str, Any]]] = None
    functions: Optional[List[Dict[str, Any]]] = None
    imports: Optional[List[str]] = None
    file_info: Optional[Dict[str, str]] = None
    parse_time_ms: Optional[int] = None
    error: Optional[str] = None

class DocumentBuildRequest(BaseModel):
    ast_results: List[Dict[str, Any]] = Field(..., description="AST 파싱 결과들")
    chunking_strategy: str = Field("semantic", description="청킹 전략")
    chunk_size: int = Field(1000, description="청크 크기")
    chunk_overlap: int = Field(200, description="청크 오버랩")
    include_metadata: bool = Field(True, description="메타데이터 포함 여부")
    enhance_content: bool = Field(True, description="콘텐츠 강화 여부")

class DocumentBuildResponse(BaseModel):
    success: bool
    documents: Optional[List[Dict[str, Any]]] = None
    document_count: int = 0
    total_chunks: int = 0
    build_time_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class IndexingRequest(BaseModel):
    documents: List[Dict[str, Any]] = Field(..., description="인덱싱할 문서들")
    collection_name: str = Field(..., description="컬렉션/인덱스 이름")
    batch_size: int = Field(100, description="배치 크기")
    update_existing: bool = Field(False, description="기존 항목 업데이트 여부")

class IndexingResponse(BaseModel):
    success: bool
    indexed_count: int = 0
    failed_count: int = 0
    collection_name: str
    index_time_ms: Optional[int] = None
    errors: Optional[List[str]] = None

class IndexStatsResponse(BaseModel):
    vector_index_stats: Dict[str, Any]
    bm25_index_stats: Dict[str, Any]
    total_documents: int
```

```python
# app/features/search/schema.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SearchResult(BaseModel):
    content: str
    score: float
    metadata: Dict[str, Any]
    document_id: Optional[str] = None

class VectorSearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리")
    collection_name: str = Field(..., description="컬렉션 이름")
    top_k: int = Field(10, description="반환할 결과 수")
    score_threshold: float = Field(0.0, description="최소 유사도 점수")
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="메타데이터 필터")

class VectorSearchResponse(BaseModel):
    success: bool
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
    collection_name: str

class BM25SearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리")
    index_name: str = Field(..., description="인덱스 이름")
    top_k: int = Field(10, description="반환할 결과 수")
    filter_language: Optional[str] = Field(None, description="언어 필터")

class BM25SearchResponse(BaseModel):
    success: bool
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
    index_name: str

class HybridSearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리")
    collection_name: str = Field(..., description="벡터 컬렉션 이름")
    index_name: str = Field(..., description="BM25 인덱스 이름")
    top_k: int = Field(10, description="반환할 결과 수")
    vector_weight: float = Field(0.7, description="벡터 검색 가중치")
    bm25_weight: float = Field(0.3, description="BM25 검색 가중치")
    use_rrf: bool = Field(True, description="RRF 사용 여부")
    rrf_k: int = Field(60, description="RRF 파라미터 k")
    score_threshold: float = Field(0.0, description="최소 점수 임계값")
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="메타데이터 필터")
    filter_language: Optional[str] = Field(None, description="언어 필터")

class HybridSearchResponse(BaseModel):
    success: bool
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
    vector_results_count: int
    bm25_results_count: int
    fusion_method: str
    weights_used: Dict[str, float]
```

## ✅ 완료 조건

1. **파싱 API**: AST 파싱 및 코드 분석 API 완전 구현
2. **문서 빌드 API**: 파싱 결과를 검색 가능한 문서로 변환하는 API
3. **인덱싱 API**: 벡터 및 BM25 인덱스 생성/관리 API
4. **검색 API**: 벡터, BM25, 하이브리드 검색 API
5. **파일 업로드**: 코드 파일 업로드 및 처리 지원
6. **에러 처리**: 모든 예외 상황 적절히 처리
7. **API 문서**: FastAPI 자동 문서 생성
8. **통계 및 모니터링**: 각 기능별 통계 정보 제공

## 📋 다음 Task와의 연관관계

- **Task 16-2**: RAG 서비스 통합 API (Task 13-15 완료 후)
- **Task 17**: 기존 개별 features 모듈들을 통합 API로 대체

## 🧪 테스트 계획

```python
# tests/unit/features/indexing/test_router.py
def test_parse_code_api(client: TestClient):
    """코드 파싱 API 테스트"""
    response = client.post("/api/v1/indexing/parse", json={
        "code": "public class Test { public void method() {} }",
        "language": "java"
    })
    assert response.status_code == 200
    assert response.json()["success"] == True

def test_vector_index_api(client: TestClient):
    """벡터 인덱싱 API 테스트"""
    response = client.post("/api/v1/indexing/vector/index", json={
        "documents": [{"content": "test content"}],
        "collection_name": "test_collection"
    })
    assert response.status_code == 200

# tests/unit/features/search/test_router.py
def test_hybrid_search_api(client: TestClient):
    """하이브리드 검색 API 테스트"""
    response = client.post("/api/v1/search/hybrid", json={
        "query": "authentication method",
        "collection_name": "test_collection",
        "index_name": "test_index"
    })
    assert response.status_code == 200
    assert "results" in response.json()
```

이 Task는 인덱싱 및 검색 관련 기능들을 REST API로 제공하여 클라이언트가 쉽게 사용할 수 있도록 합니다.

## 📋 작업 개요
Task 8-12에서 구현된 인덱싱 및 검색 기능들에 대한 API 엔드포인트를 구현합니다. AST 파싱, 문서 빌더, 벡터 인덱스, BM25 인덱스, 하이브리드 검색 기능을 위한 RESTful API를 제공합니다.

## 🎯 작업 목표
- 인덱싱 관련 API 엔드포인트 구현
- 검색 관련 API 엔드포인트 구현  
- 파일 업로드 및 처리 API 구현
- API 문서 자동 생성 및 유지보수성 향상

## 🔗 의존성
- **선행 Task**: Task 8 (AST Parser), Task 9 (Document Builder), Task 10 (Vector Index), Task 11 (BM25 Index), Task 12 (Hybrid Retriever)
- **후속 Task**: Task 16-2 (RAG 서비스 통합 API)

## 🔧 구현 사항

### 1. 인덱싱 API 라우터

```python
# app/features/indexing/router.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
import logging
from pathlib import Path

from app.index.ast_parser import ASTParserService
from app.index.document_builder import DocumentBuilderService  
from app.index.vector_index import VectorIndexService
from app.index.bm25_index import BM25IndexService
from .schema import (
    ParseRequest, ParseResponse, DocumentBuildRequest, DocumentBuildResponse,
    IndexingRequest, IndexingResponse, IndexStatsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/indexing", tags=["Indexing"])

# 서비스 인스턴스들
ast_parser = ASTParserService()
document_builder = DocumentBuilderService()
vector_index = VectorIndexService()
bm25_index = BM25IndexService()

@router.post("/parse", response_model=ParseResponse, status_code=200)
async def parse_code(
    request: ParseRequest,
    background_tasks: BackgroundTasks
) -> ParseResponse:
    """
    코드 파싱 및 AST 생성
    
    - **code**: 파싱할 코드 내용
    - **language**: 프로그래밍 언어 (java, python, javascript 등)
    - **file_path**: 파일 경로 (선택사항)
    - **extract_methods**: 메서드 추출 여부
    - **extract_classes**: 클래스 추출 여부
    
    Returns:
        파싱된 AST 정보 및 추출된 코드 요소들
    """
    try:
        result = await ast_parser.parse_code(
            code=request.code,
            language=request.language,
            file_path=request.file_path,
            extract_methods=request.extract_methods,
            extract_classes=request.extract_classes,
            extract_functions=request.extract_functions,
            extract_imports=request.extract_imports
        )
        
        response = ParseResponse(
            success=True,
            ast_info=result.ast_info,
            methods=result.methods,
            classes=result.classes,
            functions=result.functions,
            imports=result.imports,
            file_info=result.file_info,
            parse_time_ms=result.parse_time_ms
        )
        
        # 백그라운드에서 파싱 통계 로깅
        background_tasks.add_task(
            log_parse_stats, 
            request.language, 
            len(request.code),
            result.parse_time_ms
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"코드 파싱 파라미터 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"잘못된 요청: {str(e)}"
        )
    except Exception as e:
        logger.error(f"코드 파싱 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="코드 파싱 중 오류가 발생했습니다"
        )

@router.post("/parse/files", response_model=List[ParseResponse])
async def parse_files(
    files: List[UploadFile] = File(...),
    language: str = "java",
    extract_methods: bool = True,
    extract_classes: bool = True,
    extract_functions: bool = True,
    extract_imports: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> List[ParseResponse]:
    """
    여러 파일 일괄 파싱
    
    업로드된 코드 파일들을 일괄 파싱합니다.
    """
    try:
        results = []
        
        for file in files:
            try:
                # 파일 내용 읽기
                content = await file.read()
                file_content = content.decode('utf-8')
                
                # 파싱 실행
                result = await ast_parser.parse_code(
                    code=file_content,
                    language=language,
                    file_path=file.filename,
                    extract_methods=extract_methods,
                    extract_classes=extract_classes,
                    extract_functions=extract_functions,
                    extract_imports=extract_imports
                )
                
                response = ParseResponse(
                    success=True,
                    ast_info=result.ast_info,
                    methods=result.methods,
                    classes=result.classes,
                    functions=result.functions,
                    imports=result.imports,
                    file_info=result.file_info,
                    parse_time_ms=result.parse_time_ms
                )
                
                results.append(response)
                
            except Exception as e:
                logger.error(f"파일 {file.filename} 파싱 실패: {e}")
                error_response = ParseResponse(
                    success=False,
                    error=f"파일 파싱 실패: {str(e)}",
                    file_info={"filename": file.filename}
                )
                results.append(error_response)
        
        # 백그라운드 통계 업데이트
        background_tasks.add_task(
            update_bulk_parse_stats, 
            len(files), 
            len([r for r in results if r.success])
        )
        
        return results
        
    except Exception as e:
        logger.error(f"파일 일괄 파싱 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 일괄 파싱 실패: {str(e)}"
        )

@router.post("/documents/build", response_model=DocumentBuildResponse)
async def build_documents(
    request: DocumentBuildRequest,
    background_tasks: BackgroundTasks
) -> DocumentBuildResponse:
    """
    문서 빌드
    
    파싱된 코드 정보를 기반으로 검색 가능한 문서를 생성합니다.
    """
    try:
        result = await document_builder.build_documents(
            ast_results=request.ast_results,
            chunking_strategy=request.chunking_strategy,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            include_metadata=request.include_metadata,
            enhance_content=request.enhance_content
        )
        
        response = DocumentBuildResponse(
            success=True,
            documents=result.documents,
            document_count=len(result.documents),
            total_chunks=result.total_chunks,
            build_time_ms=result.build_time_ms,
            metadata=result.metadata
        )
        
        # 백그라운드 통계 업데이트
        background_tasks.add_task(
            log_document_build_stats,
            len(result.documents),
            result.total_chunks,
            result.build_time_ms
        )
        
        return response
        
    except Exception as e:
        logger.error(f"문서 빌드 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 빌드 실패: {str(e)}"
        )

@router.post("/vector/index", response_model=IndexingResponse)
async def create_vector_index(
    request: IndexingRequest,
    background_tasks: BackgroundTasks
) -> IndexingResponse:
    """
    벡터 인덱스 생성
    
    문서들을 벡터화하여 인덱스에 저장합니다.
    """
    try:
        result = await vector_index.index_documents(
            documents=request.documents,
            collection_name=request.collection_name,
            batch_size=request.batch_size,
            update_existing=request.update_existing
        )
        
        response = IndexingResponse(
            success=result.success,
            indexed_count=result.indexed_count,
            failed_count=result.failed_count,
            collection_name=result.collection_name,
            index_time_ms=result.index_time_ms,
            errors=result.errors
        )
        
        # 백그라운드 통계 업데이트
        background_tasks.add_task(
            update_vector_index_stats,
            result.collection_name,
            result.indexed_count
        )
        
        return response
        
    except Exception as e:
        logger.error(f"벡터 인덱싱 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"벡터 인덱싱 실패: {str(e)}"
        )

@router.post("/bm25/index", response_model=IndexingResponse)
async def create_bm25_index(
    request: IndexingRequest,
    background_tasks: BackgroundTasks
) -> IndexingResponse:
    """
    BM25 인덱스 생성
    
    문서들을 BM25 인덱스에 저장합니다.
    """
    try:
        result = await bm25_index.index_documents(
            documents=request.documents,
            index_name=request.collection_name,
            update_existing=request.update_existing
        )
        
        response = IndexingResponse(
            success=result.success,
            indexed_count=result.indexed_count,
            failed_count=result.failed_count,
            collection_name=result.index_name,
            index_time_ms=result.index_time_ms,
            errors=result.errors
        )
        
        # 백그라운드 통계 업데이트
        background_tasks.add_task(
            update_bm25_index_stats,
            result.index_name,
            result.indexed_count
        )
        
        return response
        
    except Exception as e:
        logger.error(f"BM25 인덱싱 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BM25 인덱싱 실패: {str(e)}"
        )

@router.get("/stats", response_model=IndexStatsResponse)
async def get_index_stats() -> IndexStatsResponse:
    """
    인덱스 통계 조회
    
    벡터 인덱스와 BM25 인덱스의 통계 정보를 반환합니다.
    """
    try:
        vector_stats = await vector_index.get_stats()
        bm25_stats = await bm25_index.get_stats()
        
        return IndexStatsResponse(
            vector_index_stats=vector_stats,
            bm25_index_stats=bm25_stats,
            total_documents=vector_stats.get("total_documents", 0) + bm25_stats.get("total_documents", 0)
        )
        
    except Exception as e:
        logger.error(f"인덱스 통계 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인덱스 통계 조회 실패"
        )

@router.delete("/vector/{collection_name}")
async def delete_vector_collection(collection_name: str) -> Dict[str, str]:
    """벡터 컬렉션 삭제"""
    try:
        await vector_index.delete_collection(collection_name)
        return {"message": f"컬렉션 '{collection_name}'이 삭제되었습니다"}
    except Exception as e:
        logger.error(f"벡터 컬렉션 삭제 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"컬렉션 삭제 실패: {str(e)}"
        )

@router.delete("/bm25/{index_name}")
async def delete_bm25_index(index_name: str) -> Dict[str, str]:
    """BM25 인덱스 삭제"""
    try:
        await bm25_index.delete_index(index_name)
        return {"message": f"인덱스 '{index_name}'이 삭제되었습니다"}
    except Exception as e:
        logger.error(f"BM25 인덱스 삭제 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인덱스 삭제 실패: {str(e)}"
        )

# 헬퍼 함수들
async def log_parse_stats(language: str, code_length: int, parse_time: int):
    """파싱 통계 로깅"""
    logger.info(f"Code parsed: language={language}, length={code_length}, time={parse_time}ms")

async def update_bulk_parse_stats(total_files: int, success_files: int):
    """일괄 파싱 통계 업데이트"""  
    logger.info(f"Bulk parsing completed: {success_files}/{total_files} files")

async def log_document_build_stats(doc_count: int, chunk_count: int, build_time: int):
    """문서 빌드 통계 로깅"""
    logger.info(f"Documents built: docs={doc_count}, chunks={chunk_count}, time={build_time}ms")

async def update_vector_index_stats(collection_name: str, indexed_count: int):
    """벡터 인덱스 통계 업데이트"""
    logger.info(f"Vector index updated: collection={collection_name}, count={indexed_count}")

async def update_bm25_index_stats(index_name: str, indexed_count: int):
    """BM25 인덱스 통계 업데이트"""
    logger.info(f"BM25 index updated: index={index_name}, count={indexed_count}")
```

### 2. 검색 API 라우터

```python
# app/features/search/router.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import logging

from app.retriever.hybrid_retriever import HybridRetriever
from .schema import (
    SearchRequest, SearchResponse, VectorSearchRequest, VectorSearchResponse,
    BM25SearchRequest, BM25SearchResponse, HybridSearchRequest, HybridSearchResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["Search"])

# 검색 서비스 인스턴스
hybrid_retriever = HybridRetriever()

@router.post("/vector", response_model=VectorSearchResponse)
async def vector_search(
    request: VectorSearchRequest
) -> VectorSearchResponse:
    """
    벡터 검색
    
    - **query**: 검색 쿼리
    - **collection_name**: 검색할 컬렉션 이름
    - **top_k**: 반환할 결과 수
    - **score_threshold**: 최소 유사도 점수
    
    Returns:
        벡터 검색 결과
    """
    try:
        results = await hybrid_retriever.vector_search(
            query=request.query,
            collection_name=request.collection_name,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            filter_metadata=request.filter_metadata
        )
        
        return VectorSearchResponse(
            success=True,
            results=results.results,
            total_results=len(results.results),
            search_time_ms=results.search_time_ms,
            collection_name=request.collection_name
        )
        
    except Exception as e:
        logger.error(f"벡터 검색 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"벡터 검색 실패: {str(e)}"
        )

@router.post("/bm25", response_model=BM25SearchResponse)
async def bm25_search(
    request: BM25SearchRequest
) -> BM25SearchResponse:
    """
    BM25 검색
    
    - **query**: 검색 쿼리
    - **index_name**: 검색할 인덱스 이름
    - **top_k**: 반환할 결과 수
    
    Returns:
        BM25 검색 결과
    """
    try:
        results = await hybrid_retriever.bm25_search(
            query=request.query,
            index_name=request.index_name,
            top_k=request.top_k,
            filter_language=request.filter_language
        )
        
        return BM25SearchResponse(
            success=True,
            results=results.results,
            total_results=len(results.results),
            search_time_ms=results.search_time_ms,
            index_name=request.index_name
        )
        
    except Exception as e:
        logger.error(f"BM25 검색 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BM25 검색 실패: {str(e)}"
        )

@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(
    request: HybridSearchRequest
) -> HybridSearchResponse:
    """
    하이브리드 검색
    
    벡터 검색과 BM25 검색을 결합한 하이브리드 검색을 수행합니다.
    
    - **query**: 검색 쿼리
    - **collection_name**: 벡터 컬렉션 이름
    - **index_name**: BM25 인덱스 이름
    - **top_k**: 반환할 결과 수
    - **vector_weight**: 벡터 검색 가중치 (0.0 ~ 1.0)
    - **bm25_weight**: BM25 검색 가중치 (0.0 ~ 1.0)
    - **use_rrf**: Reciprocal Rank Fusion 사용 여부
    
    Returns:
        하이브리드 검색 결과
    """
    try:
        results = await hybrid_retriever.hybrid_search(
            query=request.query,
            collection_name=request.collection_name,
            index_name=request.index_name,
            top_k=request.top_k,
            vector_weight=request.vector_weight,
            bm25_weight=request.bm25_weight,
            use_rrf=request.use_rrf,
            rrf_k=request.rrf_k,
            score_threshold=request.score_threshold,
            filter_metadata=request.filter_metadata,
            filter_language=request.filter_language
        )
        
        return HybridSearchResponse(
            success=True,
            results=results.results,
            total_results=len(results.results),
            search_time_ms=results.search_time_ms,
            vector_results_count=results.vector_results_count,
            bm25_results_count=results.bm25_results_count,
            fusion_method=results.fusion_method,
            weights_used=results.weights_used
        )
        
    except Exception as e:
        logger.error(f"하이브리드 검색 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"하이브리드 검색 실패: {str(e)}"
        )

@router.get("/health")
async def search_health_check() -> Dict[str, Any]:
    """검색 서비스 헬스 체크"""
    try:
        health_status = await hybrid_retriever.health_check()
        return {
            "status": "healthy" if health_status["vector_index"] and health_status["bm25_index"] else "degraded",
            "components": health_status,
            "service": "search"
        }
    except Exception as e:
        logger.error(f"검색 헬스 체크 실패: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "search"
        }
```

### 3. 스키마 정의

```python
# app/features/indexing/schema.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ParseRequest(BaseModel):
    code: str = Field(..., description="파싱할 코드 내용")
    language: str = Field("java", description="프로그래밍 언어")
    file_path: Optional[str] = Field(None, description="파일 경로")
    extract_methods: bool = Field(True, description="메서드 추출 여부")
    extract_classes: bool = Field(True, description="클래스 추출 여부")
    extract_functions: bool = Field(True, description="함수 추출 여부")
    extract_imports: bool = Field(True, description="import 추출 여부")

class ParseResponse(BaseModel):
    success: bool
    ast_info: Optional[Dict[str, Any]] = None
    methods: Optional[List[Dict[str, Any]]] = None
    classes: Optional[List[Dict[str, Any]]] = None
    functions: Optional[List[Dict[str, Any]]] = None
    imports: Optional[List[str]] = None
    file_info: Optional[Dict[str, str]] = None
    parse_time_ms: Optional[int] = None
    error: Optional[str] = None

class DocumentBuildRequest(BaseModel):
    ast_results: List[Dict[str, Any]] = Field(..., description="AST 파싱 결과들")
    chunking_strategy: str = Field("semantic", description="청킹 전략")
    chunk_size: int = Field(1000, description="청크 크기")
    chunk_overlap: int = Field(200, description="청크 오버랩")
    include_metadata: bool = Field(True, description="메타데이터 포함 여부")
    enhance_content: bool = Field(True, description="콘텐츠 강화 여부")

class DocumentBuildResponse(BaseModel):
    success: bool
    documents: Optional[List[Dict[str, Any]]] = None
    document_count: int = 0
    total_chunks: int = 0
    build_time_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class IndexingRequest(BaseModel):
    documents: List[Dict[str, Any]] = Field(..., description="인덱싱할 문서들")
    collection_name: str = Field(..., description="컬렉션/인덱스 이름")
    batch_size: int = Field(100, description="배치 크기")
    update_existing: bool = Field(False, description="기존 항목 업데이트 여부")

class IndexingResponse(BaseModel):
    success: bool
    indexed_count: int = 0
    failed_count: int = 0
    collection_name: str
    index_time_ms: Optional[int] = None
    errors: Optional[List[str]] = None

class IndexStatsResponse(BaseModel):
    vector_index_stats: Dict[str, Any]
    bm25_index_stats: Dict[str, Any]
    total_documents: int
```

```python
# app/features/search/schema.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SearchResult(BaseModel):
    content: str
    score: float
    metadata: Dict[str, Any]
    document_id: Optional[str] = None

class VectorSearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리")
    collection_name: str = Field(..., description="컬렉션 이름")
    top_k: int = Field(10, description="반환할 결과 수")
    score_threshold: float = Field(0.0, description="최소 유사도 점수")
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="메타데이터 필터")

class VectorSearchResponse(BaseModel):
    success: bool
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
    collection_name: str

class BM25SearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리")
    index_name: str = Field(..., description="인덱스 이름")
    top_k: int = Field(10, description="반환할 결과 수")
    filter_language: Optional[str] = Field(None, description="언어 필터")

class BM25SearchResponse(BaseModel):
    success: bool
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
    index_name: str

class HybridSearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리")
    collection_name: str = Field(..., description="벡터 컬렉션 이름")
    index_name: str = Field(..., description="BM25 인덱스 이름")
    top_k: int = Field(10, description="반환할 결과 수")
    vector_weight: float = Field(0.7, description="벡터 검색 가중치")
    bm25_weight: float = Field(0.3, description="BM25 검색 가중치")
    use_rrf: bool = Field(True, description="RRF 사용 여부")
    rrf_k: int = Field(60, description="RRF 파라미터 k")
    score_threshold: float = Field(0.0, description="최소 점수 임계값")
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="메타데이터 필터")
    filter_language: Optional[str] = Field(None, description="언어 필터")

class HybridSearchResponse(BaseModel):
    success: bool
    results: List[SearchResult]
    total_results: int
    search_time_ms: int
    vector_results_count: int
    bm25_results_count: int
    fusion_method: str
    weights_used: Dict[str, float]
```

## ✅ 완료 조건

1. **파싱 API**: AST 파싱 및 코드 분석 API 완전 구현
2. **문서 빌드 API**: 파싱 결과를 검색 가능한 문서로 변환하는 API
3. **인덱싱 API**: 벡터 및 BM25 인덱스 생성/관리 API
4. **검색 API**: 벡터, BM25, 하이브리드 검색 API
5. **파일 업로드**: 코드 파일 업로드 및 처리 지원
6. **에러 처리**: 모든 예외 상황 적절히 처리
7. **API 문서**: FastAPI 자동 문서 생성
8. **통계 및 모니터링**: 각 기능별 통계 정보 제공

## 📋 다음 Task와의 연관관계

- **Task 16-2**: RAG 서비스 통합 API (Task 13-15 완료 후)
- **Task 17**: 기존 개별 features 모듈들을 통합 API로 대체

## 🧪 테스트 계획

```python
# tests/unit/features/indexing/test_router.py
def test_parse_code_api(client: TestClient):
    """코드 파싱 API 테스트"""
    response = client.post("/api/v1/indexing/parse", json={
        "code": "public class Test { public void method() {} }",
        "language": "java"
    })
    assert response.status_code == 200
    assert response.json()["success"] == True

def test_vector_index_api(client: TestClient):
    """벡터 인덱싱 API 테스트"""
    response = client.post("/api/v1/indexing/vector/index", json={
        "documents": [{"content": "test content"}],
        "collection_name": "test_collection"
    })
    assert response.status_code == 200

# tests/unit/features/search/test_router.py
def test_hybrid_search_api(client: TestClient):
    """하이브리드 검색 API 테스트"""
    response = client.post("/api/v1/search/hybrid", json={
        "query": "authentication method",
        "collection_name": "test_collection",
        "index_name": "test_index"
    })
    assert response.status_code == 200
    assert "results" in response.json()
```

이 Task는 인덱싱 및 검색 관련 기능들을 REST API로 제공하여 클라이언트가 쉽게 사용할 수 있도록 합니다.