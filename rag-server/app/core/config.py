from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Server API"
    VERSION: str = "0.1.0"
    
    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # 보안 설정
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 환경 설정
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # 외부 서비스 설정
    embedding_server_url: str = "http://localhost:8001"
    llm_server_url: str = "http://localhost:8002"
    qdrant_host: str = "qdrant-server"
    qdrant_port: int = 6333
    request_timeout: int = 30
    max_retries: int = 3
    
    class Config:
        env_file = ".env"


settings = Settings() 