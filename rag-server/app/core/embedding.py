"""
embedding-server와 연동하는 커스텀 임베딩 모델
"""
from typing import List, Any
from llama_index.core.embeddings import BaseEmbedding
import httpx
import asyncio
import logging
from .config import settings

logger = logging.getLogger(__name__)


class CustomEmbeddingModel(BaseEmbedding):
    """embedding-server와 연동하는 커스텀 임베딩 모델"""
    
    def __init__(self):
        super().__init__(
            embed_batch_size=10,
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.embedding_server_url = settings.embedding_server_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """쿼리 임베딩 생성 (동기)"""
        return asyncio.run(self._aget_query_embedding(query))
    
    async def _aget_query_embedding(self, query: str) -> List[float]:
        """쿼리 임베딩 생성 (비동기)"""
        try:
            response = await self.client.post(
                f"{self.embedding_server_url}/api/v1/embedding/embed",
                json={"text": query}
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("embedding", [])
            else:
                logger.error(f"임베딩 생성 실패: {response.status_code} - {response.text}")
                # 기본 임베딩 반환 (384 차원)
                return [0.0] * 384
                
        except Exception as e:
            logger.error(f"임베딩 서버 연결 실패: {e}")
            # 기본 임베딩 반환 (384 차원)
            return [0.0] * 384
    
    def _get_text_embedding(self, text: str) -> List[float]:
        """텍스트 임베딩 생성 (동기)"""
        return asyncio.run(self._aget_text_embedding(text))
    
    async def _aget_text_embedding(self, text: str) -> List[float]:
        """텍스트 임베딩 생성 (비동기)"""
        return await self._aget_query_embedding(text)
    
    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트 임베딩 생성 (동기)"""
        return asyncio.run(self._aget_text_embeddings(texts))
    
    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트 임베딩 생성 (비동기)"""
        try:
            response = await self.client.post(
                f"{self.embedding_server_url}/api/v1/embedding/embed/bulk",
                json={"texts": texts}
            )
            
            if response.status_code == 200:
                result = response.json()
                embeddings = result.get("embeddings", [])
                return [emb.get("embedding", [0.0] * 384) for emb in embeddings]
            else:
                logger.error(f"벌크 임베딩 생성 실패: {response.status_code} - {response.text}")
                # 기본 임베딩들 반환
                return [[0.0] * 384 for _ in texts]
                
        except Exception as e:
            logger.error(f"벌크 임베딩 서버 연결 실패: {e}")
            # 기본 임베딩들 반환
            return [[0.0] * 384 for _ in texts]
    
    def __del__(self):
        """리소스 정리"""
        if hasattr(self, 'client'):
            asyncio.run(self.client.aclose()) 