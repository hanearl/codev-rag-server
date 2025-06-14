from typing import List, Dict, Any, Optional, Union
import logging
import asyncio

from .vector_index import CodeVectorIndex, VectorIndexConfig
from app.retriever.document_builder import EnhancedDocument

logger = logging.getLogger(__name__)


class VectorIndexService:
    """Vector Index 서비스"""
    
    def __init__(self, config: VectorIndexConfig = None):
        self.config = config or VectorIndexConfig()
        self.index = CodeVectorIndex(self.config)
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """서비스 초기화"""
        async with self._lock:
            if not self._initialized:
                try:
                    await self.index.setup()
                    self._initialized = True
                    logger.info(f"Vector Index 서비스 초기화 완료: {self.config.collection_name}")
                except Exception as e:
                    logger.error(f"Vector Index 서비스 초기화 실패: {e}")
                    raise
    
    async def _ensure_initialized(self):
        """초기화 확인"""
        if not self._initialized:
            await self.initialize()
    
    async def index_documents(self, documents: List[EnhancedDocument], collection_name: str = None) -> Dict[str, Any]:
        """문서들 인덱싱"""
        # collection_name이 제공되면 새로운 인덱스 인스턴스 생성
        if collection_name and collection_name != self.config.collection_name:
            temp_config = VectorIndexConfig(collection_name=collection_name, vector_size=384)
            temp_index = CodeVectorIndex(temp_config)
            await temp_index.setup()
            current_index = temp_index
            current_collection = collection_name
        else:
            await self._ensure_initialized()
            current_index = self.index
            current_collection = self.config.collection_name
        
        if not documents:
            return {
                "success": True,
                "indexed_count": 0,
                "document_ids": [],
                "collection": current_collection,
                "message": "인덱싱할 문서가 없습니다"
            }
        
        try:
            added_ids = await current_index.add_documents(documents)
            
            logger.info(f"문서 인덱싱 완료: {len(added_ids)}개 (컬렉션: {current_collection})")
            
            return {
                "success": True,
                "indexed_count": len(added_ids),
                "document_ids": added_ids,
                "collection": current_collection,
                "message": f"{len(added_ids)}개 문서가 성공적으로 인덱싱되었습니다"
            }
        except Exception as e:
            logger.error(f"문서 인덱싱 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "indexed_count": 0,
                "collection": current_collection
            }
    
    async def index_legacy_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """기존 형식 문서들 인덱싱"""
        await self._ensure_initialized()
        
        if not documents:
            return {
                "success": True,
                "indexed_count": 0,
                "document_ids": [],
                "collection": self.config.collection_name
            }
        
        try:
            added_ids = await self.index.add_documents(documents)
            
            logger.info(f"기존 형식 문서 인덱싱 완료: {len(added_ids)}개")
            
            return {
                "success": True,
                "indexed_count": len(added_ids),
                "document_ids": added_ids,
                "collection": self.config.collection_name
            }
        except Exception as e:
            logger.error(f"기존 형식 문서 인덱싱 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "indexed_count": 0
            }
    
    async def search_similar_code(
        self, 
        query: str, 
        limit: int = 10,
        threshold: float = 0.0,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """유사 코드 검색"""
        await self._ensure_initialized()
        
        if not query.strip():
            logger.warning("빈 검색 쿼리")
            return []
        
        try:
            if threshold > 0:
                results = await self.index.similarity_search_with_threshold(
                    query, threshold, limit
                )
                logger.info(f"임계값 검색 완료: {len(results)}개 결과 (threshold: {threshold})")
            else:
                results = await self.index.search_with_scores(
                    query, limit, filters
                )
                logger.info(f"일반 검색 완료: {len(results)}개 결과")
            
            return results
            
        except Exception as e:
            logger.error(f"유사 코드 검색 실패: {e}")
            return []
    
    async def search_documents(
        self,
        query: str,
        limit: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """문서 검색 (IndexedDocument 형식)"""
        await self._ensure_initialized()
        
        try:
            indexed_docs = await self.index.search(query, limit, filters)
            
            # IndexedDocument를 Dict로 변환
            results = []
            for doc in indexed_docs:
                result = {
                    "id": doc.id,
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "indexed_at": doc.indexed_at,
                    "source": "vector"
                }
                results.append(result)
            
            logger.info(f"문서 검색 완료: {len(results)}개 결과")
            return results
            
        except Exception as e:
            logger.error(f"문서 검색 실패: {e}")
            return []
    
    async def update_document(self, doc_id: str, document: Dict[str, Any]) -> Dict[str, Any]:
        """문서 업데이트"""
        await self._ensure_initialized()
        
        try:
            success = await self.index.update_document(doc_id, document)
            
            if success:
                logger.info(f"문서 업데이트 완료: {doc_id}")
                return {
                    "success": True,
                    "document_id": doc_id,
                    "message": "문서가 성공적으로 업데이트되었습니다"
                }
            else:
                return {
                    "success": False,
                    "document_id": doc_id,
                    "error": "문서 업데이트에 실패했습니다"
                }
                
        except Exception as e:
            logger.error(f"문서 업데이트 중 오류: {e}")
            return {
                "success": False,
                "document_id": doc_id,
                "error": str(e)
            }
    
    async def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """문서 삭제"""
        await self._ensure_initialized()
        
        try:
            success = await self.index.delete_document(doc_id)
            
            if success:
                logger.info(f"문서 삭제 완료: {doc_id}")
                return {
                    "success": True,
                    "document_id": doc_id,
                    "message": "문서가 성공적으로 삭제되었습니다"
                }
            else:
                return {
                    "success": False,
                    "document_id": doc_id,
                    "error": "문서 삭제에 실패했습니다"
                }
                
        except Exception as e:
            logger.error(f"문서 삭제 중 오류: {e}")
            return {
                "success": False,
                "document_id": doc_id,
                "error": str(e)
            }
    
    async def delete_by_file_path(self, file_path: str) -> Dict[str, Any]:
        """파일 경로로 문서 삭제"""
        await self._ensure_initialized()
        
        try:
            filters = {"file_path": file_path}
            deleted_count = await self.index.bulk_delete_by_filter(filters)
            
            logger.info(f"파일 경로 기반 삭제 완료: {file_path} - {deleted_count}개 문서")
            
            return {
                "success": True,
                "file_path": file_path,
                "deleted_count": deleted_count,
                "message": f"{deleted_count}개 문서가 삭제되었습니다"
            }
            
        except Exception as e:
            logger.error(f"파일 경로 기반 삭제 실패: {e}")
            return {
                "success": False,
                "file_path": file_path,
                "deleted_count": 0,
                "error": str(e)
            }
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """ID로 문서 조회"""
        await self._ensure_initialized()
        
        try:
            indexed_doc = await self.index.get_document_by_id(doc_id)
            
            if indexed_doc:
                return {
                    "id": indexed_doc.id,
                    "content": indexed_doc.content,
                    "metadata": indexed_doc.metadata,
                    "indexed_at": indexed_doc.indexed_at
                }
            else:
                logger.warning(f"문서를 찾을 수 없음: {doc_id}")
                return None
                
        except Exception as e:
            logger.error(f"문서 조회 실패: {e}")
            return None
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계"""
        await self._ensure_initialized()
        
        try:
            stats = await self.index.get_stats()
            
            # 추가 정보 포함
            enhanced_stats = {
                **stats,
                "service_status": "active",
                "config": {
                    "collection_name": self.config.collection_name,
                    "vector_size": self.config.vector_size,
                    "similarity_top_k": self.config.similarity_top_k,
                    "retrieval_mode": self.config.retrieval_mode
                }
            }
            
            return enhanced_stats
            
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {
                "collection_name": self.config.collection_name,
                "error": str(e),
                "service_status": "error"
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """헬스 체크"""
        try:
            await self._ensure_initialized()
            stats = await self.get_collection_stats()
            
            return {
                "status": "healthy",
                "service": "vector_index",
                "collection": self.config.collection_name,
                "document_count": stats.get("total_documents", 0),
                "vector_size": stats.get("vector_size", self.config.vector_size),
                "initialized": self._initialized
            }
        except Exception as e:
            logger.error(f"헬스 체크 실패: {e}")
            return {
                "status": "unhealthy",
                "service": "vector_index",
                "error": str(e),
                "initialized": self._initialized
            }
    
    async def search_by_similarity(
        self,
        query: str,
        top_k: int = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """유사도 기반 검색 (고급 옵션)"""
        await self._ensure_initialized()
        
        try:
            # 설정된 top_k 값 사용 또는 기본값
            limit = top_k or self.config.similarity_top_k
            
            results = await self.index.search_with_scores(query, limit)
            
            # 최소 점수 필터링
            if min_score > 0:
                results = [r for r in results if r.get('score', 0) >= min_score]
            
            logger.info(f"유사도 검색 완료: {len(results)}개 결과 (min_score: {min_score})")
            return results
            
        except Exception as e:
            logger.error(f"유사도 검색 실패: {e}")
            return []
    
    async def bulk_index_documents(
        self,
        documents: List[Union[EnhancedDocument, Dict[str, Any]]],
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """대량 문서 인덱싱 (배치 처리)"""
        await self._ensure_initialized()
        
        if not documents:
            return {
                "success": True,
                "total_documents": 0,
                "indexed_count": 0,
                "batch_count": 0
            }
        
        total_indexed = 0
        batch_count = 0
        errors = []
        
        try:
            # 배치 단위로 처리
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_count += 1
                
                try:
                    if isinstance(batch[0], EnhancedDocument):
                        result = await self.index_documents(batch)
                    else:
                        result = await self.index_legacy_documents(batch)
                    
                    if result["success"]:
                        total_indexed += result["indexed_count"]
                        logger.info(f"배치 {batch_count} 완료: {result['indexed_count']}개 문서")
                    else:
                        errors.append(f"배치 {batch_count} 실패: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    error_msg = f"배치 {batch_count} 처리 중 오류: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            return {
                "success": len(errors) == 0,
                "total_documents": len(documents),
                "indexed_count": total_indexed,
                "batch_count": batch_count,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"대량 인덱싱 실패: {e}")
            return {
                "success": False,
                "total_documents": len(documents),
                "indexed_count": total_indexed,
                "batch_count": batch_count,
                "error": str(e),
                "errors": errors
            }
    
    async def teardown(self):
        """서비스 종료 및 리소스 정리"""
        try:
            if self._initialized and self.index:
                await self.index.teardown()
                self._initialized = False
                logger.info("Vector Index 서비스 종료 완료")
        except Exception as e:
            logger.error(f"서비스 종료 중 오류: {e}")


# 싱글톤 인스턴스
_vector_service_instance = None


def get_vector_index_service(config: VectorIndexConfig = None) -> VectorIndexService:
    """Vector Index 서비스 싱글톤 인스턴스 반환"""
    global _vector_service_instance
    
    if _vector_service_instance is None:
        _vector_service_instance = VectorIndexService(config)
    
    return _vector_service_instance 