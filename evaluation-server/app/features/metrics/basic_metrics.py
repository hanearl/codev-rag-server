import math
from typing import List
from app.features.metrics.interface import MetricCalculator, RankingMetric


class RecallAtK(RankingMetric):
    """Recall@K 메트릭"""
    
    @property
    def name(self) -> str:
        return "recall_at_k"
    
    @property
    def description(self) -> str:
        return "Recall@K measures the fraction of relevant items that are retrieved in the top-k results"
    
    def calculate(self, predictions: List[str], ground_truth: List[str], k: int) -> float:
        """
        Recall@K = (상위 k개 중 관련 있는 항목 수) / (전체 관련 있는 항목 수)
        """
        self.validate_inputs(predictions, ground_truth, k)
        
        # 관련성 점수 계산
        relevance_scores = self.calculate_relevance_scores(predictions, ground_truth, k)
        
        # 상위 k개 중 관련 있는 항목 수
        relevant_retrieved = sum(relevance_scores)
        
        # 전체 관련 있는 항목 수
        total_relevant = len(ground_truth)
        
        # Recall 계산
        if total_relevant == 0:
            return 0.0
        
        return relevant_retrieved / total_relevant


class PrecisionAtK(RankingMetric):
    """Precision@K 메트릭"""
    
    @property
    def name(self) -> str:
        return "precision_at_k"
    
    @property
    def description(self) -> str:
        return "Precision@K measures the fraction of retrieved items that are relevant in the top-k results"
    
    def calculate(self, predictions: List[str], ground_truth: List[str], k: int) -> float:
        """
        Precision@K = (상위 k개 중 관련 있는 항목 수) / k
        """
        self.validate_inputs(predictions, ground_truth, k)
        
        # 관련성 점수 계산
        relevance_scores = self.calculate_relevance_scores(predictions, ground_truth, k)
        
        # 상위 k개 중 관련 있는 항목 수
        relevant_retrieved = sum(relevance_scores)
        
        # 실제로 검색된 항목 수 (k보다 적을 수 있음)
        retrieved_count = min(k, len(predictions))
        
        # Precision 계산
        if retrieved_count == 0:
            return 0.0
        
        return relevant_retrieved / retrieved_count


class HitAtK(RankingMetric):
    """Hit@K 메트릭 (Hit Rate@K)"""
    
    @property
    def name(self) -> str:
        return "hit_at_k"
    
    @property
    def description(self) -> str:
        return "Hit@K measures whether at least one relevant item is found in the top-k results (binary: 0 or 1)"
    
    def calculate(self, predictions: List[str], ground_truth: List[str], k: int) -> float:
        """
        Hit@K = 1 if 상위 k개 중 관련 있는 항목이 하나라도 있으면, 0 otherwise
        """
        self.validate_inputs(predictions, ground_truth, k)
        
        # 관련성 점수 계산
        relevance_scores = self.calculate_relevance_scores(predictions, ground_truth, k)
        
        # 관련 있는 항목이 하나라도 있으면 1, 없으면 0
        return 1.0 if sum(relevance_scores) > 0 else 0.0


class MeanReciprocalRank(RankingMetric):
    """Mean Reciprocal Rank (MRR) 메트릭"""
    
    @property
    def name(self) -> str:
        return "mrr"
    
    @property
    def description(self) -> str:
        return "Mean Reciprocal Rank measures the average of reciprocal ranks of the first relevant item"
    
    def calculate(self, predictions: List[str], ground_truth: List[str], k: int) -> float:
        """
        MRR = 1 / (첫 번째 관련 항목의 순위)
        관련 항목이 없으면 0
        """
        self.validate_inputs(predictions, ground_truth, k)
        
        # 정답을 집합으로 변환
        ground_truth_set = set(ground_truth)
        
        # 첫 번째 관련 항목의 순위 찾기
        for i, pred in enumerate(predictions[:k]):
            if pred in ground_truth_set:
                return 1.0 / (i + 1)  # 순위는 1부터 시작
        
        # 관련 항목이 없으면 0
        return 0.0


class NDCG(RankingMetric):
    """Normalized Discounted Cumulative Gain (NDCG@K) 메트릭"""
    
    @property
    def name(self) -> str:
        return "ndcg_at_k"
    
    @property
    def description(self) -> str:
        return "NDCG@K measures the ranking quality considering the position of relevant items"
    
    def calculate(self, predictions: List[str], ground_truth: List[str], k: int) -> float:
        """
        NDCG@K = DCG@K / IDCG@K
        
        DCG@K = sum(rel_i / log2(i + 1)) for i in [1, k]
        IDCG@K = 이상적인 순서로 정렬했을 때의 DCG@K
        """
        self.validate_inputs(predictions, ground_truth, k)
        
        # DCG 계산
        dcg = self._calculate_dcg(predictions, ground_truth, k)
        
        # IDCG 계산 (이상적인 순서)
        idcg = self._calculate_idcg(ground_truth, k)
        
        # NDCG 계산
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def _calculate_dcg(self, predictions: List[str], ground_truth: List[str], k: int) -> float:
        """DCG 계산"""
        ground_truth_set = set(ground_truth)
        dcg = 0.0
        
        for i, pred in enumerate(predictions[:k]):
            if pred in ground_truth_set:
                # 관련 항목이면 relevance = 1, 아니면 0
                relevance = 1.0
                dcg += relevance / math.log2(i + 2)  # i+2 because log2(1) = 0
        
        return dcg
    
    def _calculate_idcg(self, ground_truth: List[str], k: int) -> float:
        """IDCG 계산 (이상적인 순서)"""
        # 이상적인 경우: 모든 관련 항목이 상위에 위치
        relevant_count = min(len(ground_truth), k)
        idcg = 0.0
        
        for i in range(relevant_count):
            relevance = 1.0
            idcg += relevance / math.log2(i + 2)
        
        return idcg 