# Task 7: 하이브리드 아키텍처 기반 구조 생성

## 📋 작업 개요
LlamaIndex와 LangChain을 활용한 하이브리드 아키텍처로 전환하기 위한 기반 디렉토리 구조를 생성하고 기본 설정을 구축합니다.

## 🎯 작업 목표
- 새로운 하이브리드 아키텍처를 위한 디렉토리 구조 생성
- 필요한 의존성 패키지 설치 및 설정
- 기본 인터페이스 및 베이스 클래스 정의

## 📁 생성할 디렉토리 구조

```
app/
├── retriever/              # LlamaIndex 기반 검색
│   ├── __init__.py
│   ├── base_retriever.py   # 기본 리트리버 인터페이스
│   └── exceptions.py       # 리트리버 관련 예외
├── index/                  # LlamaIndex 인덱스 관리
│   ├── __init__.py
│   ├── base_index.py       # 기본 인덱스 인터페이스
│   └── exceptions.py       # 인덱스 관련 예외
├── llm/                    # LangChain 기반 LLM 처리
│   ├── __init__.py
│   ├── base_chain.py       # 기본 체인 인터페이스
│   └── exceptions.py       # LLM 관련 예외
└── features/
    └── hybrid_rag/         # 새로운 통합 모듈
        ├── __init__.py
        ├── schema.py       # 통합 스키마
        └── exceptions.py   # 하이브리드 RAG 관련 예외
```

## 🔧 구현 사항

### 1. 의존성 추가

기존 `requirements.txt`에 다음 패키지 추가:

```text
# LlamaIndex 관련
llama-index-core==0.10.57
llama-index-readers-file==0.1.23
llama-index-embeddings-openai==0.1.10
llama-index-vector-stores-qdrant==0.2.8
llama-index-retrievers-bm25==0.1.4

# LangChain 관련
langchain==0.2.11
langchain-openai==0.1.17
langchain-core==0.2.25
langchain-community==0.2.10

# 코드 파싱 관련
javalang==0.13.0
ast-tools==0.2.0
tree-sitter==0.20.4
tree-sitter-java==0.20.2
tree-sitter-python==0.20.4
tree-sitter-javascript==0.20.4
```

### 2. 기본 인터페이스 구현

#### 2.1 Base Retriever Interface

```python
# app/retriever/base_retriever.py
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
        """검색 실행"""
        pass
    
    @abstractmethod
    async def setup(self) -> None:
        """리트리버 초기화"""
        pass
    
    @abstractmethod
    async def teardown(self) -> None:
        """리트리버 정리"""
        pass
```

#### 2.2 Base Index Interface

```python
# app/index/base_index.py
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
        """문서 추가"""
        pass
    
    @abstractmethod
    async def update_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """문서 업데이트"""
        pass
    
    @abstractmethod
    async def delete_document(self, doc_id: str) -> bool:
        """문서 삭제"""
        pass
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[IndexedDocument]:
        """문서 검색"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """인덱스 통계 정보"""
        pass
```

#### 2.3 Base Chain Interface

```python
# app/llm/base_chain.py
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
        """체인 실행"""
        pass
    
    @abstractmethod
    async def setup(self) -> None:
        """체인 초기화"""
        pass
    
    @abstractmethod
    async def teardown(self) -> None:
        """체인 정리"""
        pass
```

### 3. 예외 클래스 정의

#### 3.1 Retriever Exceptions

```python
# app/retriever/exceptions.py
class RetrieverError(Exception):
    """리트리버 기본 예외"""
    pass

class RetrieverSetupError(RetrieverError):
    """리트리버 설정 예외"""
    pass

class RetrieverQueryError(RetrieverError):
    """리트리버 쿼리 예외"""
    pass

class RetrieverConnectionError(RetrieverError):
    """리트리버 연결 예외"""
    pass
```

#### 3.2 Index Exceptions

```python
# app/index/exceptions.py
class IndexError(Exception):
    """인덱스 기본 예외"""
    pass

class IndexBuildError(IndexError):
    """인덱스 빌드 예외"""
    pass

class IndexQueryError(IndexError):
    """인덱스 쿼리 예외"""
    pass

class IndexUpdateError(IndexError):
    """인덱스 업데이트 예외"""
    pass
```

#### 3.3 LLM Exceptions

