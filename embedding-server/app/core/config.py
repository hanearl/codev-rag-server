from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    host: str = "0.0.0.0"
    port: int = 8001
    
    class Config:
        env_file = ".env"


# 전역 설정 인스턴스
settings = Settings() 