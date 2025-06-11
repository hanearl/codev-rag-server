import pytest
from pydantic import ValidationError
from app.features.users.schema import UserCreate, UserUpdate, UserResponse
from datetime import datetime


def test_user_create_should_validate_valid_data():
    """유효한 데이터로 UserCreate 스키마 검증이 성공해야 함"""
    # Given
    valid_data = {
        "name": "홍길동",
        "email": "hong@example.com"
    }
    
    # When
    user = UserCreate(**valid_data)
    
    # Then
    assert user.name == "홍길동"
    assert user.email == "hong@example.com"


def test_user_create_should_raise_error_when_invalid_email():
    """잘못된 이메일 형식으로 UserCreate 생성 시 ValidationError가 발생해야 함"""
    # Given
    invalid_data = {
        "name": "홍길동",
        "email": "invalid-email"
    }
    
    # When & Then
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(**invalid_data)
    
    assert "value is not a valid email address" in str(exc_info.value)


def test_user_create_should_raise_error_when_missing_required_fields():
    """필수 필드가 누락된 경우 ValidationError가 발생해야 함"""
    # Given
    incomplete_data = {
        "name": "홍길동"
        # email 누락
    }
    
    # When & Then
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(**incomplete_data)
    
    assert "field required" in str(exc_info.value)


def test_user_update_should_allow_partial_data():
    """UserUpdate는 부분적인 데이터 업데이트를 허용해야 함"""
    # Given
    partial_data = {
        "name": "홍길동2"
        # email은 제공하지 않음
    }
    
    # When
    user_update = UserUpdate(**partial_data)
    
    # Then
    assert user_update.name == "홍길동2"
    assert user_update.email is None
    assert user_update.is_active is None


def test_user_update_should_allow_empty_data():
    """UserUpdate는 빈 데이터도 허용해야 함"""
    # Given
    empty_data = {}
    
    # When
    user_update = UserUpdate(**empty_data)
    
    # Then
    assert user_update.name is None
    assert user_update.email is None
    assert user_update.is_active is None


def test_user_response_should_validate_complete_user_data():
    """완전한 사용자 데이터로 UserResponse 검증이 성공해야 함"""
    # Given
    complete_data = {
        "id": 1,
        "name": "홍길동",
        "email": "hong@example.com",
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    # When
    user_response = UserResponse(**complete_data)
    
    # Then
    assert user_response.id == 1
    assert user_response.name == "홍길동"
    assert user_response.email == "hong@example.com"
    assert user_response.is_active is True
    assert isinstance(user_response.created_at, datetime)
    assert isinstance(user_response.updated_at, datetime)


def test_user_response_should_raise_error_when_missing_required_fields():
    """UserResponse에서 필수 필드가 누락된 경우 ValidationError가 발생해야 함"""
    # Given
    incomplete_data = {
        "name": "홍길동",
        "email": "hong@example.com"
        # id, is_active, created_at, updated_at 누락
    }
    
    # When & Then
    with pytest.raises(ValidationError) as exc_info:
        UserResponse(**incomplete_data)
    
    error_str = str(exc_info.value)
    assert "field required" in error_str 