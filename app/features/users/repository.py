from sqlalchemy.orm import Session
from typing import List, Optional
from app.features.users.model import User
from app.features.users.schema import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        return self.db.query(User).filter(User.email == email).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """모든 사용자 조회"""
        return self.db.query(User).offset(skip).limit(limit).all()

    def create(self, user_data: UserCreate) -> User:
        """사용자 생성"""
        user = User(**user_data.model_dump())
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """사용자 수정"""
        user = self.get_by_id(user_id)
        if user:
            update_data = user_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(user, key, value)
            self.db.commit()
            self.db.refresh(user)
        return user

    def delete(self, user_id: int) -> bool:
        """사용자 삭제"""
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False 