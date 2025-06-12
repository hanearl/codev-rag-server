import httpx
import logging
from typing import List, Dict, Any, Optional
from app.features.systems.interface import RAGSystemInterface, RetrievalResult

logger = logging.getLogger(__name__)


class HTTPRAGSystem(RAGSystemInterface):
    """HTTP API 기반 RAG 시스템 클라이언트"""
    
    def __init__(
        self, 
        base_url: str, 
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Args:
            base_url: RAG 시스템의 기본 URL
            api_key: API 인증 키 (선택적)
            timeout: 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        # HTTP 클라이언트 설정
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout
        )
    
    async def embed_query(self, query: str) -> List[float]:
        """쿼리 임베딩 생성"""
        try:
            response = await self.client.post(
                "/api/v1/embed",
                json={"text": query}
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("embedding", [])
            
        except httpx.HTTPError as e:
            logger.error(f"임베딩 생성 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            raise
    
    async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """검색 수행"""
        try:
            response = await self.client.post(
                "/api/v1/search",
                json={
                    "query": query,
                    "k": top_k
                }
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get("results", []):
                result = RetrievalResult(
                    content=item.get("content", ""),
                    score=float(item.get("score", 0.0)),
                    filepath=item.get("filepath"),
                    metadata=item.get("metadata", {})
                )
                results.append(result)
            
            return results
            
        except httpx.HTTPError as e:
            logger.error(f"검색 수행 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            raise
    
    async def health_check(self) -> bool:
        """시스템 상태 확인"""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"헬스체크 실패: {e}")
            return False
    
    async def get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 조회"""
        try:
            response = await self.client.get("/api/v1/info")
            if response.status_code == 200:
                return response.json()
            else:
                return await super().get_system_info()
                
        except Exception as e:
            logger.warning(f"시스템 정보 조회 실패: {e}")
            return await super().get_system_info()
    
    async def close(self):
        """리소스 정리"""
        await self.client.aclose()
    
    def __repr__(self):
        return f"<HTTPRAGSystem(base_url='{self.base_url}')>" 