from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import Field


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
    
    # OpenAI API 설정 (LLM 서버가 OpenAI 호환 API 제공)
    openai_api_key: str = Field(default="sk-dummy-key", env="OPENAI_API_KEY")
    openai_api_base_url: str = Field(default="http://localhost:8002/v1", env="OPENAI_API_BASE_URL")
    
    class Config:
        env_file = ".env"


settings = Settings() 