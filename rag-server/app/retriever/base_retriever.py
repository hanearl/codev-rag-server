from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class RetrievalResult(BaseModel):
    """검색 결과 기본 모델"""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float
    source: str = "unknown"

class BaseRetriever(ABC):
    """기본 리트리버 인터페이스"""
    
    @abstractmethod
    async def retrieve(
        self, 
        query: str, 
        limit: int = 10,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        검색 실행
        
        Args:
            query: 검색 쿼리
            limit: 검색 결과 수 제한
            **kwargs: 추가 검색 옵션
            
        Returns:
            검색 결과 리스트
        """
        pass
    
    @abstractmethod
    async def setup(self) -> None:
        """
        리트리버 초기화
        
        검색 인덱스 로드, 연결 설정 등 초기화 작업을 수행합니다.
        """
        pass
    
    @abstractmethod
    async def teardown(self) -> None:
        """
        리트리버 정리
        
        연결 해제, 리소스 정리 등 종료 작업을 수행합니다.
        """
        pass 