# 코드 어시스턴트 마이크로서비스 MVP 개발 태스크

본 문서는 마이크로서비스 아키텍처 기반 코드 어시스턴트 시스템 MVP 개발을 위한 태스크 분할 계획입니다.

## 🎯 전체 목표
Docker Compose 기반 마이크로서비스로 구성된 AI 코드 검색 및 생성 시스템 MVP를 구축하여 핵심 기능을 검증합니다.

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RAG Server    │    │ Embedding Server│    │   LLM Server    │
│   (Port: 8000)  │    │   (Port: 8001)  │    │   (Port: 8002)  │
│                 │    │                 │    │                 │
│ - 코드 인덱싱    │◄───┤ - HuggingFace   │    │ - vLLM Interface│
│ - 검색 & 생성   │    │   임베딩 모델    │    │ - OpenAI API    │
│ - API 통합      │    │ - Bulk 임베딩   │    │ - gpt-4o-mini   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                                │
         │              ┌─────────────────┐              │
         └──────────────►│   Vector DB     │◄─────────────┘
                        │   (Port: 6333)  │
                        │                 │
                        │ - Qdrant        │
                        │ - Keyword Index │
                        └─────────────────┘
```

## 🛠️ 개발 원칙

- **TDD 필수**: 모든 구현은 테스트 우선 개발로 진행
- **모듈화**: FastAPI features 구조 기반 모듈 단위 개발
- **컨테이너화**: Docker Compose 기반 마이크로서비스 구성
- **개발 편의성**: 소스코드 변경 시 실시간 반영 (volume mount)

---

## 📋 태스크 목록

### [Task 01: Embedding Server 구현](./task-01-embedding-server.md)
**목표**: HuggingFace 기반 임베딩 서비스 구현  
**기간**: 3일  
**핵심 기능**: 
- HuggingFace 임베딩 모델 서빙
- 단일/벌크 임베딩 API 제공
- FastAPI 기반 RESTful API
- TDD 기반 개발

### [Task 02: LLM Server 구현](./task-02-llm-server.md)
**목표**: vLLM 인터페이스 기반 LLM 서비스 구현  
**기간**: 3일  
**핵심 기능**: 
- vLLM 호환 API 인터페이스
- OpenAI API 프록시 구현
- gpt-4o-mini 기본 모델
- TDD 기반 개발

### [Task 03: Vector DB 구성](./task-03-vector-db.md)
**목표**: Qdrant 기반 벡터 데이터베이스 구성  
**기간**: 2일  
**핵심 기능**: 
- Qdrant 컨테이너 설정
- 벡터 스토리지 스키마 설계
- 키워드 인덱스 통합
- 데이터 백업/복원

### [Task 04: Docker Compose 통합](./task-04-docker-integration.md)
**목표**: 전체 시스템 컨테이너화 및 서비스 간 통신 구성  
**기간**: 2일  
**핵심 기능**: 
- Docker Compose 설정
- 서비스 간 통신 구성
- 개발 환경 최적화
- 기본 E2E 테스트 환경 구성

### [Task 05: RAG Server 구현](./task-05-rag-server.md) ⚠️ **분할됨**
**목표**: 코드 인덱싱, 검색, 생성 통합 서비스 구현  
**기간**: 8일 (4개 서브태스크로 분할)  
**서브태스크**:
- [Task 05-A: 코드 파서 구현 (1.5일)](./task-05-a-code-parser.md)
- [Task 05-B: 외부 서비스 클라이언트 (2일)](./task-05-b-external-clients.md)
- [Task 05-C: 인덱싱 서비스 (2일)](./task-05-c-indexing-service.md)
- [Task 05-D: 검색/생성 서비스 (2.5일)](./task-05-d-search-generation.md)

**핵심 기능**: 
- 코드 인덱싱 모듈
- 하이브리드 검색 모듈
- 코드 생성 모듈
- 통합 API 제공
- TDD 기반 개발

### [Task 06: 전체 시스템 통합 테스트 및 검증](./task-06-integration-verification.md)
**목표**: 전체 시스템 성능, 안정성, 운영 준비성 검증  
**기간**: 4일  
**핵심 기능**: 
- 전체 시스템 E2E 테스트 프레임워크
- 성능 및 부하 테스트 (Locust, k6)
- 장애 복구 테스트 시나리오
- 운영 환경 배포 준비 (모니터링, 알림)

---

## 🐳 Docker Compose 구성

```yaml
version: '3.8'
services:
  rag-server:
    build: ./rag-server
    ports:
      - "8000:8000"
    volumes:
      - ./rag-server:/app
    depends_on:
      - embedding-server
      - llm-server
      - vector-db

  embedding-server:
    build: ./embedding-server
    ports:
      - "8001:8001"
    volumes:
      - ./embedding-server:/app

  llm-server:
    build: ./llm-server
    ports:
      - "8002:8002"
    volumes:
      - ./llm-server:/app

  vector-db:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - ./data/qdrant:/qdrant/storage
