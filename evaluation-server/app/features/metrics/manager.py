from typing import Dict, List, Any, Optional
from app.features.metrics.interface import MetricCalculator
from app.features.metrics.basic_metrics import (
    RecallAtK, PrecisionAtK, HitAtK, MeanReciprocalRank, NDCG
)


class MetricsManager:
    """메트릭 계산 및 관리 클래스"""
    
    def __init__(self):
        """기본 메트릭들로 초기화"""
        self.metrics: Dict[str, MetricCalculator] = {
            'recall': RecallAtK(),
            'precision': PrecisionAtK(),
            'hit': HitAtK(),
            'mrr': MeanReciprocalRank(),
            'ndcg': NDCG()
        }
    
    def add_metric(self, name: str, metric: MetricCalculator) -> None:
        """
        새로운 메트릭 추가
        
        Args:
            name: 메트릭 이름
            metric: 메트릭 계산기 인스턴스
        """
        self.metrics[name] = metric
    
    def remove_metric(self, name: str) -> None:
        """
        메트릭 제거
        
        Args:
            name: 제거할 메트릭 이름
        """
        if name in self.metrics:
            del self.metrics[name]
    
    def get_metric(self, name: str) -> Optional[MetricCalculator]:
        """
        메트릭 계산기 조회
        
        Args:
            name: 메트릭 이름
            
        Returns:
            메트릭 계산기 인스턴스 또는 None
        """
        return self.metrics.get(name)
    
    def list_metrics(self) -> List[str]:
        """
        사용 가능한 메트릭 목록 반환
        
        Returns:
            메트릭 이름 리스트
        """
        return list(self.metrics.keys())
    
    def calculate_single(
        self, 
        metric_name: str, 
        predictions: List[str], 
        ground_truth: List[str], 
        k: int
    ) -> float:
        """
        단일 메트릭 계산
        
        Args:
            metric_name: 메트릭 이름
            predictions: 예측 결과
            ground_truth: 정답
            k: k 값
            
        Returns:
            계산된 메트릭 값
            
        Raises:
            ValueError: 메트릭이 존재하지 않는 경우
        """
        if metric_name not in self.metrics:
            raise ValueError(f"Unknown metric: {metric_name}")
        
        metric = self.metrics[metric_name]
        return metric.calculate(predictions, ground_truth, k)
    
    def calculate_all(
        self, 
        predictions: List[str], 
        ground_truth: List[str], 
        k_values: List[int],
        selected_metrics: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        모든 메트릭에 대해 K값별로 계산
        
        Args:
            predictions: 예측 결과
            ground_truth: 정답
            k_values: K 값 리스트
            selected_metrics: 계산할 메트릭 이름 리스트 (None이면 모든 메트릭)
            
        Returns:
            {metric_name: {k: value}} 형태의 결과
        """
        if selected_metrics is None:
            selected_metrics = self.list_metrics()
        
        results = {}
        
        for metric_name in selected_metrics:
            if metric_name not in self.metrics:
                continue
                
            metric = self.metrics[metric_name]
            metric_results = {}
            
            for k in k_values:
                try:
                    value = metric.calculate(predictions, ground_truth, k)
                    metric_results[str(k)] = value
                except Exception as e:
                    # 개별 메트릭 계산 실패 시 0으로 처리
                    metric_results[str(k)] = 0.0
            
            results[metric_name] = metric_results
        
        return results
    
    def calculate_average_metrics(
        self, 
        all_predictions: List[List[str]], 
        all_ground_truths: List[List[str]], 
        k_values: List[int],
        selected_metrics: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        여러 쿼리에 대한 평균 메트릭 계산
        
        Args:
            all_predictions: 모든 쿼리의 예측 결과 리스트
            all_ground_truths: 모든 쿼리의 정답 리스트
            k_values: K 값 리스트
            selected_metrics: 계산할 메트릭 이름 리스트
            
        Returns:
            평균 메트릭 결과
        """
        if len(all_predictions) != len(all_ground_truths):
            raise ValueError("predictions and ground_truths must have the same length")
        
        if len(all_predictions) == 0:
            return {}
        
        if selected_metrics is None:
            selected_metrics = self.list_metrics()
        
        # 각 쿼리별 메트릭 계산
        all_results = []
        for predictions, ground_truth in zip(all_predictions, all_ground_truths):
            query_results = self.calculate_all(
                predictions, ground_truth, k_values, selected_metrics
            )
            all_results.append(query_results)
        
        # 평균 계산
        averaged_results = {}
        for metric_name in selected_metrics:
            if metric_name not in self.metrics:
                continue
                
            averaged_results[metric_name] = {}
            
            for k in k_values:
                k_str = str(k)
                values = []
                
                for query_results in all_results:
                    if metric_name in query_results and k_str in query_results[metric_name]:
                        values.append(query_results[metric_name][k_str])
                
                # 평균 계산
                if values:
                    averaged_results[metric_name][k_str] = sum(values) / len(values)
                else:
                    averaged_results[metric_name][k_str] = 0.0
        
        return averaged_results
    
    def get_metric_info(self) -> Dict[str, Dict[str, str]]:
        """
        모든 메트릭의 정보 반환
        
        Returns:
            메트릭 정보 딕셔너리
        """
        info = {}
        for name, metric in self.metrics.items():
            info[name] = {
                "name": metric.name,
                "description": metric.description
            }
        return info


# 전역 메트릭 매니저 인스턴스
default_metrics_manager = MetricsManager() 