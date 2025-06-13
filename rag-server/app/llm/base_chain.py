from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ChainInput(BaseModel):
    """체인 입력 모델"""
    query: str
    context: List[Dict[str, Any]] = []
    parameters: Dict[str, Any] = {}

class ChainOutput(BaseModel):
    """체인 출력 모델"""
    response: str
    metadata: Dict[str, Any] = {}
    processing_time_ms: int = 0

class BaseChain(ABC):
    """기본 체인 인터페이스"""
    
    @abstractmethod
    async def run(self, input_data: ChainInput) -> ChainOutput:
        """
        체인 실행
        
        Args:
            input_data: 체인 입력 데이터
            
        Returns:
            체인 실행 결과
        """
        pass
    
    @abstractmethod
    async def setup(self) -> None:
        """
        체인 초기화
        
        LLM 연결, 프롬프트 템플릿 설정 등 초기화 작업을 수행합니다.
        """
        pass
    
    @abstractmethod
    async def teardown(self) -> None:
        """
        체인 정리
        
        연결 해제, 리소스 정리 등 종료 작업을 수행합니다.
        """
        pass 