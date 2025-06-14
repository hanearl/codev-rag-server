import httpx
import logging
from typing import List, Dict, Any, Optional
from app.features.systems.interface import RAGSystemInterface, RetrievalResult, RAGSystemConfig

logger = logging.getLogger(__name__)


class GenericHTTPRAGSystem(RAGSystemInterface):
    """범용 HTTP API 기반 RAG 시스템 어댑터"""
    
    def __init__(self, config: RAGSystemConfig):
        """
        Args:
            config: RAG 시스템 설정
        """
        super().__init__(config)
        self.base_url = config.base_url.rstrip('/')
        
        # HTTP 클라이언트 설정
        headers = {"Content-Type": "application/json"}
        
        # 인증 헤더 설정
        if config.api_key:
            if config.auth_type == "bearer":
                headers[config.auth_header] = f"Bearer {config.api_key}"
            elif config.auth_type == "api_key":
                headers[config.auth_header] = config.api_key
            elif config.auth_type == "basic":
                import base64
                credentials = base64.b64encode(f":{config.api_key}".encode()).decode()
                headers[config.auth_header] = f"Basic {credentials}"
        
        # 커스텀 헤더 추가
        headers.update(config.custom_headers)
            
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=config.timeout
        )
    
    async def embed_query(self, query: str) -> List[float]:
        """쿼리 임베딩 생성"""
        try:
            # 요청 데이터 구성
            request_data = {
                self.config.request_format.text_field: query
            }
            request_data.update(self.config.request_format.additional_fields)
            
            response = await self.client.post(
                self.config.endpoints.embed,
                json=request_data
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get(self.config.response_format.embedding_field, [])
            
        except httpx.HTTPError as e:
            logger.error(f"임베딩 생성 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            raise
    
    async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """검색 수행"""
        try:
            # 요청 데이터 구성
            request_data = {
                self.config.request_format.query_field: query,
                self.config.request_format.top_k_field: top_k
            }
            request_data.update(self.config.request_format.additional_fields)
            
            response = await self.client.post(
                self.config.endpoints.search,
                json=request_data
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # 응답 형식에 따라 결과 파싱
            items = data.get(self.config.response_format.results_field, [])
            
            for item in items:
                result = RetrievalResult(
                    content=item.get(self.config.response_format.content_field, ""),
                    score=float(item.get(self.config.response_format.score_field, 0.0)),
                    filepath=item.get(self.config.response_format.filepath_field),
                    metadata=item.get(self.config.response_format.metadata_field, {})
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
            response = await self.client.get(self.config.endpoints.health)
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"헬스체크 실패: {e}")
            return False
    
    async def get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 조회"""
        try:
            response = await self.client.get(self.config.endpoints.info)
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
        return f"<GenericHTTPRAGSystem(name='{self.config.name}', type='{self.config.system_type}')>"


# 기존 HTTPRAGSystem을 호환성을 위해 유지
class HTTPRAGSystem(GenericHTTPRAGSystem):
    """기존 HTTPRAGSystem (호환성 유지)"""
    
    def __init__(
        self, 
        base_url: str, 
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """기존 방식 호환성 유지"""
        from app.features.systems.interface import RAGSystemConfig, RAGSystemType
        
        config = RAGSystemConfig(
            name="legacy-http-system",
            system_type=RAGSystemType.CUSTOM_HTTP,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries
        )
        super().__init__(config) 