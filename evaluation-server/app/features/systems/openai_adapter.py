import httpx
import logging
from typing import List, Dict, Any, Optional
from app.features.systems.interface import RAGSystemInterface, RetrievalResult, RAGSystemConfig

logger = logging.getLogger(__name__)


class OpenAIRAGAdapter(RAGSystemInterface):
    """OpenAI RAG 시스템 어댑터"""
    
    def __init__(self, config: RAGSystemConfig):
        super().__init__(config)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
            "OpenAI-Beta": "assistants=v1"
        }
        headers.update(config.custom_headers)
        
        self.client = httpx.AsyncClient(
            base_url=config.base_url or "https://api.openai.com/v1",
            headers=headers,
            timeout=config.timeout
        )
    
    async def embed_query(self, query: str) -> List[float]:
        """OpenAI Embeddings API 사용"""
        try:
            response = await self.client.post(
                "/embeddings",
                json={
                    "input": query,
                    "model": "text-embedding-ada-002"
                }
            )
            response.raise_for_status()
            
            data = response.json()
            return data["data"][0]["embedding"]
            
        except Exception as e:
            logger.error(f"OpenAI 임베딩 생성 오류: {e}")
            raise
    
    async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """OpenAI Assistant API 또는 커스텀 검색 사용"""
        try:
            # OpenAI의 경우 Assistant API나 커스텀 구현 필요
            # 여기서는 예시로 커스텀 엔드포인트 사용
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": "gpt-4",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that retrieves relevant code snippets."},
                        {"role": "user", "content": f"Find relevant code for: {query}"}
                    ],
                    "max_tokens": 1000
                }
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # OpenAI 응답을 RetrievalResult 형식으로 변환
            results = [
                RetrievalResult(
                    content=content,
                    score=1.0,  # OpenAI는 점수를 제공하지 않으므로 기본값
                    filepath=None,
                    metadata={"model": "gpt-4", "usage": data.get("usage", {})}
                )
            ]
            
            return results
            
        except Exception as e:
            logger.error(f"OpenAI 검색 오류: {e}")
            raise
    
    async def health_check(self) -> bool:
        """OpenAI API 상태 확인"""
        try:
            response = await self.client.get("/models")
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """리소스 정리"""
        await self.client.aclose()


class LangChainRAGAdapter(RAGSystemInterface):
    """LangChain RAG 시스템 어댑터"""
    
    def __init__(self, config: RAGSystemConfig):
        super().__init__(config)
        
        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["X-API-Key"] = config.api_key
        headers.update(config.custom_headers)
        
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers=headers,
            timeout=config.timeout
        )
    
    async def embed_query(self, query: str) -> List[float]:
        """LangChain 임베딩 엔드포인트 사용"""
        try:
            response = await self.client.post(
                "/embeddings",
                json={"text": query}
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("embedding", [])
            
        except Exception as e:
            logger.error(f"LangChain 임베딩 생성 오류: {e}")
            raise
    
    async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """LangChain 검색 엔드포인트 사용"""
        try:
            response = await self.client.post(
                "/search",
                json={
                    "query": query,
                    "top_k": top_k,
                    "return_metadata": True
                }
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for doc in data.get("documents", []):
                result = RetrievalResult(
                    content=doc.get("page_content", ""),
                    score=doc.get("score", 0.0),
                    filepath=doc.get("metadata", {}).get("source"),
                    metadata=doc.get("metadata", {})
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"LangChain 검색 오류: {e}")
            raise
    
    async def health_check(self) -> bool:
        """LangChain 서비스 상태 확인"""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """리소스 정리"""
        await self.client.aclose()


class LlamaIndexRAGAdapter(RAGSystemInterface):
    """LlamaIndex RAG 시스템 어댑터"""
    
    def __init__(self, config: RAGSystemConfig):
        super().__init__(config)
        
        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        headers.update(config.custom_headers)
        
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers=headers,
            timeout=config.timeout
        )
    
    async def embed_query(self, query: str) -> List[float]:
        """LlamaIndex 임베딩 엔드포인트 사용"""
        try:
            response = await self.client.post(
                "/v1/embeddings",
                json={"input": query}
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [{}])[0].get("embedding", [])
            
        except Exception as e:
            logger.error(f"LlamaIndex 임베딩 생성 오류: {e}")
            raise
    
    async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """LlamaIndex 쿼리 엔드포인트 사용"""
        try:
            response = await self.client.post(
                "/v1/query",
                json={
                    "query": query,
                    "similarity_top_k": top_k,
                    "response_mode": "tree_summarize"
                }
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # LlamaIndex 응답 형식에 따라 파싱
            for node in data.get("source_nodes", []):
                result = RetrievalResult(
                    content=node.get("node", {}).get("text", ""),
                    score=node.get("score", 0.0),
                    filepath=node.get("node", {}).get("metadata", {}).get("file_path"),
                    metadata=node.get("node", {}).get("metadata", {})
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"LlamaIndex 검색 오류: {e}")
            raise
    
    async def health_check(self) -> bool:
        """LlamaIndex 서비스 상태 확인"""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """리소스 정리"""
        await self.client.aclose() 