from typing import List, Dict, Any, Optional
from app.core.clients import EmbeddingClient, VectorClient
import logging

logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, embedding_client: EmbeddingClient, vector_client: VectorClient):
        self.embedding_client = embedding_client
        self.vector_client = vector_client
    
    async def search(
        self, 
        query: str,
        keywords: Optional[List[str]] = None,
        limit: int = 10,
        collection_name: str = "code_chunks"
    ) -> List[Dict[str, Any]]:
        """하이브리드 검색 수행"""
        try:
            # 쿼리 임베딩 생성
            embedding_response = await self.embedding_client.embed_single({
                "text": query
            })
            query_embedding = embedding_response["embedding"]
            
            # 벡터 DB에서 하이브리드 검색 수행 (기존 구현 활용)
            results = self.vector_client.hybrid_search(
                collection_name=collection_name,
                query_embedding=query_embedding,
                keywords=keywords,
                limit=limit
            )
            
            return results
            
        except Exception as e:
            logger.error(f"하이브리드 검색 실패: {e}")
            raise 