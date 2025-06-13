import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session
from app.features.baselines.service import BaselineService
from app.features.baselines.repository import BaselineRepository
from app.features.baselines.model import Baseline
from app.features.evaluations.model import EvaluationResult
from app.features.evaluation.schema import BaselineComparison


class TestBaselineService:
    """베이스라인 서비스 테스트"""
    
    @pytest.fixture
    def mock_repository(self):
        """베이스라인 저장소 모킹"""
        return Mock(spec=BaselineRepository)
    
    @pytest.fixture
    def baseline_service(self, mock_repository):
        """베이스라인 서비스 인스턴스"""
        return BaselineService(mock_repository)
    
    @pytest.fixture
    def mock_db(self):
        """데이터베이스 세션 모킹"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_evaluation_result(self):
        """샘플 평가 결과"""
        return EvaluationResult(
            id=1,
            system_id=1,
            dataset_id="test-dataset",
            metrics={
                "recall": {"1": 0.6, "3": 0.7, "5": 0.8},
                "precision": {"1": 0.5, "3": 0.6, "5": 0.7},
                "ndcg": {"1": 0.55, "3": 0.65, "5": 0.75}
            },
            execution_time=5.2,
            config={"k_values": [1, 3, 5]},
            status="completed"
        )
    
    @pytest.fixture
    def sample_baseline(self, sample_evaluation_result):
        """샘플 베이스라인"""
        return Baseline(
            id=1,
            name="baseline-v1",
            description="첫 번째 베이스라인",
            dataset_id="test-dataset",
            evaluation_result_id=1,
            evaluation_result=sample_evaluation_result,
            is_active=True
        )

    @pytest.mark.asyncio
    async def test_register_baseline_should_create_baseline_when_valid_evaluation_result(
        self, baseline_service, mock_db, mock_repository, sample_evaluation_result
    ):
        """유효한 평가 결과로 베이스라인 등록 시 베이스라인이 생성되어야 함"""
        # Given
        name = "baseline-v1"
        description = "첫 번째 베이스라인"
        evaluation_result_id = 1
        
        # DB 쿼리 모킹
        mock_db.query.return_value.filter.return_value.first.return_value = sample_evaluation_result
        
        # 중복 베이스라인 검사 모킹 (없음으로 설정)
        mock_repository.get_by_name_and_dataset.return_value = None
        
        # Repository 모킹
        expected_baseline = Baseline(
            id=1,
            name=name,
            description=description,
            dataset_id=sample_evaluation_result.dataset_id,
            evaluation_result_id=evaluation_result_id
        )
        mock_repository.create.return_value = expected_baseline
        
        # When
        result = await baseline_service.register_baseline(
            mock_db, name, description, evaluation_result_id
        )
        
        # Then
        assert result == expected_baseline
        mock_repository.create.assert_called_once()
        created_data = mock_repository.create.call_args[1]['obj_in']
        assert created_data['name'] == name
        assert created_data['description'] == description
        assert created_data['dataset_id'] == sample_evaluation_result.dataset_id
        assert created_data['evaluation_result_id'] == evaluation_result_id

    @pytest.mark.asyncio
    async def test_register_baseline_should_raise_error_when_evaluation_result_not_found(
        self, baseline_service, mock_db
    ):
        """존재하지 않는 평가 결과로 베이스라인 등록 시 에러가 발생해야 함"""
        # Given
        evaluation_result_id = 999
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # When & Then
        with pytest.raises(ValueError, match="Evaluation result not found: 999"):
            await baseline_service.register_baseline(
                mock_db, "test", "test", evaluation_result_id
            )

    @pytest.mark.asyncio
    async def test_compare_with_baseline_should_return_comparison_when_valid_baseline(
        self, baseline_service, mock_db, mock_repository, sample_baseline
    ):
        """유효한 베이스라인과 비교 시 비교 결과를 반환해야 함"""
        # Given
        baseline_id = 1
        current_result = EvaluationResult(
            id=2,
            system_id=1,
            dataset_id="test-dataset",
            metrics={
                "recall": {"1": 0.7, "3": 0.8, "5": 0.9},  # 개선됨
                "precision": {"1": 0.4, "3": 0.5, "5": 0.6},  # 악화됨
                "ndcg": {"1": 0.6, "3": 0.7, "5": 0.8}  # 개선됨
            },
            execution_time=4.8,
            config={"k_values": [1, 3, 5]},
            status="completed"
        )
        
        mock_repository.get.return_value = sample_baseline
        
        # When
        result = await baseline_service.compare_with_baseline(
            mock_db, baseline_id, current_result
        )
        
        # Then
        assert isinstance(result, BaselineComparison)
        assert result.baseline_id == str(baseline_id)
        assert result.current_result_id == str(current_result.id)
        
        # 메트릭 개선도 확인
        assert "recall" in result.metric_improvements
        assert "precision" in result.metric_improvements
        assert "ndcg" in result.metric_improvements
        
        # Recall은 개선되어야 함 (0.6 -> 0.7 = 16.67% 개선)
        recall_improvement_k1 = result.metric_improvements["recall"]["1"]
        assert recall_improvement_k1 > 0
        
        # Precision은 악화되어야 함 (0.5 -> 0.4 = -20% 악화)
        precision_improvement_k1 = result.metric_improvements["precision"]["1"]
        assert precision_improvement_k1 < 0

    @pytest.mark.asyncio
    async def test_compare_with_baseline_should_raise_error_when_baseline_not_found(
        self, baseline_service, mock_db, mock_repository
    ):
        """존재하지 않는 베이스라인과 비교 시 에러가 발생해야 함"""
        # Given
        baseline_id = 999
        current_result = Mock()
        mock_repository.get.return_value = None
        
        # When & Then
        with pytest.raises(ValueError, match="Baseline not found: 999"):
            await baseline_service.compare_with_baseline(
                mock_db, baseline_id, current_result
            )

    def test_is_overall_better_should_return_true_when_more_improvements(
        self, baseline_service
    ):
        """개선된 메트릭이 더 많을 때 True를 반환해야 함"""
        # Given
        improvements = {
            "recall": {"1": 10.0, "3": 5.0},    # 개선
            "precision": {"1": -2.0, "3": -1.0}, # 악화
            "ndcg": {"1": 8.0, "3": 12.0}       # 개선
        }
        
        # When
        result = baseline_service._is_overall_better(improvements)
        
        # Then
        assert result is True  # 전체 합이 양수이므로 개선됨

    def test_is_overall_better_should_return_false_when_more_degradations(
        self, baseline_service
    ):
        """악화된 메트릭이 더 많을 때 False를 반환해야 함"""
        # Given
        improvements = {
            "recall": {"1": 2.0, "3": 1.0},      # 소폭 개선
            "precision": {"1": -10.0, "3": -8.0}, # 큰 악화
            "ndcg": {"1": -5.0, "3": -3.0}       # 악화
        }
        
        # When
        result = baseline_service._is_overall_better(improvements)
        
        # Then
        assert result is False  # 전체 합이 음수이므로 악화됨 