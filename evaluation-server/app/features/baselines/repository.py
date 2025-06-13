from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.repository import BaseRepository
from app.features.baselines.model import Baseline


class BaselineRepository(BaseRepository[Baseline]):
    """베이스라인 저장소"""
    
    def __init__(self):
        super().__init__(Baseline)
    
    def get_by_dataset(self, db: Session, dataset_id: str) -> List[Baseline]:
        """데이터셋별 베이스라인 조회"""
        return db.query(Baseline).filter(
            Baseline.dataset_id == dataset_id,
            Baseline.is_active == True
        ).order_by(Baseline.created_at.desc()).all()
    
    def get_active_baseline(self, db: Session, dataset_id: str) -> Optional[Baseline]:
        """활성 베이스라인 조회 (가장 최근)"""
        return db.query(Baseline).filter(
            Baseline.dataset_id == dataset_id,
            Baseline.is_active == True
        ).order_by(Baseline.created_at.desc()).first()
    
    def get_by_name_and_dataset(
        self, 
        db: Session, 
        name: str, 
        dataset_id: str
    ) -> Optional[Baseline]:
        """이름과 데이터셋으로 베이스라인 조회"""
        return db.query(Baseline).filter(
            Baseline.name == name,
            Baseline.dataset_id == dataset_id,
            Baseline.is_active == True
        ).first()
    
    def deactivate_baseline(self, db: Session, baseline_id: int) -> Optional[Baseline]:
        """베이스라인 비활성화"""
        baseline = self.get(db, baseline_id)
        if baseline:
            baseline.is_active = False
            db.commit()
            db.refresh(baseline)
        return baseline 