from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.features.baselines.repository import BaselineRepository
from app.features.baselines.model import Baseline
from app.features.evaluations.model import EvaluationResult
from app.features.evaluation.schema import BaselineComparison
import logging

logger = logging.getLogger(__name__)


class BaselineService:
    """베이스라인 서비스"""
    
    def __init__(self, baseline_repository: BaselineRepository):
        self.baseline_repository = baseline_repository
    
    async def register_baseline(
        self,
        db: Session,
        name: str,
        description: str,
        evaluation_result_id: int
    ) -> Baseline:
        """평가 결과를 베이스라인으로 등록"""
        # 평가 결과 조회
        evaluation_result = db.query(EvaluationResult).filter(
            EvaluationResult.id == evaluation_result_id
        ).first()
        
        if not evaluation_result:
            raise ValueError(f"Evaluation result not found: {evaluation_result_id}")
        
        # 동일한 이름의 베이스라인이 있는지 확인
        existing_baseline = self.baseline_repository.get_by_name_and_dataset(
            db, name, evaluation_result.dataset_id
        )
        
        if existing_baseline:
            raise ValueError(f"Baseline with name '{name}' already exists for dataset '{evaluation_result.dataset_id}'")
        
        # 베이스라인 생성
        baseline_data = {
            "name": name,
            "description": description,
            "dataset_id": evaluation_result.dataset_id,
            "evaluation_result_id": evaluation_result_id
        }
        
        logger.info(f"베이스라인 등록: {name} (데이터셋: {evaluation_result.dataset_id})")
        return self.baseline_repository.create(db, obj_in=baseline_data)
    
    async def compare_with_baseline(
        self,
        db: Session,
        baseline_id: int,
        current_result: EvaluationResult
    ) -> BaselineComparison:
        """현재 결과를 베이스라인과 비교"""
        baseline = self.baseline_repository.get(db, baseline_id)
        if not baseline:
            raise ValueError(f"Baseline not found: {baseline_id}")
        
        baseline_result = baseline.evaluation_result
        
        # 메트릭별 개선도 계산
        metric_improvements = {}
        for metric_name, k_results in current_result.metrics.items():
            if metric_name in baseline_result.metrics:
                metric_improvements[metric_name] = {}
                baseline_k_results = baseline_result.metrics[metric_name]
                
                for k, current_value in k_results.items():
                    if k in baseline_k_results:
                        baseline_value = baseline_k_results[k]
                        if baseline_value != 0:
                            improvement = ((current_value - baseline_value) / baseline_value) * 100
                        else:
                            improvement = 0.0 if current_value == 0 else 100.0
                        metric_improvements[metric_name][k] = improvement
        
        is_better = self._is_overall_better(metric_improvements)
        
        logger.info(f"베이스라인 비교 완료: baseline_id={baseline_id}, is_better={is_better}")
        
        return BaselineComparison(
            baseline_id=str(baseline_id),
            current_result_id=str(current_result.id),
            metric_improvements=metric_improvements,
            is_better=is_better
        )
    
    def _is_overall_better(self, improvements: Dict[str, Any]) -> bool:
        """전체적으로 성능이 개선되었는지 판단"""
        all_improvements = []
        for metric_improvements in improvements.values():
            if isinstance(metric_improvements, dict):
                all_improvements.extend(metric_improvements.values())
        
        return sum(all_improvements) > 0 if all_improvements else False
    
    async def list_baselines(
        self,
        db: Session,
        dataset_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Baseline]:
        """베이스라인 목록 조회"""
        if dataset_id:
            return self.baseline_repository.get_by_dataset(db, dataset_id)
        else:
            return self.baseline_repository.get_multi(db, skip=skip, limit=limit)
    
    async def get_baseline_by_id(self, db: Session, baseline_id: int) -> Optional[Baseline]:
        """ID로 베이스라인 조회"""
        return self.baseline_repository.get(db, baseline_id)
    
    async def deactivate_baseline(self, db: Session, baseline_id: int) -> Optional[Baseline]:
        """베이스라인 비활성화"""
        baseline = self.baseline_repository.get(db, baseline_id)
        if not baseline:
            raise ValueError(f"Baseline not found: {baseline_id}")
        
        logger.info(f"베이스라인 비활성화: {baseline.name} (ID: {baseline_id})")
        return self.baseline_repository.deactivate_baseline(db, baseline_id) 