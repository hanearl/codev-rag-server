from functools import lru_cache
from .clients import EmbeddingClient, VectorClient, LLMClient
from .config import settings
from app.features.indexing.parser_factory import CodeParserFactory
from app.features.indexing.service import IndexingService
from app.features.search.retriever import HybridRetriever
from app.features.search.scorer import SearchScorer
from app.features.search.service import SearchService

# prompts 모듈 임포트 추가
from app.features.prompts.repository import PromptRepository
from app.features.prompts.manager import PromptManager as BasePromptManager
from app.features.prompts.service import PromptService

# generation 모듈 임포트 추가
from app.features.generation.prompt_manager import PromptManager
from app.features.generation.generator import CodeGenerator
from app.features.generation.validator import CodeValidator
from app.features.generation.service import GenerationService

@lru_cache()
def get_settings():
    return settings

@lru_cache()
def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient(
        base_url=settings.embedding_server_url,
        timeout=settings.request_timeout,
        max_retries=settings.max_retries
    )

@lru_cache()
def get_vector_client() -> VectorClient:
    return VectorClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port
    )

@lru_cache()
def get_llm_client() -> LLMClient:
    """LLM 클라이언트 의존성"""
    return LLMClient(
        base_url=settings.llm_server_url,
        timeout=120.0,  # 생성 작업은 더 긴 타임아웃 필요
        max_retries=settings.max_retries
    )

@lru_cache()
def get_parser_factory() -> CodeParserFactory:
    return CodeParserFactory()

def get_indexing_service() -> IndexingService:
    return IndexingService(
        embedding_client=get_embedding_client(),
        vector_client=get_vector_client(),
        parser_factory=get_parser_factory()
    )

@lru_cache()
def get_search_retriever() -> HybridRetriever:
    return HybridRetriever(
        embedding_client=get_embedding_client(),
        vector_client=get_vector_client()
    )

@lru_cache()
def get_search_scorer() -> SearchScorer:
    return SearchScorer()

def get_search_service() -> SearchService:
    return SearchService(
        retriever=get_search_retriever(),
        scorer=get_search_scorer()
    )

# prompts 모듈 의존성
@lru_cache()
def get_prompt_repository() -> PromptRepository:
    return PromptRepository()

@lru_cache()
def get_base_prompt_manager() -> BasePromptManager:
    return BasePromptManager(repository=get_prompt_repository())

def get_prompt_service() -> PromptService:
    return PromptService(
        manager=get_base_prompt_manager(),
        repository=get_prompt_repository()
    )

# generation 모듈 의존성
@lru_cache()
def get_prompt_manager() -> PromptManager:
    """생성용 프롬프트 매니저 (기존 prompts 모듈 활용)"""
    return PromptManager(repository=get_prompt_repository())

@lru_cache()
def get_code_validator() -> CodeValidator:
    return CodeValidator()

@lru_cache()
def get_code_generator() -> CodeGenerator:
    return CodeGenerator(
        llm_client=get_llm_client(),
        prompt_manager=get_prompt_manager()
    )

def get_generation_service() -> GenerationService:
    return GenerationService(
        search_service=get_search_service(),
        generator=get_code_generator(),
        validator=get_code_validator()
    ) 