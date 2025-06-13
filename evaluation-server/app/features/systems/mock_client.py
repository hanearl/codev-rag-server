import random
import asyncio
from typing import List, Dict, Any
from app.features.systems.interface import RAGSystemInterface, RetrievalResult


class MockRAGSystem(RAGSystemInterface):
    """테스트용 Mock RAG 시스템"""
    
    def __init__(
        self, 
        config=None,  # 호환성을 위해 선택적 매개변수
        embedding_dim: int = 768,
        simulate_delay: bool = True,
        failure_rate: float = 0.0
    ):
        """
        Args:
            config: RAG 시스템 설정 (선택적)
            embedding_dim: 임베딩 차원 수
            simulate_delay: 네트워크 지연 시뮬레이션 여부
            failure_rate: 실패율 (0.0 ~ 1.0)
        """
        if config:
            super().__init__(config)
        self.embedding_dim = embedding_dim
        self.simulate_delay = simulate_delay
        self.failure_rate = failure_rate
        
        # 더미 문서 데이터
        self.documents = [
            {
                "content": "도서 관리를 담당하는 BookController 클래스입니다.",
                "filepath": "src/main/java/com/skax/library/controller/BookController.java",
                "score": 0.95
            },
            {
                "content": "회원 정보를 관리하는 MemberService 인터페이스입니다.",
                "filepath": "src/main/java/com/skax/library/service/MemberService.java",
                "score": 0.88
            },
            {
                "content": "도서 대출 처리를 담당하는 LoanController 클래스입니다.",
                "filepath": "src/main/java/com/skax/library/controller/LoanController.java",
                "score": 0.82
            },
            {
                "content": "도서 엔티티 클래스입니다.",
                "filepath": "src/main/java/com/skax/library/model/Book.java",
                "score": 0.75
            },
            {
                "content": "회원 서비스 구현체입니다.",
                "filepath": "src/main/java/com/skax/library/service/impl/MemberServiceImpl.java",
                "score": 0.70
            },
            {
                "content": "대출 정보 저장소입니다.",
                "filepath": "src/main/java/com/skax/library/repository/LoanRepository.java",
                "score": 0.65
            },
            {
                "content": "도서 검색 서비스입니다.",
                "filepath": "src/main/java/com/skax/library/service/impl/BookServiceImpl.java",
                "score": 0.60
            },
            {
                "content": "회원 엔티티 클래스입니다.",
                "filepath": "src/main/java/com/skax/library/model/Member.java",
                "score": 0.55
            },
            {
                "content": "대출 엔티티 클래스입니다.",
                "filepath": "src/main/java/com/skax/library/model/Loan.java",
                "score": 0.50
            },
            {
                "content": "도서 저장소입니다.",
                "filepath": "src/main/java/com/skax/library/repository/BookRepository.java",
                "score": 0.45
            }
        ]
    
    async def embed_query(self, query: str) -> List[float]:
        """더미 임베딩 생성"""
        await self._simulate_processing()
        
        if random.random() < self.failure_rate:
            raise Exception("Mock embedding failure")
        
        # 쿼리 기반으로 결정적인 임베딩 생성
        random.seed(hash(query) % 2**32)
        embedding = [random.uniform(-1, 1) for _ in range(self.embedding_dim)]
        
        return embedding
    
    async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """더미 검색 결과 생성"""
        await self._simulate_processing()
        
        if random.random() < self.failure_rate:
            raise Exception("Mock retrieval failure")
        
        # 쿼리에 따라 관련성 점수 조정
        results = []
        query_lower = query.lower()
        
        for doc in self.documents:
            # 쿼리와 문서 내용의 관련성 계산 (간단한 키워드 매칭)
            relevance_boost = 0.0
            if any(keyword in doc["content"].lower() for keyword in query_lower.split()):
                relevance_boost = 0.2
            
            adjusted_score = min(1.0, doc["score"] + relevance_boost + random.uniform(-0.1, 0.1))
            
            result = RetrievalResult(
                content=doc["content"],
                score=adjusted_score,
                filepath=doc["filepath"],
                metadata={
                    "document_id": hash(doc["filepath"]) % 10000,
                    "source": "mock_system"
                }
            )
            results.append(result)
        
        # 점수 순으로 정렬하고 상위 k개 반환
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    
    async def health_check(self) -> bool:
        """항상 정상 상태 반환"""
        await self._simulate_processing(delay_range=(0.1, 0.3))
        
        if random.random() < self.failure_rate:
            return False
        
        return True
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Mock 시스템 정보 반환"""
        return {
            "type": "MockRAGSystem",
            "status": "healthy",
            "embedding_dim": self.embedding_dim,
            "document_count": len(self.documents),
            "features": {
                "embedding": True,
                "retrieval": True,
                "java_support": True
            }
        }
    
    async def _simulate_processing(self, delay_range: tuple = (0.5, 2.0)):
        """네트워크 지연 시뮬레이션"""
        if self.simulate_delay:
            delay = random.uniform(*delay_range)
            await asyncio.sleep(delay)
    
    def set_failure_rate(self, rate: float):
        """실패율 설정 (테스트용)"""
        self.failure_rate = max(0.0, min(1.0, rate))
    
    def add_document(self, content: str, filepath: str, score: float = 0.5):
        """문서 추가 (테스트용)"""
        self.documents.append({
            "content": content,
            "filepath": filepath,
            "score": score
        })
    
    def clear_documents(self):
        """모든 문서 제거 (테스트용)"""
        self.documents.clear()
    
    async def close(self):
        """리소스 정리 (Mock은 정리할 것이 없음)"""
        pass
    
    def __repr__(self):
        return f"<MockRAGSystem(docs={len(self.documents)}, dim={self.embedding_dim})>" 