from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.db.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """기본 Repository 클래스"""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """ID로 단일 객체 조회"""
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[ModelType]:
        """다중 객체 조회 (페이지네이션)"""
        return db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> ModelType:
        """새 객체 생성"""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(
        self, 
        db: Session, 
        *, 
        db_obj: ModelType, 
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """기존 객체 업데이트"""
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def remove(self, db: Session, *, id: int) -> Optional[ModelType]:
        """객체 삭제"""
        obj = self.get(db, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def get_by_field(
        self, 
        db: Session, 
        field_name: str, 
        field_value: Any
    ) -> Optional[ModelType]:
        """특정 필드로 객체 조회"""
        return db.query(self.model).filter(
            getattr(self.model, field_name) == field_value
        ).first()
    
    def get_multi_by_field(
        self, 
        db: Session, 
        field_name: str, 
        field_value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """특정 필드로 다중 객체 조회"""
        return db.query(self.model).filter(
            getattr(self.model, field_name) == field_value
        ).offset(skip).limit(limit).all() 