import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.features.systems.model import RAGSystem
from app.features.evaluations.model import EvaluationResult, EvaluationTask


@pytest.fixture
def db_session():
    """테스트용 데이터베이스 세션"""
    # 인메모리 SQLite 데이터베이스 사용
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.close()


class TestRAGSystemModel:
    """RAG 시스템 모델 테스트"""
    
    def test_create_rag_system(self, db_session):
        """RAG 시스템 생성 테스트"""
        # Given
        system_data = {
            "name": "Test RAG System",
            "description": "테스트용 RAG 시스템",
            "base_url": "http://localhost:8001",
            "system_type": "external",
            "config": {"timeout": 30, "max_retries": 3}
        }
        
        # When
        system = RAGSystem(**system_data)
        db_session.add(system)
        db_session.commit()
        db_session.refresh(system)
        
        # Then
        assert system.id is not None
        assert system.name == "Test RAG System"
        assert system.base_url == "http://localhost:8001"
        assert system.system_type == "external"
        assert system.is_active is True
        assert system.created_at is not None
        assert system.config["timeout"] == 30
    
    def test_rag_system_with_api_key(self, db_session):
        """API 키가 있는 RAG 시스템 테스트"""
        # Given
        system = RAGSystem(
            name="Secure RAG System",
            base_url="https://api.example.com",
            api_key="secret-key-123",
            system_type="external"
        )
        
        # When
        db_session.add(system)
        db_session.commit()
        db_session.refresh(system)
        
        # Then
        assert system.api_key == "secret-key-123"
        assert system.name == "Secure RAG System"
    
    def test_rag_system_default_values(self, db_session):
        """RAG 시스템 기본값 테스트"""
        # Given
        system = RAGSystem(
            name="Minimal System",
            base_url="http://localhost:8000"
        )
        
        # When
        db_session.add(system)
        db_session.commit()
        db_session.refresh(system)
        
        # Then
        assert system.system_type == "external"  # 기본값
        assert system.is_active is True  # 기본값
        assert system.config == {}  # 기본값
        assert system.api_key is None


class TestEvaluationResultModel:
    """평가 결과 모델 테스트"""
    
    def test_create_evaluation_result(self, db_session):
        """평가 결과 생성 테스트"""
        # Given - RAG 시스템 먼저 생성
        system = RAGSystem(
            name="Test System",
            base_url="http://localhost:8001"
        )
        db_session.add(system)
        db_session.commit()
        db_session.refresh(system)
        
        # Given - 평가 결과 데이터
        result_data = {
            "system_id": system.id,
            "dataset_id": "sample-dataset",
            "metrics": {
                "recall_at_k": {"1": 0.3, "3": 0.6, "5": 0.8},
                "precision_at_k": {"1": 0.3, "3": 0.2, "5": 0.16},
                "hit_at_k": {"1": 0.3, "3": 0.6, "5": 0.8},
                "mrr": 0.52
            },
            "execution_time": 45.2,
            "config": {"k_values": [1, 3, 5], "metrics": ["recall", "precision", "hit"]}
        }
        
        # When
        result = EvaluationResult(**result_data)
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)
        
        # Then
        assert result.id is not None
        assert result.system_id == system.id
        assert result.dataset_id == "sample-dataset"
        assert result.metrics["recall_at_k"]["1"] == 0.3
        assert result.execution_time == 45.2
        assert result.status == "completed"  # 기본값
        assert result.created_at is not None
    
    def test_evaluation_result_relationship(self, db_session):
        """평가 결과와 RAG 시스템 관계 테스트"""
        # Given
        system = RAGSystem(name="Test System", base_url="http://localhost:8001")
        db_session.add(system)
        db_session.commit()
        db_session.refresh(system)
        
        result = EvaluationResult(
            system_id=system.id,
            dataset_id="test-dataset",
            metrics={"hit_at_k": {"1": 0.5}},
            execution_time=10.0
        )
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)
        
        # When
        retrieved_result = db_session.query(EvaluationResult).filter_by(id=result.id).first()
        
        # Then
        assert retrieved_result.system is not None
        assert retrieved_result.system.name == "Test System"
        assert retrieved_result.system.id == system.id
    
    def test_evaluation_result_with_error(self, db_session):
        """오류가 있는 평가 결과 테스트"""
        # Given
        system = RAGSystem(name="Test System", base_url="http://localhost:8001")
        db_session.add(system)
        db_session.commit()
        db_session.refresh(system)
        
        result = EvaluationResult(
            system_id=system.id,
            dataset_id="test-dataset",
            metrics={},
            execution_time=0.0,
            status="failed",
            error_message="Connection timeout"
        )
        
        # When
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)
        
        # Then
        assert result.status == "failed"
        assert result.error_message == "Connection timeout"


class TestEvaluationTaskModel:
    """평가 작업 모델 테스트"""
    
    def test_create_evaluation_task(self, db_session):
        """평가 작업 생성 테스트"""
        # Given
        system = RAGSystem(name="Test System", base_url="http://localhost:8001")
        db_session.add(system)
        db_session.commit()
        db_session.refresh(system)
        
        task_data = {
            "task_id": "celery-task-123",
            "system_id": system.id,
            "dataset_id": "sample-dataset",
            "status": "running",
            "progress": 0.5
        }
        
        # When
        task = EvaluationTask(**task_data)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        # Then
        assert task.id is not None
        assert task.task_id == "celery-task-123"
        assert task.system_id == system.id
        assert task.dataset_id == "sample-dataset"
        assert task.status == "running"
        assert task.progress == 0.5
        assert task.created_at is not None
    
    def test_evaluation_task_default_values(self, db_session):
        """평가 작업 기본값 테스트"""
        # Given
        system = RAGSystem(name="Test System", base_url="http://localhost:8001")
        db_session.add(system)
        db_session.commit()
        db_session.refresh(system)
        
        task = EvaluationTask(
            task_id="task-456",
            system_id=system.id,
            dataset_id="test-dataset"
        )
        
        # When
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        # Then
        assert task.status == "pending"  # 기본값
        assert task.progress == 0.0  # 기본값
        assert task.result_id is None  # 기본값 