```

## 🏭 모듈 구조

각 서비스는 다음 구조를 따릅니다:

```
<service>/
├── app/
│   ├── features/           ← 비즈니스 기능 모듈
│   │   ├── embedding/      ← 임베딩 관련 기능
│   │   ├── search/         ← 검색 관련 기능
│   │   └── generation/     ← 코드 생성 관련 기능
│   ├── core/              ← 공통 설정 및 의존성
│   ├── db/                ← 데이터베이스 관련
│   └── main.py            ← FastAPI 애플리케이션
├── tests/
│   ├── unit/              ← 단위 테스트
│   ├── integration/       ← 통합 테스트
│   └── conftest.py        ← 테스트 설정
├── Dockerfile
└── requirements.txt
```

## 🧪 TDD 개발 순서

각 태스크는 다음 순서로 진행합니다:

1. **🔴 Red**: 실패하는 테스트 작성
2. **🟢 Green**: 테스트 통과하는 최소 구현
3. **🔵 Refactor**: 코드 개선 및 리팩토링
4. **🔄 반복**: 다음 기능으로 이동

## ⏰ 전체 개발 일정

| Week | Task | 기간 | 담당자 | 핵심 활동 |
|------|------|------|--------|-----------|
| 1주차 | Task 01-03 | 8일 | Backend Dev + ML Engineer | 기본 마이크로서비스 구축 |
| 2주차 | Task 04-A,B | 3.5일 | Backend Developer | RAG 서버 기반 모듈 |
| 2주차 | Task 04-C,D | 4.5일 | Backend Dev + ML Engineer | RAG 서버 완성 |
| 3주차 | Task 05 | 2일 | DevOps + Backend | 통합 및 컨테이너화 |
| 3-4주차 | Task 06 | 4일 | Full Team | 최종 검증 및 운영 준비 |

**총 개발 기간**: 21일 (3-4주)

## 🧪 통합 테스트 전략

### 각 Task별 Integration 테스트
- **Task 01-03**: 각 서비스별 독립적 integration 테스트
- **Task 04-B**: 외부 서비스 연동 integration 테스트  
- **Task 04-C**: 인덱싱 파이프라인 End-to-End 테스트
- **Task 04-D**: 완전한 RAG 워크플로우 integration 테스트
- **Task 05**: 전체 시스템 E2E 테스트
- **Task 06**: 성능, 안정성, 운영 준비성 종합 검증

## 📊 성공 기준

### 기능적 요구사항
- [ ] 코드 파일을 성공적으로 임베딩하여 벡터 DB에 저장
- [ ] 자연어 질의로 관련 코드 검색 가능
- [ ] 검색 결과 기반 코드 생성 가능
- [ ] 모든 서비스가 독립적으로 실행 가능
- [ ] 서비스 간 통신이 정상적으로 작동

### 비기능적 요구사항
- [ ] 각 서비스별 90% 이상 테스트 커버리지
- [ ] 소스코드 변경 시 실시간 반영
- [ ] 서비스 재시작 없이 개발 가능
- [ ] API 응답 시간: 검색 < 5초, 생성 < 60초
- [ ] 동시 처리: 검색 100 RPS, 생성 10 RPS

### 개발 품질
- [ ] TDD 사이클 준수
- [ ] 모듈별 단위 테스트 완료
- [ ] 각 단계별 integration 테스트 완료
- [ ] 전체 시스템 E2E 테스트 완료
- [ ] 성능 및 부하 테스트 완료
- [ ] 운영 준비성 검증 완료
- [ ] API 문서 자동 생성

### 운영 준비성
- [ ] 모니터링 시스템 구축 (Prometheus, Grafana)
- [ ] 로그 수집 및 분석 시스템
- [ ] 헬스체크 및 알림 시스템
- [ ] 장애 복구 시나리오 검증
- [ ] 운영 가이드 및 매뉴얼 작성

---

## 🚀 개발 환경 설정

### 1. 환경 변수 설정
```bash
# .env 파일
OPENAI_API_KEY=your-api-key-here
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
QDRANT_HOST=vector-db
QDRANT_PORT=6333
```

### 2. 개발 서버 실행
```bash
# 전체 서비스 실행
docker-compose up -d

# 개별 서비스 실행
docker-compose up rag-server
docker-compose up embedding-server
docker-compose up llm-server
```

### 3. 테스트 실행
```bash
# 각 서비스별 테스트
docker-compose exec rag-server pytest
docker-compose exec embedding-server pytest
docker-compose exec llm-server pytest
```

---

## 📚 참고 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Qdrant 문서](https://qdrant.tech/documentation/)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers)
- [vLLM 문서](https://docs.vllm.ai/)
- [Docker Compose 문서](https://docs.docker.com/compose/)

**총 예상 기간**: 3-4주 