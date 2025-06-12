from abc import ABC, abstractmethod
from typing import List, Dict, Any


class MetricCalculator(ABC):
    """메트릭 계산기 추상 인터페이스"""
    
    @abstractmethod
    def calculate(self, predictions: List[str], ground_truth: List[str], k: int) -> float:
        """
        메트릭을 계산합니다.
        
        Args:
            predictions: 예측된 결과 리스트 (순서대로 정렬됨)
            ground_truth: 정답 리스트
            k: 상위 k개 결과에 대해 계산
            
        Returns:
            계산된 메트릭 값
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """메트릭 이름"""
        pass
    
    @property
    def description(self) -> str:
        """메트릭 설명 (선택적 구현)"""
        return f"{self.name} metric"
    
    def validate_inputs(self, predictions: List[str], ground_truth: List[str], k: int) -> None:
        """
        입력값 검증
        
        Args:
            predictions: 예측 결과
            ground_truth: 정답
            k: k 값
            
        Raises:
            ValueError: 입력값이 유효하지 않은 경우
        """
        if not isinstance(predictions, list):
            raise ValueError("predictions must be a list")
        
        if not isinstance(ground_truth, list):
            raise ValueError("ground_truth must be a list")
        
        if k <= 0:
            raise ValueError("k must be positive")
        
        if len(ground_truth) == 0:
            raise ValueError("ground_truth cannot be empty")


class RankingMetric(MetricCalculator):
    """순위 기반 메트릭의 기본 클래스"""
    
    def calculate_relevance_scores(self, predictions: List[str], ground_truth: List[str], k: int) -> List[int]:
        """
        각 예측 결과의 관련성 점수를 계산합니다.
        
        Args:
            predictions: 예측 결과
            ground_truth: 정답
            k: 상위 k개
            
        Returns:
            관련성 점수 리스트 (1: 관련, 0: 비관련)
        """
        # 정답을 집합으로 변환 (빠른 검색을 위해)
        ground_truth_set = set(ground_truth)
        
        # 상위 k개 예측 결과에 대해 관련성 점수 계산
        relevance_scores = []
        for i, pred in enumerate(predictions[:k]):
            if pred in ground_truth_set:
                relevance_scores.append(1)
            else:
                relevance_scores.append(0)
        
        return relevance_scores 