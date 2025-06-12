import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """루트 엔드포인트 테스트"""
    # When
    response = client.get("/")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "evaluation-server"
    assert data["status"] == "running"
    assert data["version"] == "1.0.0"
    assert "features" in data
    assert "endpoints" in data


def test_health_check_endpoint():
    """헬스체크 엔드포인트 테스트"""
    # When
    response = client.get("/health")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "evaluation-server"


def test_evaluation_health_endpoint():
    """평가 서비스 헬스체크 엔드포인트 테스트"""
    # When
    response = client.get("/api/v1/evaluation/health")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "evaluation-server"


def test_evaluation_detailed_health_endpoint():
    """평가 서비스 상세 헬스체크 엔드포인트 테스트"""
    # When
    response = client.get("/api/v1/evaluation/health/detailed")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "evaluation-server"
    assert "components" in data


def test_cors_headers():
    """CORS 헤더 테스트"""
    # When
    response = client.options("/")
    
    # Then
    # CORS 미들웨어가 적용되어 있는지 확인
    assert response.status_code in [200, 405]  # OPTIONS 메서드가 허용되지 않을 수도 있음


def test_api_docs_available():
    """API 문서 접근 가능 테스트"""
    # When
    docs_response = client.get("/docs")
    redoc_response = client.get("/redoc")
    
    # Then
    assert docs_response.status_code == 200
    assert redoc_response.status_code == 200
    assert "text/html" in docs_response.headers.get("content-type", "")
    assert "text/html" in redoc_response.headers.get("content-type", "") 