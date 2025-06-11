import os
from typing import List, Dict, Any
from datetime import datetime
import logging

from .schema import (
    IndexingRequest, IndexingResponse, BatchIndexingRequest, BatchIndexingResponse,
    ChunkQueryRequest, ChunkQueryResponse, CodeChunkResponse,
    JsonIndexingRequest, JsonBatchIndexingRequest, CodeAnalysisData
)
from .parser_factory import CodeParserFactory
from app.core.clients import EmbeddingClient, VectorClient

logger = logging.getLogger(__name__)

class IndexingService:
    def __init__(self, embedding_client: EmbeddingClient, 
                 vector_client: VectorClient, parser_factory: CodeParserFactory):
        self.embedding_client = embedding_client
        self.vector_client = vector_client
        self.parser_factory = parser_factory
        self.collection_name = "code_chunks"
    
    async def index_file(self, request: IndexingRequest) -> IndexingResponse:
        """단일 파일 인덱싱"""
        if not os.path.exists(request.file_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {request.file_path}")
        
        try:
            # 파일 확장자에 맞는 파서 선택
            parser = self.parser_factory.create_parser_for_file(request.file_path)
            
            # 코드 파싱
            parse_result = parser.parse_file(request.file_path)
            
            if not parse_result.chunks:
                return IndexingResponse(
                    file_path=request.file_path,
                    chunks_count=0,
                    message="처리할 코드 청크가 없습니다.",
                    indexed_at=datetime.now()
                )
            
            # 강제 업데이트 시 기존 데이터 삭제
            if request.force_update:
                self.vector_client.delete_by_file_path(self.collection_name, request.file_path)
            
            # 임베딩 생성
            texts = [chunk.code_content for chunk in parse_result.chunks]
            embedding_response = await self.embedding_client.embed_bulk({"texts": texts})
            embeddings = [emb["embedding"] for emb in embedding_response["embeddings"]]
            
            # 벡터 DB에 저장
            inserted_count = 0
            for chunk, embedding in zip(parse_result.chunks, embeddings):
                metadata = {
                    "file_path": chunk.file_path,
                    "name": chunk.name,
                    "code_content": chunk.code_content,
                    "code_type": chunk.code_type.value,
                    "language": chunk.language.value,
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                    "keywords": chunk.keywords,
                    "namespace": chunk.namespace,
                    "parent_class": chunk.parent_class,
                    "annotations": chunk.annotations or [],
                    "modifiers": chunk.modifiers or [],
                    "return_type": chunk.return_type,
                    "parameters": chunk.parameters or [],
                    "extends": chunk.extends,
                    "implements": chunk.implements or [],
                    "language_specific": chunk.language_specific or {},
                    "indexed_at": datetime.now().isoformat()
                }
                
                point_id = self.vector_client.insert_code_embedding(
                    self.collection_name, embedding, metadata
                )
                
                if point_id:
                    inserted_count += 1
            
            message = f"인덱싱 성공: {inserted_count}개 청크 처리"
            if request.force_update:
                message += " (기존 데이터 업데이트)"
            
            return IndexingResponse(
                file_path=request.file_path,
                chunks_count=inserted_count,
                message=message,
                indexed_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"파일 인덱싱 실패 ({request.file_path}): {e}")
            raise
    
    async def index_batch(self, request: BatchIndexingRequest) -> BatchIndexingResponse:
        """배치 파일 인덱싱"""
        results = []
        errors = []
        total_chunks = 0
        successful_files = 0
        
        for file_path in request.file_paths:
            try:
                file_request = IndexingRequest(
                    file_path=file_path, 
                    force_update=request.force_update
                )
                result = await self.index_file(file_request)
                results.append(result)
                total_chunks += result.chunks_count
                successful_files += 1
                
            except Exception as e:
                error_msg = f"{file_path}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"배치 인덱싱 오류: {error_msg}")
        
        return BatchIndexingResponse(
            total_files=len(request.file_paths),
            successful_files=successful_files,
            failed_files=len(request.file_paths) - successful_files,
            total_chunks=total_chunks,
            results=results,
            errors=errors
        )
    
    async def query_chunks(self, request: ChunkQueryRequest) -> ChunkQueryResponse:
        """청크 조회"""
        try:
            # 페이지네이션 계산
            offset = (request.page - 1) * request.size
            
            # 벡터 DB에서 청크 조회
            chunks_data, total_count = self.vector_client.query_chunks(
                collection_name=self.collection_name,
                file_path=request.file_path,
                code_type=request.code_type,
                language=request.language,
                keyword=request.keyword,
                offset=offset,
                limit=request.size
            )
            
            # 응답 객체로 변환
            chunks = []
            for chunk_data in chunks_data:
                chunk_response = CodeChunkResponse(
                    id=chunk_data["id"],
                    file_path=chunk_data["file_path"],
                    function_name=chunk_data.get("function_name"),
                    code_content=chunk_data["code_content"],
                    code_type=chunk_data["code_type"],
                    language=chunk_data["language"],
                    line_start=chunk_data["line_start"],
                    line_end=chunk_data["line_end"],
                    keywords=chunk_data["keywords"],
                    indexed_at=datetime.fromisoformat(chunk_data["indexed_at"])
                )
                chunks.append(chunk_response)
            
            # 총 페이지 수 계산
            total_pages = (total_count + request.size - 1) // request.size if total_count > 0 else 0
            
            return ChunkQueryResponse(
                chunks=chunks,
                total=total_count,
                page=request.page,
                size=request.size,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error(f"청크 조회 실패: {e}")
            raise 
    
    async def index_from_json(self, request: JsonIndexingRequest) -> IndexingResponse:
        """JSON 분석 데이터를 통한 인덱싱"""
        try:
            analysis_data = request.analysis_data
            
            # 언어 타입 매핑
            language_mapping = {
                "java": "java",
                "python": "python", 
                "javascript": "javascript"
            }
            
            language = language_mapping.get(analysis_data.language.lower())
            if not language:
                raise ValueError(f"지원하지 않는 언어입니다: {analysis_data.language}")
            
            # 코드를 청크로 분할 (간단한 방식으로 클래스별/메서드별 분할)
            chunks_data = []
            
            # 전체 파일을 하나의 청크로 처리
            chunks_data.append({
                "file_path": analysis_data.filePath,
                "name": f"File_{analysis_data.filePath.split('/')[-1]}",
                "code_content": analysis_data.code,
                "code_type": "file",
                "language": language,
                "line_start": 1,
                "line_end": len(analysis_data.code.split('\n')),
                "keywords": self._extract_keywords_from_analysis(analysis_data),
                "namespace": self._extract_namespace(analysis_data),
                "parent_class": None,
                "annotations": [],
                "modifiers": [],
                "return_type": None,
                "parameters": [],
                "extends": None,
                "implements": [],
                "language_specific": {
                    "framework": analysis_data.framework,
                    "module": analysis_data.module,
                    "references": analysis_data.references or []
                }
            })
            
            # 클래스별 청크 생성
            if analysis_data.classes:
                for cls in analysis_data.classes:
                    # 클래스 청크
                    chunks_data.append({
                        "file_path": analysis_data.filePath,
                        "name": cls.name,
                        "code_content": f"class {cls.name}",
                        "code_type": "class",
                        "language": language,
                        "line_start": 1,
                        "line_end": 1,
                        "keywords": [cls.name] + (analysis_data.references or []),
                        "namespace": self._extract_namespace(analysis_data),
                        "parent_class": None,
                        "annotations": [],
                        "modifiers": [],
                        "return_type": None,
                        "parameters": [],
                        "extends": None,
                        "implements": [],
                        "language_specific": {
                            "framework": analysis_data.framework,
                            "module": analysis_data.module
                        }
                    })
                    
                    # 메서드별 청크
                    for method in cls.methods:
                        chunks_data.append({
                            "file_path": analysis_data.filePath,
                            "name": method.name,
                            "code_content": f"{method.returnType or 'void'} {method.name}({', '.join(method.params)})",
                            "code_type": "method",
                            "language": language,
                            "line_start": 1,
                            "line_end": 1,
                            "keywords": [method.name, cls.name] + method.params,
                            "namespace": self._extract_namespace(analysis_data),
                            "parent_class": cls.name,
                            "annotations": [],
                            "modifiers": [],
                            "return_type": method.returnType,
                            "parameters": method.params,
                            "extends": None,
                            "implements": [],
                            "language_specific": {
                                "framework": analysis_data.framework,
                                "module": analysis_data.module
                            }
                        })
            
            if not chunks_data:
                return IndexingResponse(
                    file_path=analysis_data.filePath,
                    chunks_count=0,
                    message="처리할 코드 청크가 없습니다.",
                    indexed_at=datetime.now()
                )
            
            # 강제 업데이트 시 기존 데이터 삭제
            if request.force_update:
                self.vector_client.delete_by_file_path(self.collection_name, analysis_data.filePath)
            
            # 임베딩 생성
            texts = [chunk["code_content"] for chunk in chunks_data]
            embedding_response = await self.embedding_client.embed_bulk({"texts": texts})
            embeddings = [emb["embedding"] for emb in embedding_response["embeddings"]]
            
            # 벡터 DB에 저장
            inserted_count = 0
            for chunk_data, embedding in zip(chunks_data, embeddings):
                metadata = {
                    **chunk_data,
                    "indexed_at": datetime.now().isoformat()
                }
                
                point_id = self.vector_client.insert_code_embedding(
                    self.collection_name, embedding, metadata
                )
                
                if point_id:
                    inserted_count += 1
            
            message = f"JSON 인덱싱 성공: {inserted_count}개 청크 처리"
            if request.force_update:
                message += " (기존 데이터 업데이트)"
            
            return IndexingResponse(
                file_path=analysis_data.filePath,
                chunks_count=inserted_count,
                message=message,
                indexed_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"JSON 인덱싱 실패 ({analysis_data.filePath}): {e}")
            raise
    
    async def index_batch_from_json(self, request: JsonBatchIndexingRequest) -> BatchIndexingResponse:
        """배치 JSON 인덱싱"""
        results = []
        errors = []
        total_chunks = 0
        successful_files = 0
        
        for analysis_data in request.analysis_data_list:
            try:
                json_request = JsonIndexingRequest(
                    analysis_data=analysis_data,
                    force_update=request.force_update
                )
                result = await self.index_from_json(json_request)
                results.append(result)
                total_chunks += result.chunks_count
                successful_files += 1
                
            except Exception as e:
                error_msg = f"{analysis_data.filePath}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"배치 JSON 인덱싱 오류: {error_msg}")
        
        return BatchIndexingResponse(
            total_files=len(request.analysis_data_list),
            successful_files=successful_files,
            failed_files=len(request.analysis_data_list) - successful_files,
            total_chunks=total_chunks,
            results=results,
            errors=errors
        )
    
    def _extract_keywords_from_analysis(self, analysis_data: CodeAnalysisData) -> List[str]:
        """분석 데이터에서 키워드 추출"""
        keywords = []
        
        # 파일명에서 키워드 추출
        file_name = analysis_data.filePath.split('/')[-1].replace('.java', '')
        keywords.append(file_name)
        
        # 프레임워크와 모듈 정보 추가
        if analysis_data.framework:
            keywords.append(analysis_data.framework)
        if analysis_data.module:
            keywords.append(analysis_data.module)
        
        # 클래스명과 메서드명 추가
        if analysis_data.classes:
            for cls in analysis_data.classes:
                keywords.append(cls.name)
                for method in cls.methods:
                    keywords.append(method.name)
        
        # 참조 정보에서 중요한 키워드 추출
        if analysis_data.references:
            for ref in analysis_data.references:
                # 간단한 클래스명 추출 (패키지 경로 제거)
                if '.' in ref:
                    class_name = ref.split('.')[-1]
                    keywords.append(class_name)
                else:
                    keywords.append(ref)
        
        return list(set(keywords))  # 중복 제거
    
    def _extract_namespace(self, analysis_data: CodeAnalysisData) -> str:
        """네임스페이스/패키지 추출"""
        code_lines = analysis_data.code.split('\n')
        for line in code_lines:
            line = line.strip()
            if line.startswith('package '):
                return line.replace('package ', '').replace(';', '').strip()
        return ""