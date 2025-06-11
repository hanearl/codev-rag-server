from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""
    openai_api_key: str
    model_name: str = "gpt-4o-mini"
    host: str = "0.0.0.0"
    port: int = 8002
    openai_base_url: Optional[str] = None
    
    class Config:
        env_file = ".env"


# 전역 설정 인스턴스
settings = Settings() 