from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite:///./evaluation.db"
    
    # 데이터셋 설정
    DATASETS_PATH: str = "./datasets"
    
    # 외부 서비스 URL
    RAG_SERVER_URL: str = "http://rag-server:8000"
    EMBEDDING_SERVER_URL: str = "http://embedding-server:8001"
    LLM_SERVER_URL: str = "http://llm-server:8002"
    VECTOR_DB_URL: str = "http://vector-db:6333"
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    
    # Redis 설정 (Celery용)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # API 설정
    API_V1_PREFIX: str = "/api/v1"
    
    # 보안 설정
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 평가 설정
    DEFAULT_K_VALUES: list = [1, 3, 5, 10]
    DEFAULT_METRICS: list = ["recall", "precision", "hit"]
    MAX_CONCURRENT_EVALUATIONS: int = 3
    
    # 모니터링 설정
    ENABLE_MONITORING: bool = True
    ALERT_WEBHOOK_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 전역 설정 인스턴스
settings = Settings() 