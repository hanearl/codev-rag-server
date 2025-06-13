import httpx
import logging
from typing import List, Dict, Any, Optional
from app.features.systems.interface import RAGSystemInterface, RetrievalResult, RAGSystemConfig

logger = logging.getLogger(__name__)


class RAGServerAdapter(RAGSystemInterface):
    """codev-rag-server 전용 어댑터"""
    
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
        """
        rag-server는 별도의 임베딩 엔드포인트가 없으므로
        embedding-server를 직접 호출하거나 검색 과정에서 임베딩을 추출
        """
        try:
            # embedding-server 호출 (rag-server와 같은 네트워크에 있다고 가정)
            embedding_url = self.config.base_url.replace("rag-server:8000", "embedding-server:8001")
            
            async with httpx.AsyncClient() as embedding_client:
                response = await embedding_client.post(
                    f"{embedding_url}/api/v1/embed",
                    json={"text": query},
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                
                data = response.json()
                return data.get("embedding", [])
                
        except Exception as e:
            logger.error(f"rag-server 임베딩 생성 오류: {e}")
            # 임베딩 실패 시 빈 리스트 반환 (검색은 여전히 가능)
            return []
    
    async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """rag-server의 검색 API 사용"""
        try:
            # rag-server 검색 API 호출
            search_request = {
                "query": query,
                "limit": min(top_k, 50),  # rag-server 최대 제한
                "vector_weight": 0.7,
                "keyword_weight": 0.3,
                "collection_name": "code_chunks",
                "use_rrf": True,  # RRF 사용으로 더 나은 결과
                "rrf_k": 60
            }
            
            response = await self.client.post(
                "/api/v1/search/",
                json=search_request
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # rag-server 응답을 RetrievalResult로 변환
            for item in data.get("results", []):
                # 코드 내용과 파일 정보 조합
                content_parts = []
                if item.get("function_name"):
                    content_parts.append(f"Function: {item['function_name']}")
                content_parts.append(item.get("code_content", ""))
                
                content = "\n".join(content_parts)
                
                result = RetrievalResult(
                    content=content,
                    score=float(item.get("combined_score", 0.0)),
                    filepath=item.get("file_path"),
                    metadata={
                        "id": item.get("id"),
                        "function_name": item.get("function_name"),
                        "code_type": item.get("code_type"),
                        "language": item.get("language"),
                        "line_start": item.get("line_start"),
                        "line_end": item.get("line_end"),
                        "keywords": item.get("keywords", []),
                        "vector_score": item.get("vector_score", 0.0),
                        "keyword_score": item.get("keyword_score", 0.0),
                        "search_method": data.get("search_method", "weighted"),
                        "search_time_ms": data.get("search_time_ms", 0)
                    }
                )
                results.append(result)
            
            logger.info(f"rag-server 검색 완료: {len(results)}개 결과, {data.get('search_time_ms', 0)}ms")
            return results
            
        except httpx.HTTPError as e:
            logger.error(f"rag-server 검색 HTTP 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"rag-server 검색 오류: {e}")
            raise
    
    async def health_check(self) -> bool:
        """rag-server 상태 확인"""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"rag-server 헬스체크 실패: {e}")
            return False
    
    async def get_system_info(self) -> Dict[str, Any]:
        """rag-server 시스템 정보 조회"""
        try:
            # 기본 정보
            info = await super().get_system_info()
            
            # 검색 서비스 상태 확인
            search_health = await self.client.get("/api/v1/search/health")
            generation_health = await self.client.get("/api/v1/generate/health")
            
            # 지원 언어 조회
            languages_response = await self.client.get("/api/v1/generate/languages")
            languages = languages_response.json() if languages_response.status_code == 200 else {}
            
            info.update({
                "rag_server_info": {
                    "search_service": "healthy" if search_health.status_code == 200 else "unhealthy",
                    "generation_service": "healthy" if generation_health.status_code == 200 else "unhealthy",
                    "supported_languages": languages.get("languages", []),
                    "features": {
                        "hybrid_search": True,
                        "rrf_fusion": True,
                        "code_generation": True,
                        "multi_language": True,
                        "vector_search": True,
                        "keyword_search": True
                    }
                }
            })
            
            return info
            
        except Exception as e:
            logger.warning(f"rag-server 시스템 정보 조회 실패: {e}")
            return await super().get_system_info()
    
    async def search_with_generation(self, query: str, language: str = "python", top_k: int = 10) -> Dict[str, Any]:
        """
        rag-server의 고유 기능: 검색 + 코드 생성
        (evaluation에서는 사용하지 않지만 확장성을 위해 제공)
        """
        try:
            # 1. 검색 수행
            search_results = await self.retrieve(query, top_k)
            
            # 2. 코드 생성 요청
            generation_request = {
                "query": query,
                "language": language,
                "max_tokens": 1000,
                "temperature": 0.1,
                "use_search": True,
                "search_limit": top_k
            }
            
            generation_response = await self.client.post(
                "/api/v1/generate/",
                json=generation_request
            )
            generation_response.raise_for_status()
            
            generation_data = generation_response.json()
            
            return {
                "search_results": [
                    {
                        "content": r.content,
                        "score": r.score,
                        "filepath": r.filepath,
                        "metadata": r.metadata
                    } for r in search_results
                ],
                "generated_code": generation_data.get("generated_code", ""),
                "explanation": generation_data.get("explanation", ""),
                "tokens_used": generation_data.get("tokens_used", 0),
                "generation_time_ms": generation_data.get("generation_time_ms", 0)
            }
            
        except Exception as e:
            logger.error(f"rag-server 검색+생성 오류: {e}")
            raise
    
    async def close(self):
        """리소스 정리"""
        await self.client.aclose()
    
    def __repr__(self):
        return f"<RAGServerAdapter(name='{self.config.name}', base_url='{self.config.base_url}')>" 