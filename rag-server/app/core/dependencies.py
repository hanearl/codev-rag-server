from functools import lru_cache
from .clients import EmbeddingClient, VectorClient
from .config import settings
from app.features.indexing.parser_factory import CodeParserFactory
from app.features.indexing.service import IndexingService

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
def get_parser_factory() -> CodeParserFactory:
    return CodeParserFactory()

def get_indexing_service() -> IndexingService:
    return IndexingService(
        embedding_client=get_embedding_client(),
        vector_client=get_vector_client(),
        parser_factory=get_parser_factory()
    ) 