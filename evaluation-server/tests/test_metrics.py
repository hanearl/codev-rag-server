import pytest
import math
from app.features.metrics.basic_metrics import (
    RecallAtK, PrecisionAtK, HitAtK, MeanReciprocalRank, NDCG
)
from app.features.metrics.manager import MetricsManager


class TestRecallAtK:
    """Recall@K 메트릭 테스트"""
    
    def setup_method(self):
        self.metric = RecallAtK()
    
    def test_perfect_recall(self):
        """완벽한 Recall 테스트"""
        # Given
        predictions = ["A", "B", "C", "D", "E"]
        ground_truth = ["A", "B", "C"]
        k = 5
        
        # When
        recall = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert recall == 1.0  # 3/3 = 1.0
    
    def test_partial_recall(self):
        """부분적 Recall 테스트"""
        # Given
        predictions = ["A", "X", "B", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 5
        
        # When
        recall = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert recall == 2/3  # 2/3 ≈ 0.667
    
    def test_zero_recall(self):
        """Recall이 0인 경우 테스트"""
        # Given
        predictions = ["X", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 3
        
        # When
        recall = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert recall == 0.0
    
    def test_recall_with_k_limit(self):
        """K 제한이 있는 Recall 테스트"""
        # Given
        predictions = ["A", "X", "Y", "B", "C"]
        ground_truth = ["A", "B", "C"]
        k = 3  # 상위 3개만 고려
        
        # When
        recall = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert recall == 1/3  # 1/3 ≈ 0.333


class TestPrecisionAtK:
    """Precision@K 메트릭 테스트"""
    
    def setup_method(self):
        self.metric = PrecisionAtK()
    
    def test_perfect_precision(self):
        """완벽한 Precision 테스트"""
        # Given
        predictions = ["A", "B", "C"]
        ground_truth = ["A", "B", "C", "D", "E"]
        k = 3
        
        # When
        precision = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert precision == 1.0  # 3/3 = 1.0
    
    def test_partial_precision(self):
        """부분적 Precision 테스트"""
        # Given
        predictions = ["A", "X", "B", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 5
        
        # When
        precision = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert precision == 2/5  # 2/5 = 0.4
    
    def test_zero_precision(self):
        """Precision이 0인 경우 테스트"""
        # Given
        predictions = ["X", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 3
        
        # When
        precision = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert precision == 0.0


class TestHitAtK:
    """Hit@K 메트릭 테스트"""
    
    def setup_method(self):
        self.metric = HitAtK()
    
    def test_hit_found(self):
        """Hit가 발견된 경우 테스트"""
        # Given
        predictions = ["X", "A", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 4
        
        # When
        hit = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert hit == 1.0
    
    def test_hit_not_found(self):
        """Hit가 발견되지 않은 경우 테스트"""
        # Given
        predictions = ["X", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 3
        
        # When
        hit = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert hit == 0.0
    
    def test_hit_at_first_position(self):
        """첫 번째 위치에서 Hit 테스트"""
        # Given
        predictions = ["A", "X", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 4
        
        # When
        hit = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert hit == 1.0


class TestMeanReciprocalRank:
    """MRR 메트릭 테스트"""
    
    def setup_method(self):
        self.metric = MeanReciprocalRank()
    
    def test_mrr_first_position(self):
        """첫 번째 위치에서 관련 항목 발견"""
        # Given
        predictions = ["A", "X", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 4
        
        # When
        mrr = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert mrr == 1.0  # 1/1 = 1.0
    
    def test_mrr_second_position(self):
        """두 번째 위치에서 관련 항목 발견"""
        # Given
        predictions = ["X", "A", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 4
        
        # When
        mrr = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert mrr == 0.5  # 1/2 = 0.5
    
    def test_mrr_third_position(self):
        """세 번째 위치에서 관련 항목 발견"""
        # Given
        predictions = ["X", "Y", "A", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 4
        
        # When
        mrr = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert mrr == pytest.approx(1/3, rel=1e-3)  # 1/3 ≈ 0.333
    
    def test_mrr_no_relevant(self):
        """관련 항목이 없는 경우"""
        # Given
        predictions = ["X", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 3
        
        # When
        mrr = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert mrr == 0.0


class TestNDCG:
    """NDCG 메트릭 테스트"""
    
    def setup_method(self):
        self.metric = NDCG()
    
    def test_perfect_ndcg(self):
        """완벽한 순서의 NDCG 테스트"""
        # Given
        predictions = ["A", "B", "C", "X", "Y"]
        ground_truth = ["A", "B", "C"]
        k = 5
        
        # When
        ndcg = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert ndcg == 1.0  # 완벽한 순서
    
    def test_reversed_ndcg(self):
        """역순의 NDCG 테스트"""
        # Given
        predictions = ["X", "Y", "C", "B", "A"]
        ground_truth = ["A", "B", "C"]
        k = 5
        
        # When
        ndcg = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        # DCG = 1/log2(4) + 1/log2(5) + 1/log2(6)
        # IDCG = 1/log2(2) + 1/log2(3) + 1/log2(4)
        expected_dcg = 1/math.log2(4) + 1/math.log2(5) + 1/math.log2(6)
        expected_idcg = 1/math.log2(2) + 1/math.log2(3) + 1/math.log2(4)
        expected_ndcg = expected_dcg / expected_idcg
        
        assert ndcg == pytest.approx(expected_ndcg, rel=1e-3)
    
    def test_zero_ndcg(self):
        """NDCG가 0인 경우 테스트"""
        # Given
        predictions = ["X", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 3
        
        # When
        ndcg = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        assert ndcg == 0.0
    
    def test_partial_ndcg(self):
        """부분적 NDCG 테스트"""
        # Given
        predictions = ["A", "X", "B", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 5
        
        # When
        ndcg = self.metric.calculate(predictions, ground_truth, k)
        
        # Then
        # DCG = 1/log2(2) + 1/log2(4)
        # IDCG = 1/log2(2) + 1/log2(3) + 1/log2(4)
        expected_dcg = 1/math.log2(2) + 1/math.log2(4)
        expected_idcg = 1/math.log2(2) + 1/math.log2(3) + 1/math.log2(4)
        expected_ndcg = expected_dcg / expected_idcg
        
        assert ndcg == pytest.approx(expected_ndcg, rel=1e-3)


class TestMetricsValidation:
    """메트릭 입력값 검증 테스트"""
    
    def setup_method(self):
        self.metric = RecallAtK()
    
    def test_invalid_predictions_type(self):
        """잘못된 predictions 타입"""
        with pytest.raises(ValueError, match="predictions must be a list"):
            self.metric.calculate("not_a_list", ["A", "B"], 3)
    
    def test_invalid_ground_truth_type(self):
        """잘못된 ground_truth 타입"""
        with pytest.raises(ValueError, match="ground_truth must be a list"):
            self.metric.calculate(["A", "B"], "not_a_list", 3)
    
    def test_invalid_k_value(self):
        """잘못된 k 값"""
        with pytest.raises(ValueError, match="k must be positive"):
            self.metric.calculate(["A", "B"], ["A", "B"], 0)
    
    def test_empty_ground_truth(self):
        """빈 ground_truth"""
        with pytest.raises(ValueError, match="ground_truth cannot be empty"):
            self.metric.calculate(["A", "B"], [], 3)


class TestMetricsManager:
    """메트릭 매니저 테스트"""
    
    def setup_method(self):
        self.manager = MetricsManager()
    
    def test_default_metrics_loaded(self):
        """기본 메트릭들이 로드되었는지 확인"""
        # When
        metrics = self.manager.list_metrics()
        
        # Then
        expected_metrics = ['recall', 'precision', 'hit', 'mrr', 'ndcg']
        assert all(metric in metrics for metric in expected_metrics)
    
    def test_add_custom_metric(self):
        """커스텀 메트릭 추가 테스트"""
        # Given
        custom_metric = RecallAtK()
        
        # When
        self.manager.add_metric("custom_recall", custom_metric)
        
        # Then
        assert "custom_recall" in self.manager.list_metrics()
        assert self.manager.get_metric("custom_recall") is custom_metric
    
    def test_remove_metric(self):
        """메트릭 제거 테스트"""
        # Given
        initial_count = len(self.manager.list_metrics())
        
        # When
        self.manager.remove_metric("recall")
        
        # Then
        assert len(self.manager.list_metrics()) == initial_count - 1
        assert "recall" not in self.manager.list_metrics()
    
    def test_calculate_single_metric(self):
        """단일 메트릭 계산 테스트"""
        # Given
        predictions = ["A", "X", "B", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k = 5
        
        # When
        recall = self.manager.calculate_single("recall", predictions, ground_truth, k)
        
        # Then
        assert recall == 2/3  # 2/3
    
    def test_calculate_single_unknown_metric(self):
        """존재하지 않는 메트릭 계산 시 오류"""
        with pytest.raises(ValueError, match="Unknown metric: unknown"):
            self.manager.calculate_single("unknown", ["A"], ["A"], 1)
    
    def test_calculate_all_metrics(self):
        """모든 메트릭 계산 테스트"""
        # Given
        predictions = ["A", "X", "B", "Y", "Z"]
        ground_truth = ["A", "B", "C"]
        k_values = [1, 3, 5]
        
        # When
        results = self.manager.calculate_all(predictions, ground_truth, k_values)
        
        # Then
        assert "recall" in results
        assert "precision" in results
        assert "hit" in results
        assert "mrr" in results
        assert "ndcg" in results
        
        # 각 메트릭에 대해 k 값별 결과 확인
        for metric_name in results:
            for k in k_values:
                assert str(k) in results[metric_name]
                assert isinstance(results[metric_name][str(k)], float)
    
    def test_calculate_selected_metrics(self):
        """선택된 메트릭만 계산 테스트"""
        # Given
        predictions = ["A", "X", "B"]
        ground_truth = ["A", "B", "C"]
        k_values = [3]
        selected_metrics = ["recall", "precision"]
        
        # When
        results = self.manager.calculate_all(
            predictions, ground_truth, k_values, selected_metrics
        )
        
        # Then
        assert len(results) == 2
        assert "recall" in results
        assert "precision" in results
        assert "hit" not in results
    
    def test_calculate_average_metrics(self):
        """평균 메트릭 계산 테스트"""
        # Given
        all_predictions = [
            ["A", "X", "B"],
            ["B", "Y", "C"],
            ["C", "Z", "A"]
        ]
        all_ground_truths = [
            ["A", "B"],
            ["B", "C"],
            ["A", "C"]
        ]
        k_values = [2, 3]
        
        # When
        avg_results = self.manager.calculate_average_metrics(
            all_predictions, all_ground_truths, k_values
        )
        
        # Then
        assert "recall" in avg_results
        assert "precision" in avg_results
        
        # 각 k 값에 대해 평균이 계산되었는지 확인
        for k in k_values:
            assert str(k) in avg_results["recall"]
            assert isinstance(avg_results["recall"][str(k)], float)
    
    def test_get_metric_info(self):
        """메트릭 정보 조회 테스트"""
        # When
        info = self.manager.get_metric_info()
        
        # Then
        assert "recall" in info
        assert "name" in info["recall"]
        assert "description" in info["recall"]
        assert info["recall"]["name"] == "recall_at_k" 