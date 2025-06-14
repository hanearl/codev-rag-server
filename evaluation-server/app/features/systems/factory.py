from typing import Dict, Type, Optional
import logging
from app.features.systems.interface import RAGSystemInterface, RAGSystemConfig, RAGSystemType, RetrievalType
from app.features.systems.http_client import GenericHTTPRAGSystem
from app.features.systems.openai_adapter import OpenAIRAGAdapter, LangChainRAGAdapter, LlamaIndexRAGAdapter
from app.features.systems.rag_server_adapter import RAGServerAdapter
from app.features.systems.rag_server_vector_adapter import RAGServerVectorAdapter
from app.features.systems.rag_server_bm25_adapter import RAGServerBM25Adapter
from app.features.systems.rag_server_hybrid_adapter import RAGServerHybridAdapter
from app.features.systems.codev_v1_adapter import CodevV1RAGAdapter
from app.features.systems.mock_client import MockRAGSystem

logger = logging.getLogger(__name__)


class RAGSystemFactory:
    """RAG 시스템 팩토리"""
    
    def __init__(self):
        self._adapters: Dict[RAGSystemType, Type[RAGSystemInterface]] = {
            RAGSystemType.OPENAI_RAG: OpenAIRAGAdapter,
            RAGSystemType.LANGCHAIN_RAG: LangChainRAGAdapter,
            RAGSystemType.LLAMAINDEX_RAG: LlamaIndexRAGAdapter,
            RAGSystemType.CUSTOM_HTTP: GenericHTTPRAGSystem,
            RAGSystemType.RAG_SERVER_VECTOR: RAGServerVectorAdapter,
            RAGSystemType.RAG_SERVER_BM25: RAGServerBM25Adapter,
            RAGSystemType.RAG_SERVER_HYBRID: RAGServerHybridAdapter,
            RAGSystemType.CODEV_V1: CodevV1RAGAdapter,
            RAGSystemType.MOCK: MockRAGSystem
        }
    
    def register_adapter(self, system_type: RAGSystemType, adapter_class: Type[RAGSystemInterface]):
        """새로운 어댑터 등록"""
        self._adapters[system_type] = adapter_class
        logger.info(f"RAG 시스템 어댑터 등록: {system_type} -> {adapter_class.__name__}")
    
    def create_system(self, config: RAGSystemConfig) -> RAGSystemInterface:
        """RAG 시스템 인스턴스 생성"""
        if config.system_type not in self._adapters:
            raise ValueError(f"지원하지 않는 RAG 시스템 타입: {config.system_type}")
        
        adapter_class = self._adapters[config.system_type]
        
        try:
            # Mock 시스템은 config 없이 생성
            if config.system_type == RAGSystemType.MOCK:
                return adapter_class()
            else:
                return adapter_class(config)
        except Exception as e:
            logger.error(f"RAG 시스템 생성 실패: {e}")
            raise
    
    def get_supported_types(self) -> list[RAGSystemType]:
        """지원하는 RAG 시스템 타입 목록"""
        return list(self._adapters.keys())
    
    def create_from_legacy_config(
        self, 
        base_url: str, 
        api_key: Optional[str] = None,
        system_type: RAGSystemType = RAGSystemType.CUSTOM_HTTP
    ) -> RAGSystemInterface:
        """기존 방식 호환성을 위한 생성 메서드"""
        config = RAGSystemConfig(
            name="legacy-system",
            system_type=system_type,
            retrieval_type=RetrievalType.HYBRID,  # 기본값
            base_url=base_url,
            api_key=api_key
        )
        return self.create_system(config)


# 전역 팩토리 인스턴스
rag_system_factory = RAGSystemFactory()


def create_rag_system(config: RAGSystemConfig) -> RAGSystemInterface:
    """RAG 시스템 생성 헬퍼 함수"""
    return rag_system_factory.create_system(config)


def register_custom_adapter(system_type: RAGSystemType, adapter_class: Type[RAGSystemInterface]):
    """커스텀 어댑터 등록 헬퍼 함수"""
    rag_system_factory.register_adapter(system_type, adapter_class)


