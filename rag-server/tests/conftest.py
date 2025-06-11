import pytest
import subprocess
import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import Base, get_db

# 테스트 데이터베이스 설정
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    """테스트용 데이터베이스 세션"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    """테스트용 FastAPI 클라이언트"""
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]

@pytest.fixture
def sample_user_data():
    """테스트용 샘플 사용자 데이터"""
    return {
        "name": "테스트 사용자",
        "email": "test@example.com"
    }

@pytest.fixture
def db_session():
    """테스트용 데이터베이스 세션"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="session")
def docker_services():
    """Docker Compose 서비스 관리 (선택적)"""
    # 실제 Docker 서비스를 시작하려면 주석 해제
    # subprocess.run(["docker-compose", "up", "-d"], check=True)
    # time.sleep(10)  # 서비스가 준비될 때까지 대기
    
    yield
    
    # 테스트 완료 후 서비스 정리
    # subprocess.run(["docker-compose", "down"], check=True) 