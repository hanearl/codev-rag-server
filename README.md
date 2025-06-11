# RAG 기반 코드 검색 시스템

TDD 방법론을 적용하여 개발된 마이크로서비스 기반의 RAG(Retrieval-Augmented Generation) 코드 검색 시스템입니다.

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Embedding     │    │   LLM Server    │    │   Vector DB     │
│   Server        │    │   (vLLM 호환)   │    │   (Qdrant)      │
│   :8001         │    │   :8002         │    │   :6333         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   RAG Server    │
                    │   (구현 예정)    │
                    │   :8000         │
                    └─────────────────┘
```

## 📁 프로젝트 구조

```
├── embedding-server/        # 텍스트 임베딩 서비스
│   ├── app/
│   │   ├── features/embedding/
│   │   ├── core/
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── llm-server/             # LLM 프록시 서비스
│   ├── app/
│   │   ├── features/llm/
│   │   ├── core/
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── vector-db/              # 벡터 데이터베이스 설정
│   ├── config/
│   ├── scripts/
│   ├── tests/
│   └── docker-compose.yml
├── rag-server/             # RAG 메인 서비스 (구현 예정)
├── tests/integration/      # 통합 테스트
├── scripts/               # 개발 스크립트
├── docker-compose.yml     # 전체 시스템 구성
├── docker-compose.dev.yml # 개발 환경 구성
└── Makefile              # 개발 편의 명령어
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 환경 변수 파일 생성
cp env.example .env

# .env 파일을 편집하여 OpenAI API 키 설정
# OPENAI_API_KEY=your_openai_api_key_here
```

### 2. 개발 환경 시작

```bash
# 자동 설정 스크립트 실행
./scripts/setup-dev.sh

# 또는 수동으로
make setup-dev
```

### 3. 서비스 확인

```bash
# 헬스체크
make health

# 개별 서비스 확인
curl http://localhost:6333/health    # Vector DB
curl http://localhost:8001/health    # Embedding Server  
curl http://localhost:8002/health    # LLM Server
```

## 🔧 개발 명령어

```bash
# 서비스 관리
make up              # 개발 환경 시작
make down            # 개발 환경 중지
make restart         # 전체 재시작
make logs            # 모든 서비스 로그
make logs-embedding  # Embedding Server 로그
make logs-llm        # LLM Server 로그
make logs-vector     # Vector DB 로그

# 테스트
make test            # 모든 테스트 실행
make test-integration # 통합 테스트만 실행

# 데이터베이스
make init-db         # Vector DB 컬렉션 초기화
make backup          # 데이터 백업

# 정리
make clean           # 환경 정리 (볼륨 포함)
```

## 🧪 서비스별 테스트

### Embedding Server 테스트
```bash
# 단일 텍스트 임베딩
curl -X POST http://localhost:8001/embedding/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "def hello_world():\n    print(\"Hello, World!\")"}'

# 벌크 임베딩
curl -X POST http://localhost:8001/embedding/embed/bulk \
  -H "Content-Type: application/json" \
  -d '{"texts": ["def func1():\n    pass", "class MyClass:\n    pass"]}'
```

### LLM Server 테스트
```bash
# 채팅 완성 (vLLM 호환)
curl -X POST http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Write a Python function"}],
    "max_tokens": 100
  }'

# 모델 목록
curl http://localhost:8002/v1/models
```

### Vector DB 테스트
```bash
# 컬렉션 목록
curl http://localhost:6333/collections

# 컬렉션 정보
curl http://localhost:6333/collections/code_embeddings
```

## 📊 모니터링 및 대시보드

- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **API 문서**:
  - Embedding Server: http://localhost:8001/docs
  - LLM Server: http://localhost:8002/docs

## 🏗️ 구현된 기능 (Task 1-4)

### ✅ Task 1: Embedding Server
- HuggingFace sentence-transformers 기반 임베딩 생성
- 단일/벌크 텍스트 임베딩 API
- FastAPI 기반 RESTful API
- Docker 컨테이너화

### ✅ Task 2: LLM Server  
- vLLM 호환 API 인터페이스
- OpenAI API 프록시 기능
- gpt-4o-mini 모델 지원
- 채팅 완성 및 텍스트 생성 API

### ✅ Task 3: Vector DB
- Qdrant 벡터 데이터베이스 구성
- 코드 임베딩 저장 스키마
- 키워드 인덱스 및 필터링 지원
- 백업/복원 기능

### ✅ Task 4: Docker Compose 통합
- 마이크로서비스 통합 환경
- 개발/프로덕션 환경 분리
- 서비스 간 네트워킹 및 의존성 관리
- 헬스체크 및 모니터링

## 🔄 다음 단계 (Task 5-6)

- **Task 5-A**: RAG Server 코드 파서 구현
- **Task 5-B**: 외부 클라이언트 연동
- **Task 5-C**: 인덱싱 서비스 구현  
- **Task 5-D**: 검색 및 생성 기능
- **Task 6**: 통합 검증 및 최적화

## 🛠️ 기술 스택

- **웹 프레임워크**: FastAPI
- **임베딩**: sentence-transformers (all-MiniLM-L6-v2)
- **LLM**: OpenAI GPT-4o-mini
- **벡터 DB**: Qdrant
- **컨테이너**: Docker, Docker Compose
- **테스트**: pytest, httpx
- **개발 도구**: TDD, 타입 힌트, 의존성 주입

## 📝 개발 규칙

### TDD 원칙
1. **Red**: 실패하는 테스트를 먼저 작성
2. **Green**: 테스트를 통과하는 최소한의 코드 작성  
3. **Refactor**: 코드를 개선하고 중복 제거

### 아키텍처 규칙
- 모든 비즈니스 기능은 `features/` 하위에 위치
- 마이크로서비스 간 HTTP 통신
- 의존성 주입 패턴 사용
- 타입 힌트 필수 사용

### 테스트 규칙
- 단위 테스트, 통합 테스트 분리
- Given-When-Then 패턴 사용
- 한글로 테스트 목적 설명
- Docker 환경에서 통합 테스트 실행

## 🔧 문제 해결

### 서비스 시작 실패
```bash
# 로그 확인
make logs

# 개별 서비스 로그
make logs-embedding
make logs-llm  
make logs-vector

# 환경 정리 후 재시작
make clean
make up
```

### 포트 충돌
```bash
# 포트 사용 확인
lsof -i :6333  # Qdrant
lsof -i :8001  # Embedding Server
lsof -i :8002  # LLM Server
```

### 환경 변수 문제
```bash
# .env 파일 확인
cat .env

# 환경 변수 예제 참고
cat env.example
```

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 