import pytest
from fastapi import status


def test_create_user_should_return_201_when_valid_data(client):
    """유효한 데이터로 사용자 생성 시 201 상태코드를 반환해야 함"""
    # Given
    user_data = {
        "name": "홍길동",
        "email": "hong@example.com"
    }
    
    # When
    response = client.post("/api/v1/users/", json=user_data)
    
    # Then
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "홍길동"
    assert data["email"] == "hong@example.com"
    assert data["id"] is not None


def test_create_user_should_return_400_when_duplicate_email(client):
    """중복된 이메일로 사용자 생성 시 400 상태코드를 반환해야 함"""
    # Given
    user_data = {
        "name": "홍길동",
        "email": "hong@example.com"
    }
    client.post("/api/v1/users/", json=user_data)  # 첫 번째 사용자 생성
    
    # When
    response = client.post("/api/v1/users/", json=user_data)  # 중복 이메일로 생성 시도
    
    # Then
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "이미 존재하는 이메일입니다." in response.json()["detail"]


def test_get_user_should_return_200_when_user_exists(client):
    """존재하는 사용자 조회 시 200 상태코드를 반환해야 함"""
    # Given
    user_data = {
        "name": "홍길동",
        "email": "hong@example.com"
    }
    create_response = client.post("/api/v1/users/", json=user_data)
    user_id = create_response.json()["id"]
    
    # When
    response = client.get(f"/api/v1/users/{user_id}")
    
    # Then
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == user_id
    assert data["name"] == "홍길동"
    assert data["email"] == "hong@example.com"


def test_get_user_should_return_404_when_user_not_exists(client):
    """존재하지 않는 사용자 조회 시 404 상태코드를 반환해야 함"""
    # Given
    non_existent_id = 999
    
    # When
    response = client.get(f"/api/v1/users/{non_existent_id}")
    
    # Then
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "사용자를 찾을 수 없습니다." in response.json()["detail"]


def test_get_users_should_return_200_with_user_list(client):
    """사용자 목록 조회 시 200 상태코드와 사용자 목록을 반환해야 함"""
    # Given
    user_data1 = {"name": "홍길동", "email": "hong@example.com"}
    user_data2 = {"name": "김철수", "email": "kim@example.com"}
    client.post("/api/v1/users/", json=user_data1)
    client.post("/api/v1/users/", json=user_data2)
    
    # When
    response = client.get("/api/v1/users/")
    
    # Then
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert any(user["name"] == "홍길동" for user in data)
    assert any(user["name"] == "김철수" for user in data)


def test_update_user_should_return_200_when_valid_data(client):
    """유효한 데이터로 사용자 수정 시 200 상태코드를 반환해야 함"""
    # Given
    user_data = {"name": "홍길동", "email": "hong@example.com"}
    create_response = client.post("/api/v1/users/", json=user_data)
    user_id = create_response.json()["id"]
    
    update_data = {"name": "홍길동2", "email": "hong2@example.com"}
    
    # When
    response = client.put(f"/api/v1/users/{user_id}", json=update_data)
    
    # Then
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "홍길동2"
    assert data["email"] == "hong2@example.com"


def test_delete_user_should_return_204_when_user_exists(client):
    """존재하는 사용자 삭제 시 204 상태코드를 반환해야 함"""
    # Given
    user_data = {"name": "홍길동", "email": "hong@example.com"}
    create_response = client.post("/api/v1/users/", json=user_data)
    user_id = create_response.json()["id"]
    
    # When
    response = client.delete(f"/api/v1/users/{user_id}")
    
    # Then
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_delete_user_should_return_404_when_user_not_exists(client):
    """존재하지 않는 사용자 삭제 시 404 상태코드를 반환해야 함"""
    # Given
    non_existent_id = 999
    
    # When
    response = client.delete(f"/api/v1/users/{non_existent_id}")
    
    # Then
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "사용자를 찾을 수 없습니다." in response.json()["detail"] 