def create_rag_server_vector(
    base_url: str = "http://rag-server:8000",
    collection_name: str = "code_chunks",
    api_key: Optional[str] = None,
    name: str = "rag-server-vector"
) -> RAGSystemInterface:
    """RAG 서버 벡터 검색 시스템 생성"""
    config = RAGSystemTemplates.rag_server_vector(base_url, api_key, collection_name)
    config.name = name
    return create_rag_system(config)


def create_rag_server_bm25(
    base_url: str = "http://rag-server:8000",
    index_name: str = "code_index",
    api_key: Optional[str] = None,
    name: str = "rag-server-bm25"
) -> RAGSystemInterface:
    """RAG 서버 BM25 검색 시스템 생성"""
    config = RAGSystemTemplates.rag_server_bm25(base_url, api_key, index_name)
    config.name = name
    return create_rag_system(config)


def create_rag_server_hybrid(
    base_url: str = "http://rag-server:8000",
    collection_name: str = "code_chunks",
    index_name: str = "code_index",
    vector_weight: float = 0.7,
    bm25_weight: float = 0.3,
    use_rrf: bool = True,
    rrf_k: int = 60,
    api_key: Optional[str] = None,
    name: str = "rag-server-hybrid"
) -> RAGSystemInterface:
    """RAG 서버 하이브리드 검색 시스템 생성"""
    config = RAGSystemTemplates.rag_server_hybrid(
        base_url, api_key, collection_name, index_name,
        vector_weight, bm25_weight, use_rrf, rrf_k
    )
    config.name = name
    return create_rag_system(config)


def create_all_rag_server_systems(
    base_url: str = "http://rag-server:8000",
    collection_name: str = "code_chunks",
    index_name: str = "code_index",
    api_key: Optional[str] = None
) -> Dict[str, RAGSystemInterface]:
    """모든 RAG 서버 검색 시스템들을 한번에 생성"""
    return {
        "vector": create_rag_server_vector(base_url, collection_name, api_key, "rag-server-vector"),
        "bm25": create_rag_server_bm25(base_url, index_name, api_key, "rag-server-bm25"),
        "hybrid": create_rag_server_hybrid(base_url, collection_name, index_name, api_key=api_key, name="rag-server-hybrid")
    }


