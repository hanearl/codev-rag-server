from functools import lru_cache
from app.features.embedding.model import EmbeddingModel
from app.features.embedding.service import EmbeddingService
from app.core.config import settings


@lru_cache()
def get_embedding_model() -> EmbeddingModel:
    """임베딩 모델 인스턴스를 반환 (싱글톤)"""
    return EmbeddingModel(settings.model_name)


def get_embedding_service() -> EmbeddingService:
    """임베딩 서비스 인스턴스를 반환"""
    model = get_embedding_model()
    return EmbeddingService(model) 