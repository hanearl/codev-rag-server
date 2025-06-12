import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from app.features.evaluation.service import evaluation_service
from app.features.evaluation.schema import (
    EvaluationRequest, SystemConfig, EvaluationOptions, EvaluationQuestion
)
from app.features.systems.interface import RetrievalResult
from app.features.metrics.manager import MetricsManager


class TestEvaluationService:
    """평가 서비스 테스트"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock 데이터베이스 세션"""
        session = MagicMock(spec=Session)
        session.query.return_value.filter.return_value.first.return_value = None
        session.add = MagicMock()
        session.flush = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        return session
    
    @pytest.fixture
    def mock_dataset_loader(self):
        """Mock 데이터셋 로더"""
        loader = AsyncMock()
        loader.load_questions.return_value = [
            EvaluationQuestion(
                difficulty="하",
                question="도서 관리 시스템에서 책을 추가하는 기능은?",
                answer=["com.example.BookController", "com.example.BookService"]
            ),
            EvaluationQuestion(
                difficulty="중",
                question="사용자 인증 처리는 어디서?",
                answer="com.example.AuthController"
            )
        ]
        loader.list_datasets.return_value = ["sample-dataset", "test-dataset"]
        loader.load_metadata.return_value = {
            "name": "sample-dataset",
            "description": "테스트 데이터셋",
            "format": "inline",
            "question_count": 2,
            "evaluation_options": EvaluationOptions(),
            "created_at": "2024-01-01T00:00:00Z",
            "version": "1.0"
        }
        return loader
    
    @pytest.fixture
    def mock_metrics_manager(self):
        """Mock 메트릭 매니저"""
        manager = MagicMock(spec=MetricsManager)
        manager.calculate_average_metrics.return_value = {
            "recall": {"1": 0.5, "3": 0.75, "5": 1.0},
            "precision": {"1": 1.0, "3": 0.67, "5": 0.4},
            "hit": {"1": 0.5, "3": 0.75, "5": 1.0},
            "mrr": {"1": 0.75, "3": 0.75, "5": 0.75},
            "ndcg": {"1": 0.5, "3": 0.65, "5": 0.8}
        }
        manager.get_metric_info.return_value = {
            "recall": {"name": "recall_at_k", "description": "Recall@K metric"},
            "precision": {"name": "precision_at_k", "description": "Precision@K metric"}
        }
        return manager
    
    @pytest.fixture
    def evaluation_service(self, mock_dataset_loader, mock_metrics_manager):
        """평가 서비스 인스턴스"""
        return EvaluationService(
            dataset_loader=mock_dataset_loader,
            metrics_manager=mock_metrics_manager
        )
    
    @pytest.fixture
    def sample_request(self):
        """샘플 평가 요청"""
        return EvaluationRequest(
            dataset_name="sample-dataset",
            system_config=SystemConfig(
                name="test-rag-system",
                base_url="http://localhost:8000",
                system_type="mock"
            ),
            k_values=[1, 3, 5],
            metrics=["recall", "precision"],
            save_results=False
        )
    
    @pytest.mark.asyncio
    async def test_evaluate_rag_system_success(self, sample_request, mock_db_session):
        """RAG 시스템 평가 성공 테스트"""
        # Given
        mock_questions = [
            EvaluationQuestion(difficulty="하", question="테스트 질문", answer=["com.example.Test"])
        ]
        mock_metadata = MagicMock()
        
        with patch.object(evaluation_service.dataset_loader, 'load_dataset') as mock_load:
            mock_load.return_value = (mock_questions, mock_metadata)
            
            with patch.object(evaluation_service, '_create_rag_system') as mock_create:
                mock_rag_system = AsyncMock()
                mock_rag_system.retrieve.return_value = [
                    RetrievalResult(content="test", score=0.9, filepath="com/example/Test.java")
                ]
                mock_rag_system.close = AsyncMock()
                mock_create.return_value = mock_rag_system
                
                # When
                result = await evaluation_service.evaluate_rag_system(sample_request, mock_db_session)
                
                # Then
                assert result.dataset_name == "sample-dataset"
                assert result.system_name == "test-rag-system"
                assert "recall" in result.metrics
                assert "precision" in result.metrics
                assert result.question_count == 1
    
    @pytest.mark.asyncio
    async def test_evaluate_with_classpath_conversion(self, mock_db_session):
        """클래스패스 변환을 포함한 평가 테스트"""
        # Given
        request = EvaluationRequest(
            dataset_name="sample-dataset",
            system_config=SystemConfig(
                name="test-rag-system",
                base_url="http://localhost:8000",
                system_type="mock"
            ),
            k_values=[1, 3],
            metrics=["recall"],
            options=EvaluationOptions(convert_filepath_to_classpath=True),
            save_results=False
        )
        
        mock_questions = [
            EvaluationQuestion(difficulty="하", question="테스트 질문", answer=["com.example.Test"])
        ]
        mock_metadata = MagicMock()
        
        with patch.object(evaluation_service.dataset_loader, 'load_dataset') as mock_load:
            mock_load.return_value = (mock_questions, mock_metadata)
            
            with patch.object(evaluation_service, '_create_rag_system') as mock_create:
                mock_rag_system = AsyncMock()
                mock_rag_system.retrieve.return_value = [
                    RetrievalResult(content="test", score=0.9, filepath="src/main/java/com/example/Test.java")
                ]
                mock_rag_system.close = AsyncMock()
                mock_create.return_value = mock_rag_system
                
                # When
                result = await evaluation_service.evaluate_rag_system(request, mock_db_session)
                
                # Then
                assert result.dataset_name == "sample-dataset"
                assert result.options.convert_filepath_to_classpath is True
    
    @pytest.mark.asyncio
    async def test_evaluate_with_save_results(self, mock_db_session):
        """결과 저장을 포함한 평가 테스트"""
        # Given
        request = EvaluationRequest(
            dataset_name="sample-dataset",
            system_config=SystemConfig(
                name="test-rag-system",
                base_url="http://localhost:8000",
                system_type="mock"
            ),
            k_values=[1],
            metrics=["recall"],
            save_results=True
        )
        
        mock_questions = [
            EvaluationQuestion(difficulty="하", question="테스트 질문", answer=["com.example.Test"])
        ]
        mock_metadata = MagicMock()
        
        with patch.object(evaluation_service.dataset_loader, 'load_dataset') as mock_load:
            mock_load.return_value = (mock_questions, mock_metadata)
            
            with patch.object(evaluation_service, '_create_rag_system') as mock_create:
                mock_rag_system = AsyncMock()
                mock_rag_system.retrieve.return_value = [
                    RetrievalResult(content="test", score=0.9, filepath="com/example/Test.java")
                ]
                mock_rag_system.close = AsyncMock()
                mock_create.return_value = mock_rag_system
                
                # When
                result = await evaluation_service.evaluate_rag_system(request, mock_db_session)
                
                # Then
                assert result is not None
                # 데이터베이스 저장이 시도되었는지 확인
                mock_db_session.add.assert_called()
    
    @pytest.mark.asyncio
    async def test_load_dataset_failure(self, sample_request, mock_db_session):
        """데이터셋 로드 실패 테스트"""
        # Given
        with patch.object(evaluation_service.dataset_loader, 'load_dataset') as mock_load:
            mock_load.side_effect = FileNotFoundError("Dataset not found")
            
            # When & Then
            with pytest.raises(FileNotFoundError):
                await evaluation_service.evaluate_rag_system(sample_request, mock_db_session)
    
    @pytest.mark.asyncio
    async def test_rag_system_initialization_failure(self, sample_request, mock_db_session):
        """RAG 시스템 초기화 실패 테스트"""
        # Given
        mock_questions = [
            EvaluationQuestion(difficulty="하", question="테스트 질문", answer=["com.example.Test"])
        ]
        mock_metadata = MagicMock()
        
        with patch.object(evaluation_service.dataset_loader, 'load_dataset') as mock_load:
            mock_load.return_value = (mock_questions, mock_metadata)
            
            with patch.object(evaluation_service, '_create_rag_system') as mock_create:
                mock_create.side_effect = Exception("RAG system initialization failed")
                
                # When & Then
                with pytest.raises(Exception, match="RAG system initialization failed"):
                    await evaluation_service.evaluate_rag_system(sample_request, mock_db_session)
    
    @pytest.mark.asyncio
    async def test_get_available_datasets(self):
        """사용 가능한 데이터셋 목록 조회 테스트"""
        # Given
        expected_datasets = ["sample-dataset", "test-dataset"]
        
        with patch.object(evaluation_service.dataset_loader, 'list_datasets') as mock_list:
            mock_list.return_value = expected_datasets
            
            # When
            datasets = await evaluation_service.get_available_datasets()
            
            # Then
            assert datasets == expected_datasets
    
    @pytest.mark.asyncio
    async def test_get_dataset_info(self):
        """데이터셋 정보 조회 테스트"""
        # Given
        mock_questions = [
            EvaluationQuestion(difficulty="하", question="테스트 질문", answer=["com.example.Test"])
        ]
        mock_metadata = MagicMock()
        mock_metadata.model_dump.return_value = {"name": "sample-dataset"}
        
        with patch.object(evaluation_service.dataset_loader, 'load_dataset') as mock_load:
            mock_load.return_value = (mock_questions, mock_metadata)
            
            # When
            info = await evaluation_service.get_dataset_info("sample-dataset")
            
            # Then
            assert info["name"] == "sample-dataset"
            assert info["question_count"] == 1
    
    def test_get_available_metrics(self):
        """사용 가능한 메트릭 정보 조회 테스트"""
        # When
        metrics_info = evaluation_service.get_available_metrics()
        
        # Then
        assert "recall" in metrics_info
        assert "precision" in metrics_info
        assert "hit" in metrics_info
        assert "mrr" in metrics_info
        assert "ndcg" in metrics_info
    
    @pytest.mark.asyncio
    async def test_test_classpath_conversion(self):
        """클래스패스 변환 테스트 기능 테스트"""
        # Given
        filepaths = [
            "src/main/java/com/example/BookController.java",
            "src/test/java/com/example/BookControllerTest.java"
        ]
        options = EvaluationOptions(
            convert_filepath_to_classpath=True,
            ignore_method_names=True
        )
        
        # When
        results = await evaluation_service.test_classpath_conversion(filepaths, options)
        
        # Then
        assert len(results) == 2
        assert "src/main/java/com/example/BookController.java" in results
        assert "src/test/java/com/example/BookControllerTest.java" in results
        
        # 클래스패스 변환 결과 확인
        for filepath, classpath in results.items():
            assert not classpath.startswith("Error:")  # 오류가 없어야 함
    
    def test_convert_predictions_to_classpaths(self):
        """예측 결과 클래스패스 변환 테스트"""
        # Given
        predictions = ["BookController", "BookService"]
        retrieval_results = [
            RetrievalResult(
                content="BookController",
                score=0.9,
                filepath="src/main/java/com/example/BookController.java"
            ),
            RetrievalResult(
                content="BookService",
                score=0.8,
                filepath="src/main/java/com/example/BookService.java"
            )
        ]
        options = EvaluationOptions(convert_filepath_to_classpath=True)
        
        # When
        converted = evaluation_service._convert_predictions_to_classpaths(
            predictions, retrieval_results, options
        )
        
        # Then
        assert len(converted) == 2
        assert "com.example.BookController" in converted
        assert "com.example.BookService" in converted
    
    def test_convert_ground_truth_to_classpaths(self):
        """정답 클래스패스 변환 테스트"""
        # Given
        ground_truth = ["com.example.BookController", "com.example.BookService"]
        options = EvaluationOptions(ignore_method_names=True)
        
        # When
        converted = evaluation_service._convert_ground_truth_to_classpaths(
            ground_truth, options
        )
        
        # Then
        assert len(converted) == 2
        assert "com.example.BookController" in converted
        assert "com.example.BookService" in converted 