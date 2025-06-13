from typing import List, Dict, Any, Optional
import logging

from .bm25_index import CodeBM25Index, BM25IndexConfig
from app.retriever.document_builder import EnhancedDocument

logger = logging.getLogger(__name__)


class BM25IndexService:
    """BM25 Index 서비스"""
    
    def __init__(self, config: BM25IndexConfig = None):
        self.config = config or BM25IndexConfig()
        self.index = CodeBM25Index(self.config)
        self._initialized = False
    
    async def initialize(self):
        """서비스 초기화"""
        if not self._initialized:
            await self.index.setup()
            self._initialized = True
            logger.info("BM25 Index 서비스 초기화 완료")
    
    async def index_documents(self, documents: List[EnhancedDocument]) -> Dict[str, Any]:
        """문서들 인덱싱"""
        await self.initialize()
        
        try:
            added_ids = await self.index.add_documents(documents)
            
            return {
                "success": True,
                "indexed_count": len(added_ids),
                "document_ids": added_ids,
                "index_type": "bm25"
            }
        except Exception as e:
            logger.error(f"BM25 문서 인덱싱 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "indexed_count": 0
            }
    
    async def search_keywords(
        self, 
        query: str, 
        limit: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """키워드 검색"""
        await self.initialize()
        return await self.index.search_with_scores(query, limit, filters)
    
    async def update_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """문서 업데이트"""
        await self.initialize()
        return await self.index.update_document(doc_id, document)
    
    async def delete_document(self, doc_id: str) -> bool:
        """문서 삭제"""
        await self.initialize()
        return await self.index.delete_document(doc_id)
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """인덱스 통계"""
        await self.initialize()
        return await self.index.get_stats()
    
    async def rebuild_index(self, documents: List[EnhancedDocument]) -> Dict[str, Any]:
        """인덱스 재구성"""
        try:
            # 기존 인덱스 초기화
            self.index.nodes = []
            self.index.documents_map = {}
            
            # 새 문서들로 인덱스 구성
            result = await self.index_documents(documents)
            
            logger.info(f"BM25 인덱스 재구성 완료: {result['indexed_count']}개 문서")
            return result
            
        except Exception as e:
            logger.error(f"BM25 인덱스 재구성 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """헬스 체크"""
        try:
            await self.initialize()
            stats = await self.get_index_stats()
            
            return {
                "status": "healthy",
                "index_type": "bm25",
                "document_count": stats.get("total_documents", 0),
                "total_tokens": stats.get("total_tokens", 0)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
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