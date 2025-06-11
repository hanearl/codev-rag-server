import pytest
from fastapi import HTTPException
from app.features.users.schema import UserCreate, UserUpdate


def test_create_user_should_return_user_with_id(user_service, user_repository):
    """사용자 생성 시 ID가 포함된 사용자 정보를 반환해야 함"""
    # Given
    user_data = UserCreate(name="홍길동", email="hong@example.com")
    
    # When
    result = user_service.create_user(user_data)
    
    # Then
    assert result.id is not None
    assert result.name == "홍길동"
    assert result.email == "hong@example.com"
    assert result.is_active is True


def test_create_user_should_raise_exception_when_email_duplicated(user_service):
    """중복된 이메일로 사용자 생성 시 예외가 발생해야 함"""
    # Given
    user_data1 = UserCreate(name="홍길동", email="hong@example.com")
    user_data2 = UserCreate(name="김철수", email="hong@example.com")
    user_service.create_user(user_data1)
    
    # When & Then
    with pytest.raises(HTTPException) as exc_info:
        user_service.create_user(user_data2)
    
    assert exc_info.value.status_code == 400
    assert "이미 존재하는 이메일입니다." in str(exc_info.value.detail)


def test_get_user_by_id_should_return_user_when_exists(user_service):
    """존재하는 사용자 ID로 조회 시 해당 사용자를 반환해야 함"""
    # Given
    user_data = UserCreate(name="홍길동", email="hong@example.com")
    created_user = user_service.create_user(user_data)
    
    # When
    result = user_service.get_user_by_id(created_user.id)
    
    # Then
    assert result.id == created_user.id
    assert result.name == "홍길동"
    assert result.email == "hong@example.com"


def test_get_user_by_id_should_raise_exception_when_not_exists(user_service):
    """존재하지 않는 사용자 ID로 조회 시 예외가 발생해야 함"""
    # Given
    non_existent_id = 999
    
    # When & Then
    with pytest.raises(HTTPException) as exc_info:
        user_service.get_user_by_id(non_existent_id)
    
    assert exc_info.value.status_code == 404
    assert "사용자를 찾을 수 없습니다." in str(exc_info.value.detail)


def test_update_user_should_return_updated_user_when_valid_data(user_service):
    """유효한 데이터로 사용자 수정 시 수정된 사용자를 반환해야 함"""
    # Given
    user_data = UserCreate(name="홍길동", email="hong@example.com")
    created_user = user_service.create_user(user_data)
    update_data = UserUpdate(name="홍길동2", email="hong2@example.com")
    
    # When
    result = user_service.update_user(created_user.id, update_data)
    
    # Then
    assert result.id == created_user.id
    assert result.name == "홍길동2"
    assert result.email == "hong2@example.com"


def test_delete_user_should_return_true_when_user_exists(user_service):
    """존재하는 사용자 삭제 시 True를 반환해야 함"""
    # Given
    user_data = UserCreate(name="홍길동", email="hong@example.com")
    created_user = user_service.create_user(user_data)
    
    # When
    result = user_service.delete_user(created_user.id)
    
    # Then
    assert result is True


def test_delete_user_should_raise_exception_when_not_exists(user_service):
    """존재하지 않는 사용자 삭제 시 예외가 발생해야 함"""
    # Given
    non_existent_id = 999
    
    # When & Then
    with pytest.raises(HTTPException) as exc_info:
        user_service.delete_user(non_existent_id)
    
    assert exc_info.value.status_code == 404
    assert "사용자를 찾을 수 없습니다." in str(exc_info.value.detail) 