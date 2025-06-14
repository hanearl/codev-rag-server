from typing import List, Dict, Any, Optional
import logging

from .bm25_index import CodeBM25Index, BM25IndexConfig
from app.retriever.document_builder import EnhancedDocument

logger = logging.getLogger(__name__)


class BM25IndexService:
    """BM25 Index 서비스 - 컬렉션별 인덱스 관리"""
    
    def __init__(self):
        # 컬렉션명별로 분리된 인덱스들을 관리
        self.indexes: Dict[str, CodeBM25Index] = {}
        self._initialized: Dict[str, bool] = {}
    
    def _get_or_create_index(self, collection_name: str) -> CodeBM25Index:
        """컬렉션별 인덱스 가져오기 또는 생성"""
        if collection_name not in self.indexes:
            # 컬렉션별 설정 생성
            config = BM25IndexConfig(
                index_path=f"data/bm25_index/{collection_name}",
                k1=1.2,
                b=0.75,
                top_k=10
            )
            self.indexes[collection_name] = CodeBM25Index(config)
            self._initialized[collection_name] = False
            logger.info(f"새 BM25 인덱스 생성: {collection_name}")
        
        return self.indexes[collection_name]
    
    async def initialize(self, collection_name: str = "default"):
        """특정 컬렉션 인덱스 초기화"""
        index = self._get_or_create_index(collection_name)
        
        if not self._initialized.get(collection_name, False):
            await index.setup()
            self._initialized[collection_name] = True
            logger.info(f"BM25 Index 초기화 완료: {collection_name}")
    
    async def index_documents(
        self, 
        documents: List[EnhancedDocument],
        collection_name: str = "default"
    ) -> Dict[str, Any]:
        """특정 컬렉션에 문서들 인덱싱"""
        await self.initialize(collection_name)
        index = self._get_or_create_index(collection_name)
        
        try:
            added_ids = await index.add_documents(documents)
            
            return {
                "success": True,
                "indexed_count": len(added_ids),
                "document_ids": added_ids,
                "index_type": "bm25",
                "collection_name": collection_name
            }
        except Exception as e:
            logger.error(f"BM25 문서 인덱싱 실패 ({collection_name}): {e}")
            return {
                "success": False,
                "error": str(e),
                "indexed_count": 0,
                "collection_name": collection_name
            }
    
    async def search_keywords(
        self, 
        query: str, 
        collection_name: str = "default",
        limit: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """특정 컬렉션에서 키워드 검색"""
        await self.initialize(collection_name)
        
        if collection_name not in self.indexes:
            logger.warning(f"컬렉션 '{collection_name}'을 찾을 수 없음")
            return []
        
        index = self.indexes[collection_name]
        results = await index.search_with_scores(query, limit, filters)
        
        # 결과에 컬렉션 정보 추가
        for result in results:
            result['collection_name'] = collection_name
        
        return results
    
    async def update_document(
        self, 
        doc_id: str, 
        document: Dict[str, Any],
        collection_name: str = "default"
    ) -> bool:
        """특정 컬렉션에서 문서 업데이트"""
        await self.initialize(collection_name)
        
        if collection_name not in self.indexes:
            return False
            
        index = self.indexes[collection_name]
        return await index.update_document(doc_id, document)
    
    async def delete_document(
        self, 
        doc_id: str,
        collection_name: str = "default"
    ) -> bool:
        """특정 컬렉션에서 문서 삭제"""
        await self.initialize(collection_name)
        
        if collection_name not in self.indexes:
            return False
            
        index = self.indexes[collection_name]
        return await index.delete_document(doc_id)
    
    async def delete_collection(self, collection_name: str) -> bool:
        """전체 컬렉션 삭제"""
        try:
            if collection_name in self.indexes:
                # 인덱스 파일 삭제
                index = self.indexes[collection_name]
                import shutil
                if index.config.index_path.exists():
                    shutil.rmtree(index.config.index_path)
                
                # 메모리에서 제거
                del self.indexes[collection_name]
                del self._initialized[collection_name]
                
                logger.info(f"BM25 컬렉션 삭제 완료: {collection_name}")
                return True
            else:
                logger.warning(f"삭제할 컬렉션 '{collection_name}'을 찾을 수 없음")
                return False
                
        except Exception as e:
            logger.error(f"BM25 컬렉션 삭제 실패 ({collection_name}): {e}")
            return False
    
    async def get_index_stats(self, collection_name: str = "default") -> Dict[str, Any]:
        """특정 컬렉션 인덱스 통계"""
        await self.initialize(collection_name)
        
        if collection_name not in self.indexes:
            return {
                "collection_name": collection_name,
                "total_documents": 0,
                "error": "Collection not found"
            }
            
        index = self.indexes[collection_name]
        stats = await index.get_stats()
        stats["collection_name"] = collection_name
        return stats
    
    async def get_all_collections(self) -> List[str]:
        """모든 컬렉션 목록 조회"""
        return list(self.indexes.keys())
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """전체 통계 정보"""
        total_docs = 0
        total_tokens = 0
        collections = {}
        
        for collection_name in self.indexes.keys():
            stats = await self.get_index_stats(collection_name)
            collections[collection_name] = stats
            total_docs += stats.get("total_documents", 0)
            total_tokens += stats.get("total_tokens", 0)
        
        return {
            "total_documents": total_docs,
            "total_tokens": total_tokens,
            "collections": collections,
            "collection_count": len(self.indexes)
        }
    
    async def rebuild_index(
        self, 
        documents: List[EnhancedDocument],
        collection_name: str = "default"
    ) -> Dict[str, Any]:
        """특정 컬렉션 인덱스 재구성"""
        try:
            # 기존 컬렉션 삭제
            await self.delete_collection(collection_name)
            
            # 새 문서들로 인덱스 구성
            result = await self.index_documents(documents, collection_name)
            
            logger.info(f"BM25 인덱스 재구성 완료: {collection_name}, {result['indexed_count']}개 문서")
            return result
            
        except Exception as e:
            logger.error(f"BM25 인덱스 재구성 실패 ({collection_name}): {e}")
            return {
                "success": False,
                "error": str(e),
                "collection_name": collection_name
            }
    
    async def health_check(self, collection_name: str = "default") -> Dict[str, Any]:
        """특정 컬렉션 헬스 체크"""
        try:
            await self.initialize(collection_name)
            stats = await self.get_index_stats(collection_name)
            
            return {
                "status": "healthy",
                "index_type": "bm25",
                "collection_name": collection_name,
                "document_count": stats.get("total_documents", 0),
                "total_tokens": stats.get("total_tokens", 0)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "collection_name": collection_name,
                "error": str(e)
            }


# 전역 서비스 인스턴스
_bm25_service_instance = None


def get_bm25_index_service(config: BM25IndexConfig = None) -> BM25IndexService:
    """BM25 Index Service 싱글톤 인스턴스 반환"""
    global _bm25_service_instance
    
    if _bm25_service_instance is None:
        _bm25_service_instance = BM25IndexService(config)
    
    return _bm25_service_instance 