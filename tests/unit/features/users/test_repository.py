import pytest
from app.features.users.schema import UserCreate, UserUpdate


def test_create_should_return_user_with_id(user_repository):
    """사용자 생성 시 ID가 포함된 사용자를 반환해야 함"""
    # Given
    user_data = UserCreate(name="홍길동", email="hong@example.com")
    
    # When
    result = user_repository.create(user_data)
    
    # Then
    assert result.id is not None
    assert result.name == "홍길동"
    assert result.email == "hong@example.com"
    assert result.is_active is True


def test_get_by_id_should_return_user_when_exists(user_repository):
    """존재하는 ID로 조회 시 해당 사용자를 반환해야 함"""
    # Given
    user_data = UserCreate(name="홍길동", email="hong@example.com")
    created_user = user_repository.create(user_data)
    
    # When
    result = user_repository.get_by_id(created_user.id)
    
    # Then
    assert result is not None
    assert result.id == created_user.id
    assert result.name == "홍길동"
    assert result.email == "hong@example.com"


def test_get_by_id_should_return_none_when_not_exists(user_repository):
    """존재하지 않는 ID로 조회 시 None을 반환해야 함"""
    # Given
    non_existent_id = 999
    
    # When
    result = user_repository.get_by_id(non_existent_id)
    
    # Then
    assert result is None


def test_get_by_email_should_return_user_when_exists(user_repository):
    """존재하는 이메일로 조회 시 해당 사용자를 반환해야 함"""
    # Given
    user_data = UserCreate(name="홍길동", email="hong@example.com")
    created_user = user_repository.create(user_data)
    
    # When
    result = user_repository.get_by_email("hong@example.com")
    
    # Then
    assert result is not None
    assert result.id == created_user.id
    assert result.email == "hong@example.com"


def test_get_by_email_should_return_none_when_not_exists(user_repository):
    """존재하지 않는 이메일로 조회 시 None을 반환해야 함"""
    # Given
    non_existent_email = "nonexistent@example.com"
    
    # When
    result = user_repository.get_by_email(non_existent_email)
    
    # Then
    assert result is None


def test_get_all_should_return_all_users(user_repository):
    """모든 사용자 조회 시 생성된 모든 사용자를 반환해야 함"""
    # Given
    user_data1 = UserCreate(name="홍길동", email="hong@example.com")
    user_data2 = UserCreate(name="김철수", email="kim@example.com")
    user_repository.create(user_data1)
    user_repository.create(user_data2)
    
    # When
    result = user_repository.get_all()
    
    # Then
    assert len(result) == 2
    names = [user.name for user in result]
    assert "홍길동" in names
    assert "김철수" in names


def test_update_should_return_updated_user_when_exists(user_repository):
    """존재하는 사용자 수정 시 수정된 사용자를 반환해야 함"""
    # Given
    user_data = UserCreate(name="홍길동", email="hong@example.com")
    created_user = user_repository.create(user_data)
    update_data = UserUpdate(name="홍길동2")
    
    # When
    result = user_repository.update(created_user.id, update_data)
    
    # Then
    assert result is not None
    assert result.id == created_user.id
    assert result.name == "홍길동2"
    assert result.email == "hong@example.com"  # 변경되지 않은 필드


def test_update_should_return_none_when_not_exists(user_repository):
    """존재하지 않는 사용자 수정 시 None을 반환해야 함"""
    # Given
    non_existent_id = 999
    update_data = UserUpdate(name="홍길동2")
    
    # When
    result = user_repository.update(non_existent_id, update_data)
    
    # Then
    assert result is None


def test_delete_should_return_true_when_user_exists(user_repository):
    """존재하는 사용자 삭제 시 True를 반환해야 함"""
    # Given
    user_data = UserCreate(name="홍길동", email="hong@example.com")
    created_user = user_repository.create(user_data)
    
    # When
    result = user_repository.delete(created_user.id)
    
    # Then
    assert result is True
    # 삭제 확인
    deleted_user = user_repository.get_by_id(created_user.id)
    assert deleted_user is None


def test_delete_should_return_false_when_user_not_exists(user_repository):
    """존재하지 않는 사용자 삭제 시 False를 반환해야 함"""
    # Given
    non_existent_id = 999
    
    # When
    result = user_repository.delete(non_existent_id)
    
    # Then
    assert result is False 