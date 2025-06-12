import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from app.main import app
from app.features.evaluation.schema import (
    EvaluationRequest, SystemConfig, EvaluationOptions, EvaluationResponse
)


class TestEvaluationRouter:
    """평가 라우터 테스트"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock 데이터베이스 세션"""
        session = MagicMock(spec=Session)
        return session
    
    def test_health_check(self, client):
        """헬스체크 엔드포인트 테스트"""
        with patch('app.features.evaluation.service.evaluation_service') as mock_service:
            mock_service.get_available_metrics.return_value = {
                "recall": {"name": "recall_at_k", "description": "Recall@K metric"}
            }
            mock_service.get_available_datasets.return_value = ["sample-dataset"]
            
            response = client.get("/api/v1/evaluation/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "evaluation-server"
            assert "features" in data
            assert "metrics" in data["features"]
            assert "datasets" in data["features"]
    
    def test_detailed_health_check(self, client):
        """상세 헬스체크 엔드포인트 테스트"""
        with patch('app.features.evaluation.service.evaluation_service') as mock_service:
            mock_service.get_available_datasets.return_value = ["sample-dataset", "test-dataset"]
            mock_service.get_available_metrics.return_value = {
                "recall": {"name": "recall_at_k", "description": "Recall@K metric"},
                "precision": {"name": "precision_at_k", "description": "Precision@K metric"}
            }
            
            response = client.get("/api/v1/evaluation/health/detailed")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "evaluation-server"
            assert data["version"] == "1.0.0"
            assert "components" in data
            assert data["components"]["dataset_loader"]["available_datasets"] == 1
            assert data["components"]["metrics_manager"]["available_metrics"] == 5
    
    def test_detailed_health_check_failure(self, client):
        """상세 헬스체크 실패 테스트"""
        with patch('app.features.evaluation.service.evaluation_service.get_available_datasets') as mock_datasets:
            mock_datasets.side_effect = Exception("Service error")
            
            response = client.get("/api/v1/evaluation/health/detailed")
            
            assert response.status_code == 503
            data = response.json()
            assert "Service unhealthy" in data["detail"]
    
    def test_list_datasets(self, client):
        """데이터셋 목록 조회 테스트"""
        response = client.get("/api/v1/evaluation/datasets")
        
        assert response.status_code == 200
        data = response.json()
        assert data["datasets"] == ["sample-dataset"]
    
    def test_list_datasets_failure(self, client):
        """데이터셋 목록 조회 실패 테스트"""
        with patch('app.features.evaluation.service.evaluation_service.get_available_datasets') as mock_datasets:
            mock_datasets.side_effect = Exception("Database error")
            
            response = client.get("/api/v1/evaluation/datasets")
            
            assert response.status_code == 500
            data = response.json()
            assert "데이터셋 목록 조회 실패" in data["detail"]
    
    def test_get_dataset_info(self, client):
        """데이터셋 정보 조회 테스트"""
        with patch('app.features.evaluation.service.evaluation_service') as mock_service:
            mock_service.get_dataset_info.return_value = {
                "name": "sample-dataset",
                "metadata": {
                    "name": "sample-dataset",
                    "description": "테스트 데이터셋",
                    "format": "inline",
                    "question_count": 10,
                    "evaluation_options": {
                        "convert_filepath_to_classpath": True,
                        "ignore_method_names": True,
                        "case_sensitive": False,
                        "java_source_root": "src/main/java",
                        "java_test_root": "src/test/java"
                    },
                    "created_at": "2024-01-01T00:00:00Z",
                    "version": "1.0"
                },
                "question_count": 10,
                "sample_questions": []
            }
            
            response = client.get("/api/v1/evaluation/datasets/sample-dataset")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "sample-dataset"
            assert data["question_count"] == 10
            assert "metadata" in data
    
    def test_get_dataset_info_not_found(self, client):
        """존재하지 않는 데이터셋 조회 테스트"""
        with patch('app.features.evaluation.service.evaluation_service') as mock_service:
            mock_service.get_dataset_info.side_effect = FileNotFoundError("Dataset not found")
            
            response = client.get("/api/v1/evaluation/datasets/nonexistent")
            
            assert response.status_code == 404
            data = response.json()
            assert "데이터셋 'nonexistent'을 찾을 수 없습니다" in data["detail"]
    
    def test_get_metrics_info(self, client):
        """메트릭 정보 조회 테스트"""
        response = client.get("/api/v1/evaluation/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert len(data["metrics"]) == 5  # recall, precision, hit, mrr, ndcg
        assert "recall" in data["metrics"]
        assert "precision" in data["metrics"]
        assert "hit" in data["metrics"]
        assert "mrr" in data["metrics"]
        assert "ndcg" in data["metrics"]
    
    def test_evaluate_rag_system_success(self, client):
        """RAG 시스템 평가 성공 테스트"""
        request_data = {
            "dataset_name": "sample-dataset",
            "system_config": {
                "name": "test-rag-system",
                "base_url": "http://localhost:8000",
                "system_type": "mock"
            },
            "k_values": [1, 3, 5],
            "metrics": ["recall", "precision", "hit"],
            "options": {
                "convert_filepath_to_classpath": True,
                "ignore_method_names": True,
                "case_sensitive": False,
                "java_source_root": "src/main/java",
                "java_test_root": "src/test/java"
            },
            "save_results": False
        }
        
        mock_response = EvaluationResponse(
            dataset_name="sample-dataset",
            system_name="test-rag-system",
            metrics={
                "recall": {"1": 0.5, "3": 0.75, "5": 1.0},
                "precision": {"1": 1.0, "3": 0.67, "5": 0.4},
                "hit": {"1": 0.5, "3": 0.75, "5": 1.0}
            },
            execution_time=1.5,
            question_count=10,
            k_values=[1, 3, 5],
            options=EvaluationOptions(**request_data["options"])
        )
        
        with patch('app.features.evaluation.service.evaluation_service.evaluate_rag_system') as mock_evaluate:
            mock_evaluate.return_value = mock_response
            
            with patch('app.db.database.get_db') as mock_get_db:
                mock_get_db.return_value = MagicMock()
                
                response = client.post("/api/v1/evaluation/evaluate", json=request_data)
                
                assert response.status_code == 200
                data = response.json()
                assert data["dataset_name"] == "sample-dataset"
                assert data["system_name"] == "test-rag-system"
                assert data["question_count"] == 10
                assert "metrics" in data
                assert "recall" in data["metrics"]
    
    def test_evaluate_rag_system_invalid_k_values(self, client):
        """잘못된 k_values로 평가 요청 테스트"""
        request_data = {
            "dataset_name": "sample-dataset",
            "system_config": {
                "name": "test-rag-system",
                "base_url": "http://localhost:8000"
            },
            "k_values": [],  # 빈 리스트
            "metrics": ["recall"]
        }
        
        response = client.post("/api/v1/evaluation/evaluate", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "k_values는 비어있을 수 없습니다" in data["detail"]
    
    def test_evaluate_rag_system_negative_k_values(self, client):
        """음수 k_values로 평가 요청 테스트"""
        request_data = {
            "dataset_name": "sample-dataset",
            "system_config": {
                "name": "test-rag-system",
                "base_url": "http://localhost:8000"
            },
            "k_values": [1, -3, 5],  # 음수 포함
            "metrics": ["recall"]
        }
        
        response = client.post("/api/v1/evaluation/evaluate", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "k_values는 모두 양수여야 합니다" in data["detail"]
    
    def test_evaluate_rag_system_no_metrics(self, client):
        """메트릭이 없는 평가 요청 테스트"""
        request_data = {
            "dataset_name": "sample-dataset",
            "system_config": {
                "name": "test-rag-system",
                "base_url": "http://localhost:8000"
            },
            "k_values": [1, 3, 5],
            "metrics": []  # 빈 리스트
        }
        
        response = client.post("/api/v1/evaluation/evaluate", json=request_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "최소 하나의 메트릭을 선택해야 합니다" in data["detail"]
    
    def test_evaluate_rag_system_invalid_metrics(self, client):
        """유효하지 않은 메트릭으로 평가 요청 테스트"""
        request_data = {
            "dataset_name": "sample-dataset",
            "system_config": {
                "name": "test-rag-system",
                "base_url": "http://localhost:8000"
            },
            "k_values": [1, 3, 5],
            "metrics": ["recall", "invalid_metric"]
        }
        
        with patch('app.features.evaluation.service.evaluation_service') as mock_service:
            mock_service.get_available_metrics.return_value = {
                "recall": {"name": "recall_at_k"},
                "precision": {"name": "precision_at_k"}
            }
            
            response = client.post("/api/v1/evaluation/evaluate", json=request_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "유효하지 않은 메트릭" in data["detail"]
            assert "invalid_metric" in data["detail"]
    
    def test_evaluate_rag_system_dataset_not_found(self, client):
        """존재하지 않는 데이터셋으로 평가 요청 테스트"""
        request_data = {
            "dataset_name": "nonexistent-dataset",
            "system_config": {
                "name": "test-rag-system",
                "base_url": "http://localhost:8000"
            },
            "k_values": [1, 3, 5],
            "metrics": ["recall"]
        }
        
        with patch('app.features.evaluation.service.evaluation_service') as mock_service:
            mock_service.get_available_metrics.return_value = {
                "recall": {"name": "recall_at_k"}
            }
            mock_service.evaluate_rag_system.side_effect = FileNotFoundError("Dataset not found")
            
            with patch('app.db.database.get_db') as mock_get_db:
                mock_get_db.return_value = MagicMock()
                
                response = client.post("/api/v1/evaluation/evaluate", json=request_data)
                
                assert response.status_code == 404
                data = response.json()
                assert "데이터셋을 찾을 수 없습니다" in data["detail"]
    
    def test_test_classpath_conversion(self, client):
        """클래스패스 변환 테스트 엔드포인트 테스트"""
        request_data = {
            "filepaths": [
                "src/main/java/com/example/BookController.java",
                "src/test/java/com/example/BookControllerTest.java"
            ],
            "options": {
                "convert_filepath_to_classpath": True,
                "ignore_method_names": True,
                "case_sensitive": False,
                "java_source_root": "src/main/java",
                "java_test_root": "src/test/java"
            }
        }
        
        mock_results = {
            "src/main/java/com/example/BookController.java": "com.example.BookController",
            "src/test/java/com/example/BookControllerTest.java": "com.example.BookControllerTest"
        }
        
        with patch('app.features.evaluation.service.evaluation_service') as mock_service:
            mock_service.test_classpath_conversion.return_value = mock_results
            
            response = client.post("/api/v1/evaluation/test-classpath-conversion", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert len(data["results"]) == 2
            assert "com.example.BookController" in data["results"].values()
    
    def test_test_classpath_conversion_failure(self, client):
        """클래스패스 변환 테스트 실패 테스트"""
        request_data = {
            "filepaths": ["invalid/path.java"],
            "options": {
                "convert_filepath_to_classpath": True,
                "ignore_method_names": True,
                "case_sensitive": False,
                "java_source_root": "src/main/java",
                "java_test_root": "src/test/java"
            }
        }
        
        with patch('app.features.evaluation.service.evaluation_service.test_classpath_conversion') as mock_convert:
            mock_convert.side_effect = Exception("Conversion error")
            
            response = client.post("/api/v1/evaluation/test-classpath-conversion", json=request_data)
            
            assert response.status_code == 500
            data = response.json()
            assert "클래스패스 변환 테스트 실패" in data["detail"] 