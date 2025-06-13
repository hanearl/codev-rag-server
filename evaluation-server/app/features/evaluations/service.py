from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.features.evaluations.repository import EvaluationResultRepository
from app.features.evaluations.model import EvaluationResult
import logging

logger = logging.getLogger(__name__)


class EvaluationHistoryService:
    """평가 결과 히스토리 서비스"""
    
    def __init__(self, repository: EvaluationResultRepository):
        self.repository = repository
    
    def get_evaluation_history(
        self,
        db: Session,
        dataset_id: Optional[str] = None,
        system_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[EvaluationResult]:
        """평가 결과 히스토리 조회"""
        try:
            return self.repository.get_by_filters(
                db=db,
                dataset_id=dataset_id,
                system_name=system_name,
                status=status,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"평가 히스토리 조회 실패: {str(e)}")
            return []
    
    def get_evaluation_by_id(self, db: Session, evaluation_id: int) -> Optional[EvaluationResult]:
        """ID로 평가 결과 조회"""
        try:
            return self.repository.get(db, evaluation_id)
        except Exception as e:
            logger.error(f"평가 결과 조회 실패 (ID: {evaluation_id}): {str(e)}")
            return None
    
    def get_latest_evaluation(
        self,
        db: Session,
        dataset_id: Optional[str] = None,
        system_name: Optional[str] = None
    ) -> Optional[EvaluationResult]:
        """최신 평가 결과 조회"""
        try:
            return self.repository.get_latest(
                db=db,
                dataset_id=dataset_id,
                system_name=system_name
            )
        except Exception as e:
            logger.error(f"최신 평가 결과 조회 실패: {str(e)}")
            return None
    
    def get_evaluation_count(
        self,
        db: Session,
        dataset_id: Optional[str] = None,
        system_name: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """평가 결과 수 조회"""
        try:
            return self.repository.count_by_filters(
                db=db,
                dataset_id=dataset_id,
                system_name=system_name,
                status=status
            )
        except Exception as e:
            logger.error(f"평가 결과 수 조회 실패: {str(e)}")
            return 0
    
    def delete_evaluation(self, db: Session, evaluation_id: int) -> Optional[EvaluationResult]:
        """평가 결과 삭제"""
        try:
            # 존재 여부 확인
            existing = self.repository.get(db, evaluation_id)
            if not existing:
                return None
            
            # 삭제 실행
            return self.repository.remove(db, id=evaluation_id)
        except Exception as e:
            logger.error(f"평가 결과 삭제 실패 (ID: {evaluation_id}): {str(e)}")
            return None
    
    def get_system_performance_summary(
        self, 
        db: Session, 
        system_name: str
    ) -> Dict[str, Any]:
        """시스템 성능 요약 조회"""
        try:
            # 해당 시스템의 모든 평가 결과 조회
            evaluations = self.repository.get_by_filters(
                db=db,
                system_name=system_name,
                status="completed"
            )
            
            if not evaluations:
                return {
                    "total_evaluations": 0,
                    "datasets": [],
                    "average_execution_time": 0.0,
                    "latest_evaluation": None
                }
            
            # 통계 계산
            total_evaluations = len(evaluations)
            datasets = list(set(eval.dataset_id for eval in evaluations))
            avg_execution_time = sum(eval.execution_time for eval in evaluations) / total_evaluations
            latest_evaluation = evaluations[0]  # 이미 최신순으로 정렬됨
            
            return {
                "total_evaluations": total_evaluations,
                "datasets": datasets,
                "average_execution_time": round(avg_execution_time, 2),
                "latest_evaluation": {
                    "id": latest_evaluation.id,
                    "dataset_id": latest_evaluation.dataset_id,
                    "created_at": latest_evaluation.created_at,
                    "metrics": latest_evaluation.metrics
                }
            }
            
        except Exception as e:
            logger.error(f"시스템 성능 요약 조회 실패 (시스템: {system_name}): {str(e)}")
            return {
                "total_evaluations": 0,
                "datasets": [],
                "average_execution_time": 0.0,
                "latest_evaluation": None
            }
    
    def get_dataset_evaluation_summary(
        self, 
        db: Session, 
        dataset_id: str
    ) -> Dict[str, Any]:
        """데이터셋 평가 요약 조회"""
        try:
            # 해당 데이터셋의 모든 평가 결과 조회
            evaluations = self.repository.get_by_filters(
                db=db,
                dataset_id=dataset_id,
                status="completed"
            )
            
            if not evaluations:
                return {
                    "total_evaluations": 0,
                    "systems": [],
                    "latest_evaluation": None
                }
            
            # 통계 계산
            total_evaluations = len(evaluations)
            systems = list(set(eval.system.name for eval in evaluations if eval.system))
            latest_evaluation = evaluations[0]  # 이미 최신순으로 정렬됨
            
            return {
                "total_evaluations": total_evaluations,
                "systems": systems,
                "latest_evaluation": {
                    "id": latest_evaluation.id,
                    "system_name": latest_evaluation.system.name if latest_evaluation.system else "Unknown",
                    "created_at": latest_evaluation.created_at,
                    "metrics": latest_evaluation.metrics
                }
            }
            
        except Exception as e:
            logger.error(f"데이터셋 평가 요약 조회 실패 (데이터셋: {dataset_id}): {str(e)}")
            return {
                "total_evaluations": 0,
                "systems": [],
                "latest_evaluation": None
            }


# 전역 히스토리 서비스 인스턴스
evaluation_history_service = EvaluationHistoryService(
    repository=EvaluationResultRepository()
) 