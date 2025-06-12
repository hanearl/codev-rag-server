from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class EvaluationResult(Base):
    """평가 결과 모델"""
    __tablename__ = "evaluation_results"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 평가 정보
    system_id = Column(Integer, ForeignKey("rag_systems.id"), nullable=False, index=True)
    dataset_id = Column(String(255), nullable=False, index=True)  # 데이터셋 이름
    
    # 평가 결과
    metrics = Column(JSON, nullable=False)  # 메트릭 결과들
    execution_time = Column(Float, nullable=False)  # 실행 시간 (초)
    
    # 평가 설정
    config = Column(JSON, default=dict)  # 평가 시 사용된 설정
    
    # 상태 정보
    status = Column(String(50), default="completed")  # completed, failed, running
    error_message = Column(Text, nullable=True)
    
    # 관계 설정
    system = relationship("RAGSystem", backref="evaluation_results")
    
    def __repr__(self):
        return f"<EvaluationResult(id={self.id}, system_id={self.system_id}, dataset='{self.dataset_id}')>"


class EvaluationTask(Base):
    """평가 작업 모델 (비동기 처리용)"""
    __tablename__ = "evaluation_tasks"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # 작업 정보
    task_id = Column(String(255), unique=True, index=True)  # Celery task ID
    system_id = Column(Integer, ForeignKey("rag_systems.id"), nullable=False)
    dataset_id = Column(String(255), nullable=False)
    
    # 작업 상태
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    progress = Column(Float, default=0.0)  # 진행률 (0.0 ~ 1.0)
    
    # 결과 연결
    result_id = Column(Integer, ForeignKey("evaluation_results.id"), nullable=True)
    
    # 관계 설정
    system = relationship("RAGSystem")
    result = relationship("EvaluationResult")
    
    def __repr__(self):
        return f"<EvaluationTask(id={self.id}, task_id='{self.task_id}', status='{self.status}')>" 