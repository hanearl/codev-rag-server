import httpx
import logging
from typing import List, Dict, Any, Optional
from app.features.systems.interface import RAGSystemInterface, RetrievalResult, RAGSystemConfig

logger = logging.getLogger(__name__)


class RAGServerVectorAdapter(RAGSystemInterface):
    """RAG 서버 벡터 검색 전용 어댑터"""
    
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
    
    async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """벡터 검색 수행"""
        try:
            # 벡터 검색 요청
            search_request = {
                "query": query,
                "collection_name": self.config.collection_name,
                "top_k": min(top_k, 100),
                "score_threshold": 0.0
            }
            
            response = await self.client.post(
                self.config.endpoints.vector_search,
                json=search_request
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("success", False):
                error_msg = data.get("error", "벡터 검색 실패")
                logger.error(f"벡터 검색 실패: {error_msg}")
                return []
            
            results = []
            for item in data.get("results", []):
                # full_class_name 우선 사용, 없으면 filepath 또는 filename 사용
                metadata = item.get("metadata", {})
                filepath = metadata.get("full_class_name") or metadata.get("filepath") or metadata.get("filename")
                
                result = RetrievalResult(
                    content=item.get("content", ""),
                    score=float(item.get("score", 0.0)),
                    filepath=filepath,
                    metadata={
                        **metadata,
                        "document_id": item.get("document_id"),
                        "search_type": "vector",
                        "search_time_ms": data.get("search_time_ms", 0)
                    }
                )
                results.append(result)
            
            logger.info(f"벡터 검색 완료: {len(results)}개 결과, {data.get('search_time_ms', 0)}ms")
            return results
            
        except httpx.HTTPError as e:
            logger.error(f"벡터 검색 HTTP 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"벡터 검색 오류: {e}")
            raise
    
    async def health_check(self) -> bool:
        """헬스체크"""
        try:
            # 서비스 전체 헬스체크
            response = await self.client.get(self.config.endpoints.health)
            if response.status_code != 200:
                return False
            
            # 검색 서비스 헬스체크
            search_response = await self.client.get(self.config.endpoints.search_health)
            if search_response.status_code != 200:
                return False
                
            search_health = search_response.json()
            return search_health.get("status") == "healthy"
            
        except Exception as e:
            logger.warning(f"벡터 검색 헬스체크 실패: {e}")
            return False
    
    async def get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 조회"""
        try:
            info = await super().get_system_info()
            
            # 컬렉션 목록 조회
            collections_response = await self.client.get(self.config.endpoints.collections)
            collections = collections_response.json() if collections_response.status_code == 200 else {}
            
            # 검색 서비스 헬스체크
            search_health = await self.client.get(self.config.endpoints.search_health)
            health_data = search_health.json() if search_health.status_code == 200 else {}
            
            info.update({
                "vector_search_info": {
                    "search_service": health_data.get("status", "unknown"),
                    "available_collections": collections.get("collections", []),
                    "current_collection": self.config.collection_name,
                    "vector_components": health_data.get("components", {}).get("vector_index", False),
                    "features": {
                        "vector_search": True,
                        "semantic_search": True,
                        "embedding_based": True,
                        "similarity_threshold": True
                    }
                }
            })
            
            return info
            
        except Exception as e:
            logger.warning(f"벡터 검색 시스템 정보 조회 실패: {e}")
            return await super().get_system_info()
    
    async def close(self):
        """리소스 정리"""
        await self.client.aclose()
    
    def __repr__(self):
        return f"<RAGServerVectorAdapter(name='{self.config.name}', collection='{self.config.collection_name}')>" 