import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.integration
def test_generation_api_health_check():
    """생성 API 헬스체크 테스트"""
    client = TestClient(app)
    
    # When
    response = client.get("/api/v1/generate/health")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "generation-service"

@pytest.mark.integration
def test_generation_api_supported_languages():
    """지원 언어 목록 API 테스트"""
    client = TestClient(app)
    
    # When
    response = client.get("/api/v1/generate/languages")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert "languages" in data
    assert len(data["languages"]) >= 5
    
    # Python 지원 확인
    python_lang = next((lang for lang in data["languages"] if lang["code"] == "python"), None)
    assert python_lang is not None
    assert python_lang["name"] == "Python"

@pytest.mark.integration
@pytest.mark.skipif(True, reason="LLM 서비스 연동 필요")
def test_generation_api_integration():
    """생성 API 통합 테스트 (LLM 서비스 연동 시에만 실행)"""
    client = TestClient(app)
    
    # When: 코드 생성 수행
    response = client.post("/api/v1/generate/", json={
        "query": "Create a simple function to add two numbers",
        "context_limit": 3,
        "language": "python",
        "include_tests": False
    })
    
    # Then: 성공적인 응답
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "generated_code" in data
    assert "contexts_used" in data
    assert "generation_time_ms" in data
    assert data["generation_time_ms"] < 60000  # 1분 이내

def test_generation_api_validation():
    """생성 API 요청 검증 테스트"""
    client = TestClient(app)
    
    # When: 필수 필드 누락
    response = client.post("/api/v1/generate/", json={
        "language": "python"  # query 필드 누락
    })
    
    # Then: 검증 오류
    assert response.status_code == 422
    
    # When: 지원하지 않는 언어
    response = client.post("/api/v1/generate/", json={
        "query": "test",
        "language": "unsupported_language"
    })
    
    # Then: 검증 오류
    assert response.status_code == 422

def test_generation_api_invalid_context_limit():
    """잘못된 컨텍스트 제한 테스트"""
    client = TestClient(app)
    
    # When: 범위를 벗어난 context_limit
    response = client.post("/api/v1/generate/", json={
        "query": "test",
        "language": "python",
        "context_limit": 15  # 최대 10 초과
    })
    
    # Then: 검증 오류
    assert response.status_code == 422 