# Spring Boot 샘플 프로젝트 RAG 인덱싱 가이드

이 문서는 `data/springboot-sample-pjt` 디렉토리의 Spring Boot 프로젝트를 RAG 서버에 인덱싱하는 방법을 설명합니다.

## 📋 개요

- **프로젝트 경로**: `data/springboot-sample-pjt`
- **지원 언어**: Java
- **인덱싱 타입**: Vector Search + BM25 Search
- **총 Java 파일 수**: 51개

## 🚀 사용 방법

### 1. 전체 프로젝트 인덱싱 (권장)

모든 Java 파일을 파싱하고 인덱싱합니다:

```bash
# 실행 권한 부여 (최초 1회)
chmod +x run_indexing.sh

# 인덱싱 실행
./run_indexing.sh
```

또는 Python 스크립트를 직접 실행:

```bash
python3 index_sample_project.py
```

### 2. 빠른 테스트 (일부 파일만)

주요 파일 5개만 선택하여 빠르게 테스트:

```bash
python3 test_sample_indexing.py
```

## 📝 사전 요구사항

### 1. RAG 서버 실행

먼저 RAG 서버가 실행되어 있어야 합니다:

```bash
cd rag-server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. 필요한 Python 패키지

```bash
pip install httpx asyncio
```

### 3. 프로젝트 구조 확인

```
data/springboot-sample-pjt/
├── src/main/java/
│   ├── com/skax/library/controller/
│   ├── com/skax/library/service/
│   ├── com/skax/library/dto/
│   ├── com/skax/library/repository/
│   └── ...
└── ...
```

## 🔧 스크립트 설명

### `index_sample_project.py`

**전체 프로젝트 인덱싱 스크립트**

- **기능**:
  - 모든 Java 파일 자동 검색
  - AST 파싱을 통한 코드 분석
  - 메서드 레벨 청킹
  - Vector 인덱싱 + BM25 인덱싱
  - 상세한 로그 및 결과 저장

- **컬렉션명**: `springboot-sample-pjt`
- **청킹 전략**: `method_level`
- **청크 크기**: 1000 토큰
- **청크 오버랩**: 200 토큰

### `test_sample_indexing.py`

**빠른 테스트 스크립트**

- **기능**:
  - 주요 파일 5개만 선택적 인덱싱
  - 간단한 문서 생성 (AST 파싱 생략)
  - Vector 인덱싱 + BM25 인덱싱
  - 즉시 검색 테스트 실행

- **컬렉션명**: `springboot-sample-test`
- **테스트 파일들**:
  - BookController.java
  - BookService.java
  - BookDto.java
  - BookRepository.java
  - SpringbootSamplePjtApplication.java

### `run_indexing.sh`

**통합 실행 스크립트**

- **기능**:
  - 자동 환경 체크
  - RAG 서버 상태 확인
  - 의존성 패키지 설치
  - 인덱싱 실행 및 결과 요약

## 📊 인덱싱 결과

### 생성되는 파일들

1. **`indexing.log`**: 상세한 실행 로그
2. **`indexing_result_YYYYMMDD_HHMMSS.json`**: 인덱싱 결과 요약

### 결과 예시

```json
{
  "timestamp": "2024-06-13T18:45:00",
  "duration_seconds": 120.5,
  "project_path": "data/springboot-sample-pjt",
  "collection_name": "springboot-sample-pjt",
  "total_files": 51,
  "parsed_files": 48,
  "total_documents": 127,
  "vector_indexing_success": true,
  "bm25_indexing_success": true,
  "index_stats": {
    "vector_index_stats": {
      "collection_name": "springboot-sample-pjt",
      "points_count": 127,
      "vector_dimension": 768
    },
    "bm25_index_stats": {
      "index_name": "springboot-sample-pjt",
      "document_count": 127
    }
  }
}
```

## 🔍 인덱싱 후 검색 테스트

### Vector 검색

```bash
curl -X POST http://localhost:8000/api/v1/search/vector \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "BookController createBook 메서드",
    "collection_name": "springboot-sample-pjt",
    "top_k": 5
  }'
```

### BM25 검색

```bash
curl -X POST http://localhost:8000/api/v1/search/bm25 \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "BookController createBook",
    "collection_name": "springboot-sample-pjt",
    "top_k": 5
  }'
```

### 하이브리드 검색

```bash
curl -X POST http://localhost:8000/api/v1/search/hybrid \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "도서 생성 기능",
    "collection_name": "springboot-sample-pjt",
    "top_k": 5
  }'
```

## 🛠️ 트러블슈팅

### 1. RAG 서버 연결 실패

```
❌ RAG 서버가 응답하지 않습니다.
```

**해결방법**:
- RAG 서버가 실행 중인지 확인
- 포트 8000이 사용 가능한지 확인
- 방화벽 설정 확인

### 2. 프로젝트 경로 오류

```
❌ 프로젝트 경로가 존재하지 않습니다: data/springboot-sample-pjt
```

**해결방법**:
- 현재 디렉토리가 `codev-rag-server` 루트인지 확인
- `data/springboot-sample-pjt` 디렉토리 존재 여부 확인

### 3. 파싱 실패

```
❌ 파싱된 AST 정보가 없습니다.
```

**해결방법**:
- Java 파일 문법 오류 확인
- 파일 인코딩이 UTF-8인지 확인
- 빠른 테스트 스크립트로 우선 테스트

### 4. 인덱싱 실패

```
❌ Vector 인덱싱 실패: ...
```

**해결방법**:
- Embedding 서버 상태 확인
- Vector DB (Qdrant) 상태 확인
- 메모리 사용량 확인

## 📈 성능 최적화

### 대용량 프로젝트의 경우

1. **배치 처리**: 파일을 작은 그룹으로 나누어 처리
2. **병렬 처리**: asyncio를 활용한 비동기 처리
3. **청킹 조정**: chunk_size 및 overlap 조정
4. **메모리 관리**: 대용량 파일 스트리밍 처리

### 검색 성능 향상

1. **인덱스 최적화**: Vector dimension 조정
2. **캐싱**: 자주 사용되는 검색어 캐싱
3. **하이브리드 가중치**: Vector와 BM25 비율 조정

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. **로그 파일**: `indexing.log`
2. **RAG 서버 로그**: 서버 실행 로그 확인
3. **시스템 리소스**: CPU, 메모리 사용량
4. **네트워크 연결**: 서비스 간 통신 상태

---

**마지막 업데이트**: 2024-06-13 