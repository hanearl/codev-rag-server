from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class IndexedDocument(BaseModel):
    """인덱싱된 문서 모델"""
    id: str
    content: str
    metadata: Dict[str, Any]
    indexed_at: str

class BaseIndex(ABC):
    """기본 인덱스 인터페이스"""
    
    @abstractmethod
    async def add_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        문서 추가
        
        Args:
            documents: 추가할 문서 리스트
            
        Returns:
            추가된 문서들의 ID 리스트
        """
        pass
    
    @abstractmethod
    async def update_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """
        문서 업데이트
        
        Args:
            doc_id: 업데이트할 문서 ID
            document: 업데이트할 문서 데이터
            
        Returns:
            업데이트 성공 여부
        """
        pass
    
    @abstractmethod
    async def delete_document(self, doc_id: str) -> bool:
        """
        문서 삭제
        
        Args:
            doc_id: 삭제할 문서 ID
            
        Returns:
            삭제 성공 여부
        """
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[IndexedDocument]:
        """
        문서 검색
        
        Args:
            query: 검색 쿼리
            limit: 검색 결과 수 제한
            
        Returns:
            검색된 문서 리스트
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        인덱스 통계 정보
        
        Returns:
            인덱스 통계 정보 딕셔너리
        """
        pass 