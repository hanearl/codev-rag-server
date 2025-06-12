import pytest
import asyncio
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import Base, get_db

# 테스트용 데이터베이스 URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# 테스트용 엔진 생성
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# 테스트용 세션 팩토리
TestingSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)


@pytest.fixture(scope="session")
def event_loop():
    """세션 레벨 이벤트 루프"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def db_session():
    """테스트용 데이터베이스 세션"""
    # 테이블 생성
    Base.metadata.create_all(bind=engine)
    
    # 세션 생성
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # 테이블 삭제
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """테스트용 FastAPI 클라이언트"""
    
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    # 의존성 오버라이드
    app.dependency_overrides[get_db] = override_get_db
    
    # 테스트 클라이언트 생성
    with TestClient(app) as test_client:
        yield test_client
    
    # 의존성 오버라이드 제거
    app.dependency_overrides.clear()


@pytest.fixture
def sample_dataset_path():
    """샘플 데이터셋 경로"""
    return "./datasets/sample-dataset"


@pytest.fixture
def mock_rag_system_config():
    """Mock RAG 시스템 설정"""
    return {
        "name": "Test RAG System",
        "description": "테스트용 RAG 시스템",
        "base_url": "http://localhost:8001",
        "system_type": "mock",
        "config": {}
    }


@pytest.fixture
def sample_evaluation_config():
    """샘플 평가 설정"""
    return {
        "k_values": [1, 3, 5],
        "metrics": ["recall", "precision", "hit"]
    }


@pytest.fixture
def sample_queries():
    """샘플 쿼리 데이터"""
    return [
        {"query_id": "q001", "query": "Python 리스트 정렬"},
        {"query_id": "q002", "query": "FastAPI 사용법"},
        {"query_id": "q003", "query": "머신러닝 평가"}
    ]


@pytest.fixture
def sample_ground_truth():
    """샘플 정답 데이터"""
    return {
        "q001": ["doc_py_001", "doc_py_002"],
        "q002": ["doc_api_001", "doc_api_003"],
        "q003": ["doc_ml_001", "doc_ml_005"]
    }


@pytest.fixture
def sample_retrieval_results():
    """샘플 검색 결과"""
    return {
        "q001": [
            {"doc_id": "doc_py_001", "score": 0.95},
            {"doc_id": "doc_py_003", "score": 0.85},
            {"doc_id": "doc_py_002", "score": 0.80},
            {"doc_id": "doc_py_004", "score": 0.70},
            {"doc_id": "doc_py_005", "score": 0.60}
        ],
        "q002": [
            {"doc_id": "doc_api_001", "score": 0.90},
            {"doc_id": "doc_api_002", "score": 0.85},
            {"doc_id": "doc_api_003", "score": 0.75},
            {"doc_id": "doc_api_004", "score": 0.65},
            {"doc_id": "doc_api_005", "score": 0.55}
        ]
    } 