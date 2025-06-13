from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from app.core.repository import BaseRepository
from app.features.evaluations.model import EvaluationResult
from app.features.systems.model import RAGSystem


class EvaluationResultRepository(BaseRepository[EvaluationResult]):
    """평가 결과 저장소"""
    
    def __init__(self):
        super().__init__(EvaluationResult)
    
    def get_by_filters(
        self,
        db: Session,
        dataset_id: Optional[str] = None,
        system_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[EvaluationResult]:
        """필터 조건으로 평가 결과 조회"""
        query = db.query(EvaluationResult).options(joinedload(EvaluationResult.system))
        
        # 필터 적용
        if dataset_id:
            query = query.filter(EvaluationResult.dataset_id == dataset_id)
        
        if system_name:
            query = query.join(RAGSystem).filter(RAGSystem.name == system_name)
        
        if status:
            query = query.filter(EvaluationResult.status == status)
        
        # 최신순 정렬 및 페이지네이션
        return query.order_by(desc(EvaluationResult.created_at))\
                   .offset(offset)\
                   .limit(limit)\
                   .all()
    
    def get_latest(
        self,
        db: Session,
        dataset_id: Optional[str] = None,
        system_name: Optional[str] = None
    ) -> Optional[EvaluationResult]:
        """최신 평가 결과 조회"""
        query = db.query(EvaluationResult).options(joinedload(EvaluationResult.system))
        
        if dataset_id:
            query = query.filter(EvaluationResult.dataset_id == dataset_id)
        
        if system_name:
            query = query.join(RAGSystem).filter(RAGSystem.name == system_name)
        
        return query.order_by(desc(EvaluationResult.created_at)).first()
    
    def count_by_filters(
        self,
        db: Session,
        dataset_id: Optional[str] = None,
        system_name: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """필터 조건으로 평가 결과 수 조회"""
        query = db.query(func.count(EvaluationResult.id))
        
        if dataset_id:
            query = query.filter(EvaluationResult.dataset_id == dataset_id)
        
        if system_name:
            query = query.join(RAGSystem).filter(RAGSystem.name == system_name)
        
        if status:
            query = query.filter(EvaluationResult.status == status)
        
        return query.scalar()
    
    def get_by_dataset_and_system(
        self,
        db: Session,
        dataset_id: str,
        system_id: int,
        limit: int = 10
    ) -> List[EvaluationResult]:
        """특정 데이터셋과 시스템의 평가 결과 조회"""
        return db.query(EvaluationResult)\
                .options(joinedload(EvaluationResult.system))\
                .filter(
                    EvaluationResult.dataset_id == dataset_id,
                    EvaluationResult.system_id == system_id
                )\
                .order_by(desc(EvaluationResult.created_at))\
                .limit(limit)\
                .all()
    
    def get_datasets_by_system(self, db: Session, system_name: str) -> List[str]:
        """특정 시스템이 평가한 데이터셋 목록 조회"""
        result = db.query(EvaluationResult.dataset_id.distinct())\
                  .join(RAGSystem)\
                  .filter(RAGSystem.name == system_name)\
                  .all()
        
        return [row[0] for row in result]
    
    def get_systems_by_dataset(self, db: Session, dataset_id: str) -> List[str]:
        """특정 데이터셋을 평가한 시스템 목록 조회"""
        result = db.query(RAGSystem.name.distinct())\
                  .join(EvaluationResult)\
                  .filter(EvaluationResult.dataset_id == dataset_id)\
                  .all()
        
        return [row[0] for row in result]


evaluation_result_repository = EvaluationResultRepository() 