```python
# app/llm/exceptions.py
class LLMError(Exception):
    """LLM 기본 예외"""
    pass

class LLMConfigError(LLMError):
    """LLM 설정 예외"""
    pass

class LLMProcessingError(LLMError):
    """LLM 처리 예외"""
    pass

class LLMConnectionError(LLMError):
    """LLM 연결 예외"""
    pass
```

### 4. HybridRAG 통합 스키마

```python
# app/features/hybrid_rag/schema.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class HybridSearchRequest(BaseModel):
    """하이브리드 검색 요청"""
    query: str = Field(..., description="검색 쿼리")
    limit: int = Field(default=10, ge=1, le=50, description="검색 결과 수")
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="벡터 검색 가중치")
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="키워드 검색 가중치")
    use_rrf: bool = Field(default=True, description="RRF 사용 여부")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="검색 필터")

class HybridSearchResult(BaseModel):
    """하이브리드 검색 결과"""
    id: str
    content: str
    file_path: Optional[str] = None
    function_name: Optional[str] = None
    language: Optional[str] = None
    vector_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0
    metadata: Dict[str, Any] = {}

class HybridSearchResponse(BaseModel):
    """하이브리드 검색 응답"""
    query: str
    results: List[HybridSearchResult]
    total_results: int
    search_time_ms: int
    search_metadata: Dict[str, Any] = {}

class ExplainRequest(BaseModel):
    """코드 설명 요청"""
    query: str = Field(..., description="설명 요청 질문")
    search_results: Optional[List[HybridSearchResult]] = Field(default=None, description="검색 결과")
    include_context: bool = Field(default=True, description="컨텍스트 포함 여부")
    language_preference: str = Field(default="korean", description="응답 언어")

class ExplainResponse(BaseModel):
    """코드 설명 응답"""
    query: str
    explanation: str
    context_used: List[str] = []
    processing_time_ms: int = 0
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = {}
```

### 5. HybridRAG Exceptions

```python
# app/features/hybrid_rag/exceptions.py
class HybridRAGError(Exception):
    """하이브리드 RAG 기본 예외"""
    pass

class HybridRAGConfigError(HybridRAGError):
    """하이브리드 RAG 설정 예외"""
    pass

class HybridRAGProcessingError(HybridRAGError):
    """하이브리드 RAG 처리 예외"""
    pass

class HybridRAGSearchError(HybridRAGError):
    """하이브리드 RAG 검색 예외"""
    pass
```

## ✅ 완료 조건

1. **디렉토리 구조 생성**: 모든 필요한 디렉토리와 `__init__.py` 파일 생성
2. **의존성 설치**: 새로운 패키지들이 `requirements.txt`에 추가되고 설치됨
3. **기본 인터페이스 구현**: 모든 베이스 클래스가 구현되고 타입 힌트가 완전함
4. **예외 클래스 정의**: 각 모듈별 예외 클래스가 정의됨
5. **스키마 정의**: HybridRAG의 요청/응답 스키마가 완전히 정의됨
6. **테스트 준비**: 기본 구조에 대한 간단한 테스트 작성

## 📋 다음 Task와의 연관관계

- **Task 8**: 이 Task에서 생성한 `BaseRetriever` 인터페이스를 상속받아 AST 파서 구현
- **Task 9**: `BaseIndex` 인터페이스를 활용하여 Document Builder 구현
- **Task 10-12**: 각각 Vector, BM25, Hybrid 인덱스/리트리버 구현

## 🚨 주의사항

1. **기존 코드와의 충돌 방지**: 새로운 디렉토리를 생성하되 기존 features와 충돌하지 않도록 주의
2. **타입 안정성**: 모든 인터페이스에 완전한 타입 힌트 제공
3. **확장성 고려**: 향후 다른 언어나 기능 추가를 고려한 유연한 구조 설계
4. **성능 고려**: 비동기 처리를 기본으로 하는 인터페이스 설계

## 🧪 테스트 계획

```python
# tests/unit/test_hybrid_architecture_foundation.py
def test_base_interfaces_defined():
    """기본 인터페이스들이 올바르게 정의되었는지 테스트"""
    pass

def test_exception_classes_inheritance():
    """예외 클래스들이 올바른 상속 구조를 가지는지 테스트"""
    pass

def test_schema_validation():
    """스키마 클래스들이 올바른 검증을 수행하는지 테스트"""
    pass
```

이 Task는 전체 하이브리드 아키텍처의 토대가 되는 중요한 작업입니다. 견고한 기반을 구축하여 후속 Task들이 원활하게 진행될 수 있도록 해야 합니다. 