"""
외부 서비스 호출을 위한 커스텀 예외 클래스들
"""


class ExternalServiceError(Exception):
    """외부 서비스 호출 오류 기본 클래스"""
    pass


class EmbeddingServiceError(ExternalServiceError):
    """임베딩 서비스 호출 오류"""
    pass


class LLMServiceError(ExternalServiceError):
    """LLM 서비스 호출 오류"""
    pass


class VectorDBError(ExternalServiceError):
    """벡터 DB 접근 오류"""
    pass 