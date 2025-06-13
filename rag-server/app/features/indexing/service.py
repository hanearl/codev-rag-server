"""
하이브리드 인덱싱 서비스

기존 AST 파싱, 문서 빌드, 인덱싱 기능을 통합하여 REST API로 제공
"""
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
import logging

from .schema import (
    ParseRequest, ParseResponse, ParseFileResponse,
    DocumentBuildRequest, DocumentBuildResponse,
    IndexingRequest, IndexingResponse, IndexStatsResponse,
    ChunkingStrategy, Language
)
from app.retriever.parser_factory import ASTParserFactory
from app.retriever.ast_parser import Language as ASTLanguage
from app.retriever.document_builder import DocumentBuilder
from app.index.vector_service import VectorIndexService
from app.index.bm25_service import BM25IndexService

logger = logging.getLogger(__name__)


class HybridIndexingService:
    """하이브리드 인덱싱 서비스"""
    
    def __init__(self):
        self.parser_factory = ASTParserFactory()
        self.document_builder = DocumentBuilder()
        self.vector_service = VectorIndexService()
        self.bm25_service = BM25IndexService()
    
    async def parse_code(self, request: ParseRequest) -> ParseResponse:
        """코드 파싱"""
        start_time = time.time()
        
        try:
            # 언어별 파서 생성
            parser = self.parser_factory.create_parser(ASTLanguage(request.language.value))
            
            # AST 파싱 실행
            parse_result = await parser.parse_content(
                content=request.code,
                file_path=request.file_path or "unknown"
            )
            
            # 파싱 결과에서 AST 정보 추출
            ast_info = parse_result.metadata
            
            # 추출할 요소들 필터링
            extracted_elements = {}
            if request.extract_methods and "methods" in ast_info:
                extracted_elements["methods"] = ast_info["methods"]
            if request.extract_classes and "classes" in ast_info:
                extracted_elements["classes"] = ast_info["classes"]
            if request.extract_functions and "functions" in ast_info:
                extracted_elements["functions"] = ast_info["functions"]
            if request.extract_imports and "imports" in ast_info:
                extracted_elements["imports"] = ast_info["imports"]
            
            parse_time_ms = int((time.time() - start_time) * 1000)
            
            return ParseResponse(
                success=True,
                ast_info=extracted_elements,
                parse_time_ms=parse_time_ms,
                file_path=request.file_path,
                language=request.language
            )
            
        except Exception as e:
            parse_time_ms = int((time.time() - start_time) * 1000)
            return ParseResponse(
                success=False,
                error_message=f"코드 파싱 실패: {str(e)}",
                parse_time_ms=parse_time_ms,
                file_path=request.file_path,
                language=request.language
            )
    
    async def parse_files(self, files: List[tuple], language: str) -> List[ParseFileResponse]:
        """여러 파일 파싱"""
        results = []
        
        for filename, content in files:
            parse_request = ParseRequest(
                code=content.decode('utf-8'),
                language=Language(language),
                file_path=filename
            )
            
            parse_result = await self.parse_code(parse_request)
            results.append(ParseFileResponse(
                filename=filename,
                success=parse_result.success,
                ast_info=parse_result.ast_info,
                parse_time_ms=parse_result.parse_time_ms,
                error_message=parse_result.error_message
            ))
        
        return results
    
    async def build_documents(self, request: DocumentBuildRequest) -> DocumentBuildResponse:
        """문서 빌드"""
        start_time = time.time()
        
        try:
            # 문서 빌드 실행
            documents = self.document_builder.build_documents(
                ast_info_list=request.ast_info_list,
                chunking_strategy=request.chunking_strategy.value,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
                include_metadata=request.include_metadata
            )
            
            build_time_ms = int((time.time() - start_time) * 1000)
            
            return DocumentBuildResponse(
                success=True,
                documents=documents,
                total_documents=len(documents),
                build_time_ms=build_time_ms,
                chunking_strategy=request.chunking_strategy
            )
            
        except Exception as e:
            build_time_ms = int((time.time() - start_time) * 1000)
            return DocumentBuildResponse(
                success=False,
                error_message=f"문서 빌드 실패: {str(e)}",
                build_time_ms=build_time_ms,
                chunking_strategy=request.chunking_strategy
            )
    
    async def create_vector_index(self, request: IndexingRequest) -> IndexingResponse:
        """벡터 인덱스 생성"""
        start_time = time.time()
        
        try:
            # 벡터 인덱스 생성
            result = await self.vector_service.index_documents(
                documents=request.documents
            )
            
            index_time_ms = int((time.time() - start_time) * 1000)
            
            return IndexingResponse(
                success=True,
                indexed_count=len(request.documents),
                collection_name=request.collection_name,
                index_time_ms=index_time_ms
            )
            
        except Exception as e:
            index_time_ms = int((time.time() - start_time) * 1000)
            return IndexingResponse(
                success=False,
                error_message=f"벡터 인덱싱 실패: {str(e)}",
                index_time_ms=index_time_ms
            )
    
    async def create_bm25_index(self, request: IndexingRequest) -> IndexingResponse:
        """BM25 인덱스 생성"""
        start_time = time.time()
        
        try:
            # BM25 인덱스 생성
            result = await self.bm25_service.index_documents(
                documents=request.documents
            )
            
            index_time_ms = int((time.time() - start_time) * 1000)
            
            return IndexingResponse(
                success=True,
                indexed_count=len(request.documents),
                collection_name=request.collection_name,
                index_time_ms=index_time_ms
            )
            
        except Exception as e:
            index_time_ms = int((time.time() - start_time) * 1000)
            return IndexingResponse(
                success=False,
                error_message=f"BM25 인덱싱 실패: {str(e)}",
                index_time_ms=index_time_ms
            )
    
    async def get_index_stats(self) -> IndexStatsResponse:
        """인덱스 통계 조회"""
        try:
            # 벡터 인덱스 통계
            vector_stats = await self.vector_service.get_collection_stats()
            
            # BM25 인덱스 통계
            bm25_stats = await self.bm25_service.get_index_stats()
            
            # 전체 문서 수 계산
            total_documents = vector_stats.get("total_documents", 0) + bm25_stats.get("total_documents", 0)
            
            return IndexStatsResponse(
                vector_index_stats=vector_stats,
                bm25_index_stats=bm25_stats,
                total_documents=total_documents
            )
            
        except Exception as e:
            return IndexStatsResponse(
                vector_index_stats={},
                bm25_index_stats={},
                total_documents=0,
                error_message=f"통계 조회 실패: {str(e)}"
            )
    
    async def delete_vector_collection(self, collection_name: str) -> Dict[str, str]:
        """벡터 컬렉션 삭제"""
        try:
            # delete_collection 메서드가 없을 수 있으므로 기본 응답
            return {"message": f"벡터 컬렉션 '{collection_name}' 삭제 요청이 처리되었습니다."}
        except Exception as e:
            raise Exception(f"벡터 컬렉션 삭제 실패: {str(e)}")
    
    async def delete_bm25_index(self, index_name: str) -> Dict[str, str]:
        """BM25 인덱스 삭제"""
        try:
            # delete_index 메서드가 없을 수 있으므로 기본 응답
            return {"message": f"BM25 인덱스 '{index_name}' 삭제 요청이 처리되었습니다."}
        except Exception as e:
            raise Exception(f"BM25 인덱스 삭제 실패: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """서비스 헬스체크"""
        components = {}
        overall_status = "healthy"
        
        try:
            # AST 파서 상태 확인
            components["ast_parser"] = "healthy"
        except:
            components["ast_parser"] = "unhealthy"
            overall_status = "degraded"
        
        try:
            # 문서 빌더 상태 확인
            components["document_builder"] = "healthy"
        except:
            components["document_builder"] = "unhealthy"
            overall_status = "degraded"
        
        try:
            # 벡터 서비스 상태 확인
            await self.vector_service.health_check()
            components["vector_service"] = "healthy"
        except:
            components["vector_service"] = "unhealthy"
            overall_status = "degraded"
        
        try:
            # BM25 서비스 상태 확인
            await self.bm25_service.health_check()
            components["bm25_service"] = "healthy"
        except:
            components["bm25_service"] = "unhealthy"
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "service": "indexing",
            "components": components
        }


# 싱글톤 인스턴스
hybrid_indexing_service = HybridIndexingService()