import pytest
import numpy as np
from unittest.mock import Mock, patch
from app.features.evaluation.statistics import EvaluationStatistics
from typing import List, Dict, Any


class TestEvaluationStatistics:
    """평가 통계 서비스 테스트"""
    
    @pytest.fixture
    def evaluation_statistics(self):
        """평가 통계 서비스 인스턴스"""
        return EvaluationStatistics()

    def test_calculate_response_time_stats_should_return_correct_stats_when_valid_times(
        self, evaluation_statistics
    ):
        """유효한 응답 시간 리스트로 통계 계산 시 올바른 통계를 반환해야 함"""
        # Given
        response_times = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        # When
        result = evaluation_statistics.calculate_response_time_stats(response_times)
        
        # Then
        assert result['average'] == 3.0
        assert result['median'] == 3.0
        assert result['min'] == 1.0
        assert result['max'] == 5.0
        assert abs(result['std'] - np.std(response_times)) < 1e-10

    def test_calculate_response_time_stats_should_return_zeros_when_empty_list(
        self, evaluation_statistics
    ):
        """빈 응답 시간 리스트로 통계 계산 시 0값들을 반환해야 함"""
        # Given
        response_times = []
        
        # When
        result = evaluation_statistics.calculate_response_time_stats(response_times)
        
        # Then
        assert result['average'] == 0.0
        assert result['median'] == 0.0
        assert result['std'] == 0.0
        assert result['min'] == 0.0
        assert result['max'] == 0.0

    def test_calculate_response_time_stats_should_handle_single_value(
        self, evaluation_statistics
    ):
        """단일 값 응답 시간으로 통계 계산 시 올바른 값을 반환해야 함"""
        # Given
        response_times = [2.5]
        
        # When
        result = evaluation_statistics.calculate_response_time_stats(response_times)
        
        # Then
        assert result['average'] == 2.5
        assert result['median'] == 2.5
        assert result['min'] == 2.5
        assert result['max'] == 2.5
        assert result['std'] == 0.0

    def test_calculate_response_time_stats_should_handle_outliers(
        self, evaluation_statistics
    ):
        """이상치가 있는 응답 시간으로 통계 계산 시 올바른 값을 반환해야 함"""
        # Given
        response_times = [1.0, 1.1, 1.2, 10.0]  # 10.0이 이상치
        
        # When
        result = evaluation_statistics.calculate_response_time_stats(response_times)
        
        # Then
        assert result['average'] == 3.325  # (1.0 + 1.1 + 1.2 + 10.0) / 4
        assert result['median'] == 1.15   # (1.1 + 1.2) / 2
        assert result['min'] == 1.0
        assert result['max'] == 10.0

    @patch('platform.platform')
    @patch('platform.python_version')
    @patch('psutil.cpu_count')
    @patch('psutil.virtual_memory')
    def test_collect_environment_info_should_return_system_info_when_called(
        self, mock_virtual_memory, mock_cpu_count, mock_python_version, 
        mock_platform, evaluation_statistics
    ):
        """환경 정보 수집 시 시스템 정보를 반환해야 함"""
        # Given
        mock_platform.return_value = "macOS-11.0-arm64"
        mock_python_version.return_value = "3.11.8"
        mock_cpu_count.return_value = 8
        
        # 메모리 모킹 (8GB = 8 * 1024^3 bytes)
        mock_memory = Mock()
        mock_memory.total = 8 * (1024 ** 3)
        mock_virtual_memory.return_value = mock_memory
        
        # When
        result = evaluation_statistics.collect_environment_info()
        
        # Then
        assert result['platform'] == "macOS-11.0-arm64"
        assert result['python_version'] == "3.11.8"
        assert result['cpu_count'] == 8
        assert result['memory_gb'] == 8.0
        assert 'timestamp' in result

    def test_calculate_percentiles_should_return_correct_percentiles_when_valid_data(
        self, evaluation_statistics
    ):
        """유효한 데이터로 백분위수 계산 시 올바른 값을 반환해야 함"""
        # Given
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        percentiles = [25, 50, 75, 90, 95]
        
        # When
        result = evaluation_statistics.calculate_percentiles(data, percentiles)
        
        # Then
        assert result[25] == np.percentile(data, 25)
        assert result[50] == np.percentile(data, 50)  # median
        assert result[75] == np.percentile(data, 75)
        assert result[90] == np.percentile(data, 90)
        assert result[95] == np.percentile(data, 95)

    def test_calculate_percentiles_should_return_empty_when_empty_data(
        self, evaluation_statistics
    ):
        """빈 데이터로 백분위수 계산 시 빈 딕셔너리를 반환해야 함"""
        # Given
        data = []
        percentiles = [25, 50, 75, 95]
        
        # When
        result = evaluation_statistics.calculate_percentiles(data, percentiles)
        
        # Then
        assert result == {}

    def test_calculate_error_rate_should_return_correct_rate_when_has_errors(
        self, evaluation_statistics
    ):
        """에러가 있는 결과로 에러율 계산 시 올바른 비율을 반환해야 함"""
        # Given
        total_queries = 100
        failed_queries = 5
        
        # When
        result = evaluation_statistics.calculate_error_rate(failed_queries, total_queries)
        
        # Then
        assert result == 5.0  # 5%

    def test_calculate_error_rate_should_return_zero_when_no_errors(
        self, evaluation_statistics
    ):
        """에러가 없는 결과로 에러율 계산 시 0을 반환해야 함"""
        # Given
        total_queries = 100
        failed_queries = 0
        
        # When
        result = evaluation_statistics.calculate_error_rate(failed_queries, total_queries)
        
        # Then
        assert result == 0.0

    def test_calculate_error_rate_should_return_zero_when_no_queries(
        self, evaluation_statistics
    ):
        """총 쿼리가 0인 경우 에러율 계산 시 0을 반환해야 함"""
        # Given
        total_queries = 0
        failed_queries = 0
        
        # When
        result = evaluation_statistics.calculate_error_rate(failed_queries, total_queries)
        
        # Then
        assert result == 0.0

    def test_aggregate_metrics_should_return_summary_stats_when_valid_metrics(
        self, evaluation_statistics
    ):
        """유효한 메트릭으로 집계 시 요약 통계를 반환해야 함"""
        # Given
        metrics = {
            "recall": {"1": 0.6, "3": 0.7, "5": 0.8},
            "precision": {"1": 0.5, "3": 0.6, "5": 0.7},
            "ndcg": {"1": 0.55, "3": 0.65, "5": 0.75}
        }
        
        # When
        result = evaluation_statistics.aggregate_metrics(metrics)
        
        # Then
        assert 'recall' in result
        assert 'precision' in result
        assert 'ndcg' in result
        
        # Recall 통계 확인
        recall_stats = result['recall']
        assert abs(recall_stats['mean'] - 0.7) < 1e-10  # (0.6 + 0.7 + 0.8) / 3
        assert recall_stats['min'] == 0.6
        assert recall_stats['max'] == 0.8 