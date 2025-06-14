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


class RetrievalType(str, Enum):
    """검색 타입"""
    VECTOR = "vector"
    BM25 = "bm25"
    HYBRID = "hybrid"


class RAGSystemType(str, Enum):
    """지원하는 RAG 시스템 타입"""
    OPENAI_RAG = "openai_rag"
    LANGCHAIN_RAG = "langchain_rag"
    LLAMAINDEX_RAG = "llamaindex_rag"
    CUSTOM_HTTP = "custom_http"
    RAG_SERVER_VECTOR = "rag_server_vector"
    RAG_SERVER_BM25 = "rag_server_bm25"
    RAG_SERVER_HYBRID = "rag_server_hybrid"
    CODEV_V1 = "codev_v1"
    MOCK = "mock"


class EndpointConfig(BaseModel):
    """API 엔드포인트 설정"""
    search: str = "/project/v1/repo/retrieval"  # 기본 검색 엔드포인트
    embed: str = "/embed"  # 임베딩 엔드포인트
    vector_search: str = "/api/v1/search/vector"
    bm25_search: str = "/api/v1/search/bm25"
    hybrid_search: str = "/api/v1/search/hybrid"
    collections: str = "/api/v1/search/collections"
    indexes: str = "/api/v1/search/indexes"
    health: str = "/health"
    search_health: str = "/api/v1/search/health"
    info: str = "/info"  # 시스템 정보 엔드포인트


class RequestFormat(BaseModel):
    """요청 형식 설정"""
    query_field: str = "query"
    top_k_field: str = "top_k"
    collection_name_field: str = "collection_name"
    index_name_field: str = "index_name"
    vector_weight_field: str = "vector_weight"
    bm25_weight_field: str = "bm25_weight"
    fusion_method_field: str = "fusion_method"
    use_rrf_field: str = "use_rrf"
    rrf_k_field: str = "rrf_k"
    score_threshold_field: str = "score_threshold"
    additional_fields: Dict[str, Any] = {}


class ResponseFormat(BaseModel):
    """응답 형식 설정"""
    success_field: str = "success"
    results_field: str = "results"
    content_field: str = "content"
    score_field: str = "score"
    metadata_field: str = "metadata"
    total_results_field: str = "total_results"
    search_time_field: str = "search_time_ms"
    error_field: str = "error"


class RAGSystemConfig(BaseModel):
    """RAG 시스템 설정"""
    name: str
    system_type: RAGSystemType
    base_url: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    
    # 검색 타입별 설정
    retrieval_type: RetrievalType
    collection_name: Optional[str] = "code_chunks"
    index_name: Optional[str] = "code_index"
    
    # 하이브리드 검색 설정
    vector_weight: float = 0.7
    bm25_weight: float = 0.3
    use_rrf: bool = True
    rrf_k: int = 60
    
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
            "retrieval_type": self.config.retrieval_type,
            "name": self.config.name,
            "base_url": self.config.base_url,
            "status": "unknown"
        }
    
    @abstractmethod
    async def close(self):
        """리소스 정리"""
        pass 