# 사전 정의된 설정 템플릿
class RAGSystemTemplates:
    """자주 사용되는 RAG 시스템 설정 템플릿"""
    
    @staticmethod
    def openai_rag(api_key: str, base_url: Optional[str] = None) -> RAGSystemConfig:
        """OpenAI RAG 설정"""
        return RAGSystemConfig(
            name="openai-rag",
            system_type=RAGSystemType.OPENAI_RAG,
            retrieval_type=RetrievalType.VECTOR,  # OpenAI는 벡터 검색
            base_url=base_url or "https://api.openai.com/v1",
            api_key=api_key,
            timeout=60.0
        )
    
    @staticmethod
    def langchain_rag(base_url: str, api_key: Optional[str] = None) -> RAGSystemConfig:
        """LangChain RAG 설정"""
        return RAGSystemConfig(
            name="langchain-rag",
            system_type=RAGSystemType.LANGCHAIN_RAG,
            retrieval_type=RetrievalType.HYBRID,  # LangChain은 하이브리드 지원
            base_url=base_url,
            api_key=api_key,
            auth_type="api_key",
            auth_header="X-API-Key"
        )
    
    @staticmethod
    def llamaindex_rag(base_url: str, api_key: Optional[str] = None) -> RAGSystemConfig:
        """LlamaIndex RAG 설정"""
        return RAGSystemConfig(
            name="llamaindex-rag",
            system_type=RAGSystemType.LLAMAINDEX_RAG,
            retrieval_type=RetrievalType.HYBRID,  # LlamaIndex는 하이브리드 지원
            base_url=base_url,
            api_key=api_key
        )
    
    @staticmethod
    def custom_http_rag(
        name: str,
        base_url: str,
        api_key: Optional[str] = None,
        retrieval_type: RetrievalType = RetrievalType.HYBRID,
        search_endpoint: str = "/api/v1/search",
        embed_endpoint: str = "/api/v1/embed",
        query_field: str = "query",
        k_field: str = "k",
        results_field: str = "results",
        content_field: str = "content",
        score_field: str = "score",
        filepath_field: str = "filepath"
    ) -> RAGSystemConfig:
        """커스텀 HTTP RAG 설정"""
        from app.features.systems.interface import EndpointConfig, RequestFormat, ResponseFormat
        
        return RAGSystemConfig(
            name=name,
            system_type=RAGSystemType.CUSTOM_HTTP,
            retrieval_type=retrieval_type,
            base_url=base_url,
            api_key=api_key,
            endpoints=EndpointConfig(
                vector_search=search_endpoint,
                bm25_search=search_endpoint,
                hybrid_search=search_endpoint
            ),
            request_format=RequestFormat(
                query_field=query_field,
                top_k_field=k_field
            ),
            response_format=ResponseFormat(
                results_field=results_field,
                content_field=content_field,
                score_field=score_field
            )
        )
    
    @staticmethod
    def rag_server_vector(
        base_url: str = "http://rag-server:8000", 
        api_key: Optional[str] = None,
        collection_name: str = "code_chunks"
    ) -> RAGSystemConfig:
        """RAG 서버 벡터 검색 설정"""
        return RAGSystemConfig(
            name="rag-server-vector",
            system_type=RAGSystemType.RAG_SERVER_VECTOR,
            retrieval_type=RetrievalType.VECTOR,
            base_url=base_url,
            api_key=api_key,
            collection_name=collection_name,
            timeout=30.0
        )
    
    @staticmethod
    def rag_server_bm25(
        base_url: str = "http://rag-server:8000", 
        api_key: Optional[str] = None,
        index_name: str = "code_index"
    ) -> RAGSystemConfig:
        """RAG 서버 BM25 검색 설정"""
        return RAGSystemConfig(
            name="rag-server-bm25",
            system_type=RAGSystemType.RAG_SERVER_BM25,
            retrieval_type=RetrievalType.BM25,
            base_url=base_url,
            api_key=api_key,
            index_name=index_name,
            timeout=30.0
        )
    
    @staticmethod
    def rag_server_hybrid(
        base_url: str = "http://rag-server:8000", 
        api_key: Optional[str] = None,
        collection_name: str = "code_chunks",
        index_name: str = "code_index",
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        use_rrf: bool = True,
        rrf_k: int = 60
    ) -> RAGSystemConfig:
        """RAG 서버 하이브리드 검색 설정"""
        return RAGSystemConfig(
            name="rag-server-hybrid",
            system_type=RAGSystemType.RAG_SERVER_HYBRID,
            retrieval_type=RetrievalType.HYBRID,
            base_url=base_url,
            api_key=api_key,
            collection_name=collection_name,
            index_name=index_name,
            vector_weight=vector_weight,
            bm25_weight=bm25_weight,
            use_rrf=use_rrf,
            rrf_k=rrf_k,
            timeout=30.0
        )
    
    @staticmethod
    def codev_v1(base_url: str = "http://10.250.121.100:8008") -> RAGSystemConfig:
        """Codev-v1 RAG 설정"""
        return RAGSystemConfig(
            name="codev-v1-rag",
            system_type=RAGSystemType.CODEV_V1,
            retrieval_type=RetrievalType.HYBRID,  # CodevV1은 하이브리드 검색
            base_url=base_url,
            timeout=30.0
        )
    
    @staticmethod
    def mock_rag(retrieval_type: RetrievalType = RetrievalType.HYBRID) -> RAGSystemConfig:
        """Mock RAG 설정 (테스트용)"""
        return RAGSystemConfig(
            name="mock-rag",
            system_type=RAGSystemType.MOCK,
            retrieval_type=retrieval_type,
            base_url="http://localhost:8000"
        ) 