from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.sql import func
from app.db.database import Base


class RAGSystem(Base):
    """RAG 시스템 모델"""
    __tablename__ = "rag_systems"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # RAG 시스템 정보
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    base_url = Column(String(512), nullable=False)
    api_key = Column(String(255), nullable=True)  # 암호화 필요
    system_type = Column(String(50), nullable=False, default="external")  # external, mock, local
    
    # 설정 정보 (JSON 형태로 저장)
    config = Column(JSON, default=dict)
    
    def __repr__(self):
        return f"<RAGSystem(id={self.id}, name='{self.name}', type='{self.system_type}')>" 