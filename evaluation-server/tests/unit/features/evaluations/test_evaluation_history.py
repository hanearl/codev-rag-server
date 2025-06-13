import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime
from app.features.evaluations.service import EvaluationHistoryService
from app.features.evaluations.repository import EvaluationResultRepository
from app.features.evaluations.model import EvaluationResult
from app.features.systems.model import RAGSystem


class TestEvaluationHistoryService:
    """평가 결과 히스토리 서비스 테스트"""
    
    @pytest.fixture
    def mock_repository(self):
        """평가 결과 저장소 모킹"""
        return Mock(spec=EvaluationResultRepository)
    
    @pytest.fixture
    def history_service(self, mock_repository):
        """히스토리 서비스 인스턴스"""
        return EvaluationHistoryService(mock_repository)
    
    @pytest.fixture
    def mock_db(self):
        """데이터베이스 세션 모킹"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_evaluation_results(self):
        """샘플 평가 결과 데이터"""
        system = RAGSystem(id=1, name="test-system", base_url="http://test.com")
        
        results = [
            EvaluationResult(
                id=1,
                system_id=1,
                dataset_id="test-dataset",
                metrics={"precision": {"5": 0.8, "10": 0.7}},
                execution_time=10.5,
                created_at=datetime(2024, 1, 1, 10, 0, 0),
                status="completed",
                system=system
            ),
            EvaluationResult(
                id=2,
                system_id=1,
                dataset_id="test-dataset",
                metrics={"precision": {"5": 0.85, "10": 0.75}},
                execution_time=12.3,
                created_at=datetime(2024, 1, 2, 10, 0, 0),
                status="completed",
                system=system
            )
        ]
        return results

    def test_get_evaluation_history_should_return_results_when_valid_filters(
        self, history_service, mock_db, mock_repository, sample_evaluation_results
    ):
        """유효한 필터로 평가 히스토리 조회 시 결과를 반환해야 함"""
        # Given
        dataset_id = "test-dataset"
        system_name = "test-system"
        limit = 10
        
        mock_repository.get_by_filters.return_value = sample_evaluation_results
        
        # When
        result = history_service.get_evaluation_history(
            mock_db, dataset_id=dataset_id, system_name=system_name, limit=limit
        )
        
        # Then
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].dataset_id == "test-dataset"
        assert result[1].id == 2
        mock_repository.get_by_filters.assert_called_once_with(
            db=mock_db, dataset_id=dataset_id, system_name=system_name, status=None, limit=limit, offset=0
        )

    def test_get_evaluation_history_should_return_empty_when_no_results(
        self, history_service, mock_db, mock_repository
    ):
        """결과가 없을 때 빈 리스트를 반환해야 함"""
        # Given
        mock_repository.get_by_filters.return_value = []
        
        # When
        result = history_service.get_evaluation_history(mock_db)
        
        # Then
        assert result == []
        mock_repository.get_by_filters.assert_called_once()

    def test_get_evaluation_by_id_should_return_result_when_exists(
        self, history_service, mock_db, mock_repository, sample_evaluation_results
    ):
        """ID로 평가 결과 조회 시 존재하면 결과를 반환해야 함"""
        # Given
        evaluation_id = 1
        expected_result = sample_evaluation_results[0]
        mock_repository.get.return_value = expected_result
        
        # When
        result = history_service.get_evaluation_by_id(mock_db, evaluation_id)
        
        # Then
        assert result == expected_result
        assert result.id == 1
        mock_repository.get.assert_called_once_with(mock_db, evaluation_id)

    def test_get_evaluation_by_id_should_return_none_when_not_exists(
        self, history_service, mock_db, mock_repository
    ):
        """ID로 평가 결과 조회 시 존재하지 않으면 None을 반환해야 함"""
        # Given
        evaluation_id = 999
        mock_repository.get.return_value = None
        
        # When
        result = history_service.get_evaluation_by_id(mock_db, evaluation_id)
        
        # Then
        assert result is None
        mock_repository.get.assert_called_once_with(mock_db, evaluation_id)

    def test_get_latest_evaluation_should_return_most_recent_when_exists(
        self, history_service, mock_db, mock_repository, sample_evaluation_results
    ):
        """최신 평가 결과 조회 시 가장 최근 결과를 반환해야 함"""
        # Given
        dataset_id = "test-dataset"
        system_name = "test-system"
        latest_result = sample_evaluation_results[1]  # 더 최근 날짜
        mock_repository.get_latest.return_value = latest_result
        
        # When
        result = history_service.get_latest_evaluation(
            mock_db, dataset_id=dataset_id, system_name=system_name
        )
        
        # Then
        assert result == latest_result
        assert result.id == 2
        mock_repository.get_latest.assert_called_once_with(
            db=mock_db, dataset_id=dataset_id, system_name=system_name
        )

    def test_get_evaluation_count_should_return_correct_count_when_has_results(
        self, history_service, mock_db, mock_repository
    ):
        """평가 결과 수 조회 시 올바른 수를 반환해야 함"""
        # Given
        expected_count = 5
        mock_repository.count_by_filters.return_value = expected_count
        
        # When
        result = history_service.get_evaluation_count(mock_db, dataset_id="test-dataset")
        
        # Then
        assert result == expected_count
        mock_repository.count_by_filters.assert_called_once_with(
            db=mock_db, dataset_id="test-dataset", system_name=None, status=None
        )

    def test_delete_evaluation_should_remove_result_when_exists(
        self, history_service, mock_db, mock_repository, sample_evaluation_results
    ):
        """평가 결과 삭제 시 존재하면 삭제해야 함"""
        # Given
        evaluation_id = 1
        existing_result = sample_evaluation_results[0]
        mock_repository.get.return_value = existing_result
        mock_repository.remove.return_value = existing_result
        
        # When
        result = history_service.delete_evaluation(mock_db, evaluation_id)
        
        # Then
        assert result == existing_result
        mock_repository.get.assert_called_once_with(mock_db, evaluation_id)
        mock_repository.remove.assert_called_once_with(mock_db, id=evaluation_id)

    def test_delete_evaluation_should_return_none_when_not_exists(
        self, history_service, mock_db, mock_repository
    ):
        """평가 결과 삭제 시 존재하지 않으면 None을 반환해야 함"""
        # Given
        evaluation_id = 999
        mock_repository.get.return_value = None
        
        # When
        result = history_service.delete_evaluation(mock_db, evaluation_id)
        
        # Then
        assert result is None
        mock_repository.get.assert_called_once_with(mock_db, evaluation_id)
        mock_repository.remove.assert_not_called()

    def test_get_system_performance_summary_should_return_summary_when_has_data(
        self, history_service, mock_db, mock_repository, sample_evaluation_results
    ):
        """시스템 성능 요약 조회 시 데이터가 있으면 요약을 반환해야 함"""
        # Given
        system_name = "test-system"
        mock_repository.get_by_filters.return_value = sample_evaluation_results
        
        # When
        result = history_service.get_system_performance_summary(mock_db, system_name)
        
        # Then
        assert "total_evaluations" in result
        assert "datasets" in result
        assert "average_execution_time" in result
        assert "latest_evaluation" in result
        assert result["total_evaluations"] == 2
        assert result["average_execution_time"] == 11.4  # (10.5 + 12.3) / 2 