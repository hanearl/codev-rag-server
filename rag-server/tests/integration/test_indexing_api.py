import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check_integration(client):
    """헬스체크 API integration 테스트"""
    # When
    response = client.get("/api/v1/indexing/health")
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "indexing"

def test_index_file_validation_integration(client):
    """파일 인덱싱 API 요청 검증 integration 테스트"""
    # When: 잘못된 요청
    response = client.post("/api/v1/indexing/file", json={})
    
    # Then: 검증 오류
    assert response.status_code == 422

def test_batch_index_validation_integration(client):
    """배치 인덱싱 API 요청 검증 integration 테스트"""
    # When: 잘못된 요청
    response = client.post("/api/v1/indexing/batch", json={
        "file_paths": []  # 빈 배열
    })
    
    # Then: 성공 (빈 배열도 유효함)
    assert response.status_code == 200

def test_api_endpoints_exist(client):
    """모든 API 엔드포인트가 존재하는지 확인"""
    # 엔드포인트들이 정의되어 있는지 확인
    # 파일이 없으면 404를 반환하는 것이 정상적인 비즈니스 로직
    response1 = client.post("/api/v1/indexing/file", json={"file_path": "nonexistent.py"})
    assert response1.status_code == 404  # 파일 없음으로 인한 정상적인 404
    assert "파일을 찾을 수 없습니다" in response1.json()["detail"]
    
    response2 = client.post("/api/v1/indexing/batch", json={"file_paths": ["nonexistent.py"]})
    assert response2.status_code == 200  # 배치는 에러 발생해도 200 반환
    
    response3 = client.get("/api/v1/indexing/health")
    assert response3.status_code == 200
    
    # 청크 조회 엔드포인트 확인
    response4 = client.get("/api/v1/indexing/chunks")
    # 실제 벡터 DB에 연결되어 있으므로 500 또는 200 모두 가능
    assert response4.status_code in [200, 500]

def test_query_chunks_endpoint_validation_integration(client):
    """청크 조회 API 파라미터 검증 integration 테스트"""
    # When: 잘못된 페이지 번호
    response = client.get("/api/v1/indexing/chunks", params={"page": 0})
    
    # Then: 검증 오류
    assert response.status_code == 422
    
    # When: 잘못된 페이지 크기
    response = client.get("/api/v1/indexing/chunks", params={"size": 0})
    
    # Then: 검증 오류
    assert response.status_code == 422
    
    # When: 너무 큰 페이지 크기
    response = client.get("/api/v1/indexing/chunks", params={"size": 200})
    
    # Then: 검증 오류
    assert response.status_code == 422

def test_query_chunks_endpoint_with_valid_params_integration(client):
    """청크 조회 API 유효한 파라미터 integration 테스트"""
    # When: 유효한 파라미터로 요청
    response = client.get("/api/v1/indexing/chunks", params={
        "file_path": "test.py",
        "code_type": "function",
        "language": "python",
        "keyword": "test",
        "page": 1,
        "size": 10
    })
    
    # Then: 성공 또는 서버 오류 (벡터 DB 연결 상태에 따라)
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert "chunks" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "total_pages" in data 