from typing import List, Optional
from fastapi import HTTPException, status
from app.features.users.repository import UserRepository
from app.features.users.schema import UserCreate, UserUpdate, UserResponse


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def get_user_by_id(self, user_id: int) -> UserResponse:
        """ID로 사용자 조회"""
        user = self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        return UserResponse.model_validate(user)

    def get_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """모든 사용자 조회"""
        users = self.repository.get_all(skip=skip, limit=limit)
        return [UserResponse.model_validate(user) for user in users]

    def create_user(self, user_data: UserCreate) -> UserResponse:
        """사용자 생성"""
        # 중복 이메일 체크
        existing_user = self.repository.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 존재하는 이메일입니다."
            )
        
        user = self.repository.create(user_data)
        return UserResponse.model_validate(user)

    def update_user(self, user_id: int, user_data: UserUpdate) -> UserResponse:
        """사용자 수정"""
        # 이메일 중복 체크 (변경하는 경우)
        if user_data.email:
            existing_user = self.repository.get_by_email(user_data.email)
            if existing_user and existing_user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="이미 존재하는 이메일입니다."
                )

        user = self.repository.update(user_id, user_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        return UserResponse.model_validate(user)

    def delete_user(self, user_id: int) -> bool:
        """사용자 삭제"""
        result = self.repository.delete(user_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )
        return result 