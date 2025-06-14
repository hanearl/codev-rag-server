from pydantic import Field
from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Server API"
    VERSION: str = "0.1.0"
    
    # 환경 설정
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    log_level: str = "DEBUG"
    
    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # 보안 설정
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 외부 서비스 설정 (Docker 컨테이너 환경)
    embedding_server_url: str = "http://embedding-server:8001"
    llm_server_url: str = "http://llm-server:8002"
    vector_db_url: str = "http://vector-db:6333"
    
    # 모델 설정
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_model_name: str = "gpt-4o-mini"
    
    # 서버 설정
    embedding_server_host: str = "0.0.0.0"
    embedding_server_port: str = "8001"
    llm_server_host: str = "0.0.0.0"
    llm_server_port: str = "8002"
    rag_server_host: str = "0.0.0.0"
    rag_server_port: str = "8000"
    
    # Qdrant 설정
    qdrant_host: str = "vector-db"  # Docker 컨테이너 내에서는 서비스 이름 사용
    qdrant_port: int = 6333
    qdrant_collection_name: str = "code_embeddings"
    
    # 기타 설정
    request_timeout: int = 30
    max_retries: int = 3
    
    # OpenAI API 설정 (LLM 서버가 OpenAI 호환 API 제공)
    openai_api_key: str = Field(default="sk-dummy-key", env="OPENAI_API_KEY")
    openai_api_base_url: str = Field(default="http://localhost:8002/v1", env="OPENAI_API_BASE_URL")
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # 정의되지 않은 필드 무시


settings = Settings() 