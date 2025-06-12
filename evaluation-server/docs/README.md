# RAG 성능 평가 서비스 문서

## 📁 문서 구조

```
docs/
├── README.md                    ← 이 파일
├── prd/                         ← 제품 요구사항 문서
│   └── rag-evaluation-service-prd.md
└── tasks/                       ← 개발 태스크 문서
    ├── phase1-basic-evaluation.md
    ├── phase2-advanced-features.md
    └── phase3-system-comparison.md
```

## 📋 개발 단계

### Phase 1: 기본 평가 기능 (MVP)
- **목표**: RAG 시스템 평가 기본 기능 구현
- **소요 시간**: 약 3.5일 (28시간)
- **주요 기능**:
  - RAG 시스템 인터페이스
  - 기본 메트릭 (Recall@K, Precision@K, Hit@K)
  - 단일 데이터셋 평가
  - 평가 결과 저장

### Phase 2: 확장 기능
- **목표**: NDCG 메트릭, 다중 데이터셋, 베이스라인 비교
- **소요 시간**: 약 2일 (17시간)
- **주요 기능**:
  - NDCG 메트릭 추가
  - 다중 데이터셋 지원
  - 베이스라인 등록 및 비교

### Phase 3: 고급 기능
- **목표**: 시스템 비교, 배치 평가, 고급 분석
- **소요 시간**: 약 3일 (22시간)
- **주요 기능**:
  - 시스템 간 성능 비교
  - API를 통한 동적 시스템 등록
  - 배치 평가 기능

## 🏗️ 아키텍처 개요

### 서비스 구조
```
evaluation-server/
├── app/
│   ├── features/           ← 기능별 모듈
│   │   ├── systems/        ← RAG 시스템 관리
│   │   ├── datasets/       ← 테스트 데이터셋 관리
│   │   ├── evaluations/    ← 평가 실행 및 결과
│   │   ├── metrics/        ← 평가 메트릭
│   │   ├── baselines/      ← 베이스라인 관리
│   │   └── comparisons/    ← 시스템 간 비교
│   ├── core/               ← 공통 설정 및 유틸리티
│   └── db/                 ← 데이터베이스 설정
├── datasets/               ← 테스트 데이터셋 파일
├── tests/                  ← 테스트 코드
└── docs/                   ← 문서 (이 폴더)
```

### 핵심 컴포넌트
1. **RAG 시스템 인터페이스**: 다양한 RAG 시스템과의 통신
2. **메트릭 엔진**: 평가 메트릭 계산
3. **데이터셋 관리자**: 테스트 데이터 로딩 및 관리
4. **평가 엔진**: 평가 실행 및 결과 처리
5. **비교 분석기**: 시스템 간 성능 비교

## 🎯 개발 원칙

### TDD (Test-Driven Development)
- **모든 코드는 테스트가 먼저 작성되어야 함**
- Red-Green-Refactor 사이클 엄수
- 단위 테스트 커버리지 90% 이상 목표

### 마이크로서비스 아키텍처
- 다른 서비스와 독립적으로 배포 가능
- HTTP API를 통한 서비스 간 통신
- Docker 컨테이너 기반 실행

### 확장성 고려
- 새로운 메트릭 추가 용이성
- 다양한 RAG 시스템 지원
- 대용량 데이터셋 처리 가능

## 📖 문서 읽는 순서

1. **[PRD 문서](prd/rag-evaluation-service-prd.md)** - 전체 요구사항 및 설계 이해
2. **[Phase 1 태스크](tasks/phase1-basic-evaluation.md)** - 기본 기능 구현
3. **[Phase 2 태스크](tasks/phase2-advanced-features.md)** - 확장 기능 구현
4. **[Phase 3 태스크](tasks/phase3-system-comparison.md)** - 고급 기능 구현

## 🚀 시작하기

### 개발 환경 설정
```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp env.example .env

# 4. 개발 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8003
```

### Docker로 실행
```bash
# 이미지 빌드
docker build -t evaluation-server .

# 컨테이너 실행
docker run -p 8003:8003 evaluation-server
```

## 🧪 테스트

### 단위 테스트 실행
```bash
pytest tests/unit/ -v --cov=app
```

### 통합 테스트 실행
```bash
pytest tests/integration/ -v
```

### 전체 테스트 실행
```bash
pytest -v --cov=app --cov-report=html
```

## 📊 메트릭 및 성능 목표

### 기능적 지표
- 평가 실행 성공률 > 99%
- 메트릭 계산 정확도 100%
- API 응답 시간 < 5초

### 기술적 지표
- 테스트 커버리지 > 90%
- 코드 품질 A등급 (SonarQube 기준)
- 동시 평가 요청 처리 > 10개

## 🔗 관련 링크

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/)
- [Pytest 문서](https://docs.pytest.org/)
- [Docker 문서](https://docs.docker.com/)

---

**문서 업데이트**: 개발 진행에 따라 이 문서들을 지속적으로 업데이트해주세요. 