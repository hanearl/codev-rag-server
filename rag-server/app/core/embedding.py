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
        # object.__setattr__을 사용하여 Pydantic 검증 우회
        object.__setattr__(self, '_embedding_server_url', settings.embedding_server_url)
        object.__setattr__(self, 'client', httpx.AsyncClient(timeout=30.0))
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """쿼리 임베딩 생성 (동기)"""
        try:
            # 이미 실행 중인 event loop가 있는지 확인
            loop = asyncio.get_running_loop()
            # 실행 중인 loop가 있으면 create_task 사용
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._aget_query_embedding(query))
                return future.result()
        except RuntimeError:
            # 실행 중인 loop가 없으면 asyncio.run 사용
            return asyncio.run(self._aget_query_embedding(query))
    
    async def _aget_query_embedding(self, query: str) -> List[float]:
        """쿼리 임베딩 생성 (비동기)"""
        try:
            response = await self.client.post(
                f"{self._embedding_server_url}/embedding/embed",
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
        try:
            # 이미 실행 중인 event loop가 있는지 확인
            loop = asyncio.get_running_loop()
            # 실행 중인 loop가 있으면 create_task 사용
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._aget_text_embedding(text))
                return future.result()
        except RuntimeError:
            # 실행 중인 loop가 없으면 asyncio.run 사용
            return asyncio.run(self._aget_text_embedding(text))
    
    async def _aget_text_embedding(self, text: str) -> List[float]:
        """텍스트 임베딩 생성 (비동기)"""
        return await self._aget_query_embedding(text)
    
    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트 임베딩 생성 (동기)"""
        try:
            # 이미 실행 중인 event loop가 있는지 확인
            loop = asyncio.get_running_loop()
            # 실행 중인 loop가 있으면 create_task 사용
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self._aget_text_embeddings(texts))
                return future.result()
        except RuntimeError:
            # 실행 중인 loop가 없으면 asyncio.run 사용
            return asyncio.run(self._aget_text_embeddings(texts))
    
    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트 임베딩 생성 (비동기)"""
        try:
            response = await self.client.post(
                f"{self._embedding_server_url}/embedding/embed/bulk",
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