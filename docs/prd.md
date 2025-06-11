# 코드 어시스턴트 PRD (초안)

## 개요
본 시스템은 AI 기반 코드 어시스턴트로, 사용자의 질문에 대한 정확한 코드 검색 및 생성 기능을 제공한다. Retrieval-Augmented Generation(RAG) 구조를 기반으로 하며, 임베딩 + BM25 기반의 하이브리드 검색, LLM 기반 코드 생성, 프롬프트 템플릿 관리 기능 등을 포함한다.

---

## 1. 시스템 구성 요약

- **Embedding Server**: 코드 및 AST 임베딩 처리
- **Vector DB + BM25 저장소**: 유사도 검색 및 키워드 기반 검색용 저장소
- **Retriever Interface**: 하이브리드 검색 및 리트리버 모듈화
- **Code Generator**: 코드 생성 및 병합, 에러 검증 기능 포함
- **Prompt Manager**: LLM 프롬프트 템플릿 CRUD 및 API 제공

---

## 2. 기능 명세

### 2.1 코드 임베딩

- **입력**: 코드, AST
- **처리 방식**:
  - 코드: 청크 단위(예: 함수, 클래스)로 임베딩
  - AST: 구조 정보 추출 후 병렬 저장
- **출력 저장소**:
  - Vector DB (예: Chroma, Qdrant)
  - BM25 인덱스 (예: Elasticsearch, 파일 기반)

### 2.2 하이브리드 리트리버

- **기본 동작**:
  - 사용자 쿼리에 대해 벡터 유사도 + 키워드 점수를 조합하여 상위 결과 반환
- **구현 구조**:
  - 공통 인터페이스 설계 (리트리버 클래스 기반)
  - 확장 가능한 구조 (예: Reranker, AST 기반 탐색기 추가 가능)
- **예상 출력**:
  - 관련 코드 스니펫 + 메타데이터 (파일 경로, 토픽 등)

### 2.3 코드 생성 및 검증

- **기능**:
  - LLM 기반 코드 생성
  - 기존 코드와의 병합 기능
  - 생성된 코드에 대한 오류 검증 (예: LLM 검토, 정적 분석)
- **옵션 설정**:
  - 병합 여부 ON/OFF
  - 에러 검증 여부 ON/OFF
  - LLM 부하를 고려한 설정값 외부화

### 2.4 프롬프트 템플릿 관리

- **기능**:
  - 프롬프트 템플릿 CRUD
  - LLM 호출 use-case별 프롬프트 등록
  - 프롬프트 이력 관리 (버전 관리 또는 기록)
- **API 제공**:
  - RESTful 구조
  - 템플릿 저장, 불러오기, 수정, 삭제

---

## 3. 시스템 구성 예 (docker-compose 기준)

```yaml
version: '3'
services:
  embedding-server:
    build: ./embedding
    ports:
      - "8001:8001"

  retriever-server:
    build: ./retriever
    ports:
      - "8002:8002"

  llm-server:
    image: your-llm-image
    ports:
      - "8003:8003"

  vector-db:
    image: qdrant/qdrant
    ports:
      - "6333:6333"

  bm25-index:
    image: elasticsearch:8.12
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"