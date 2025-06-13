from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel
from enum import Enum


class RetrievalResult(BaseModel):
    """검색 결과 모델"""
    content: str
    score: float
    filepath: Optional[str] = None
    metadata: Dict[str, Any] = {}


class RAGSystemType(str, Enum):
    """지원하는 RAG 시스템 타입"""
    OPENAI_RAG = "openai_rag"
    LANGCHAIN_RAG = "langchain_rag"
    LLAMAINDEX_RAG = "llamaindex_rag"
    CUSTOM_HTTP = "custom_http"
    RAG_SERVER = "rag_server"
    MOCK = "mock"


class EndpointConfig(BaseModel):
    """API 엔드포인트 설정"""
    search: str = "/api/v1/search"
    embed: str = "/api/v1/embed"
    health: str = "/health"
    info: str = "/api/v1/info"


class RequestFormat(BaseModel):
    """요청 형식 설정"""
    query_field: str = "query"
    k_field: str = "k"
    text_field: str = "text"
    additional_fields: Dict[str, Any] = {}


class ResponseFormat(BaseModel):
    """응답 형식 설정"""
    results_field: str = "results"
    content_field: str = "content"
    score_field: str = "score"
    filepath_field: str = "filepath"
    metadata_field: str = "metadata"
    embedding_field: str = "embedding"


class RAGSystemConfig(BaseModel):
    """RAG 시스템 설정"""
    name: str
    system_type: RAGSystemType
    base_url: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    
    # API 설정
    endpoints: EndpointConfig = EndpointConfig()
    request_format: RequestFormat = RequestFormat()
    response_format: ResponseFormat = ResponseFormat()
    
    # 인증 설정
    auth_type: str = "bearer"  # bearer, api_key, basic, none
    auth_header: str = "Authorization"
    
    # 추가 헤더
    custom_headers: Dict[str, str] = {}


class RAGSystemInterface(ABC):
    """RAG 시스템 인터페이스"""
    
    def __init__(self, config: RAGSystemConfig):
        self.config = config
    
    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """
        쿼리를 임베딩으로 변환
        
        Args:
            query: 검색 쿼리
            
        Returns:
            임베딩 벡터
        """
        pass
    
    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """
        쿼리에 대한 검색 수행
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 결과 수
            
        Returns:
            검색 결과 리스트
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        시스템 상태 확인
        
        Returns:
            시스템이 정상이면 True, 아니면 False
        """
        pass
    
    async def get_system_info(self) -> Dict[str, Any]:
        """
        시스템 정보 조회 (선택적 구현)
        
        Returns:
            시스템 정보 딕셔너리
        """
        return {
            "type": self.__class__.__name__,
            "system_type": self.config.system_type,
            "name": self.config.name,
            "base_url": self.config.base_url,
            "status": "unknown"
        }
    
    @abstractmethod
    async def close(self):
        """리소스 정리"""
        pass 