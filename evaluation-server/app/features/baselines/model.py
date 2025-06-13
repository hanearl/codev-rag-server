from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class Baseline(Base):
    """베이스라인 모델"""
    __tablename__ = "baselines"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # 베이스라인 정보
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    dataset_id = Column(String(255), nullable=False, index=True)
    evaluation_result_id = Column(Integer, ForeignKey("evaluation_results.id"), nullable=False)
    
    # 관계 설정
    evaluation_result = relationship("EvaluationResult", backref="baselines")
    
    def __repr__(self):
        return f"<Baseline(id={self.id}, name='{self.name}', dataset='{self.dataset_id}')>" 