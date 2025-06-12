from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class RetrievalResult(BaseModel):
    """검색 결과 모델"""
    content: str
    score: float
    filepath: Optional[str] = None
    metadata: Dict[str, Any] = {}


class RAGSystemInterface(ABC):
    """RAG 시스템 인터페이스"""
    
    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """
        쿼리를 임베딩으로 변환
        
        Args:
            query: 검색 쿼리
            
        Returns:
            임베딩 벡터
        """
        pass
    
    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """
        쿼리에 대한 검색 수행
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 결과 수
            
        Returns:
            검색 결과 리스트
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        시스템 상태 확인
        
        Returns:
            시스템이 정상이면 True, 아니면 False
        """
        pass
    
    async def get_system_info(self) -> Dict[str, Any]:
        """
        시스템 정보 조회 (선택적 구현)
        
        Returns:
            시스템 정보 딕셔너리
        """
        return {
            "type": self.__class__.__name__,
            "status": "unknown"
        } 