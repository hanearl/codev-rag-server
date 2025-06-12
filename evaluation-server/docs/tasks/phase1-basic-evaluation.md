# Phase 1: 기본 평가 기능 개발 태스크

## 📋 개요
RAG 성능 평가 서비스의 MVP를 구현하기 위한 기본 평가 기능을 개발합니다.

## 🎯 목표
- RAG 시스템 인터페이스 구현
- 기본 메트릭 계산 (Recall@K, Precision@K, Hit@K)
- 단일 데이터셋 평가
- 평가 결과 저장

## 📝 상세 태스크

### Task 1.1: 프로젝트 기본 구조 설정
**담당자**: 개발자  
**예상 소요 시간**: 2시간  
**우선순위**: High  

#### 작업 내용
- [ ] FastAPI 애플리케이션 기본 구조 생성
- [ ] Docker 설정 파일 생성
- [ ] requirements.txt 작성
- [ ] 기본 설정 파일 구현

#### 세부 작업
1. **FastAPI 메인 애플리케이션 구현**
   ```python
   # app/main.py
   from fastapi import FastAPI
   
   app = FastAPI(
       title="RAG Evaluation API",
       description="RAG 시스템 성능 평가 서비스",
       version="1.0.0"
   )
   ```

2. **기본 설정 클래스 구현**
   ```python
   # app/core/config.py
   from pydantic import BaseSettings
   
   class Settings(BaseSettings):
       HOST: str = "0.0.0.0"
       PORT: int = 8003
       DATABASE_URL: str
       DATASETS_PATH: str = "./datasets"
   ```

3. **Docker 설정**
   ```dockerfile
   # Dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY app/ ./app/
   EXPOSE 8003
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
   ```

4. **requirements.txt 작성**
   ```
   fastapi==0.104.1
   uvicorn==0.24.0
   pydantic==2.5.0
   sqlalchemy==2.0.23
   psycopg2-binary==2.9.9
   httpx==0.25.2
   numpy==1.24.3
   scikit-learn==1.3.2
   pytest==7.4.3
   pytest-asyncio==0.21.1
   ```

#### 완료 조건
- [ ] FastAPI 애플리케이션이 정상적으로 실행됨
- [ ] Docker 컨테이너 빌드 및 실행 성공
- [ ] 기본 헬스체크 엔드포인트 응답

---

### Task 1.2: 데이터베이스 설정 및 모델 구현
**담당자**: 개발자  
**예상 소요 시간**: 3시간  
**우선순위**: High  

#### 작업 내용
- [ ] SQLAlchemy 데이터베이스 설정
- [ ] 핵심 데이터 모델 구현
- [ ] Alembic 마이그레이션 설정

#### 세부 작업
1. **데이터베이스 연결 설정**
   ```python
   # app/db/database.py
   from sqlalchemy import create_engine
   from sqlalchemy.ext.declarative import declarative_base
   from sqlalchemy.orm import sessionmaker
   
   Base = declarative_base()
   
   def get_db():
       # 데이터베이스 세션 의존성
       pass
   ```

2. **RAG 시스템 모델**
   ```python
   # app/features/systems/model.py
   class RAGSystem(Base):
       __tablename__ = "rag_systems"
       
       id: int
       name: str
       description: str
       base_url: str
       api_key: str (optional)
       system_type: str
       config: dict
   ```

3. **평가 결과 모델**
   ```python
   # app/features/evaluations/model.py
   class EvaluationResult(Base):
       __tablename__ = "evaluation_results"
       
       id: int
       system_id: int
       dataset_id: str
       metrics: dict
       execution_time: float
       created_at: datetime
       config: dict
   ```

#### 완료 조건
- [ ] 데이터베이스 연결 성공
- [ ] 모든 테이블 생성 성공
- [ ] 마이그레이션 파일 생성

---

### Task 1.3: RAG 시스템 인터페이스 구현
**담당자**: 개발자  
**예상 소요 시간**: 4시간  
**우선순위**: High  

#### 작업 내용
- [ ] RAG 시스템 추상 인터페이스 정의
- [ ] HTTP 기반 RAG 시스템 클라이언트 구현
- [ ] 테스트용 Mock RAG 시스템 구현

#### 세부 작업
1. **RAG 시스템 인터페이스 정의**
   ```python
   # app/features/systems/interface.py
   from abc import ABC, abstractmethod
   from typing import List
   
   class RAGSystemInterface(ABC):
       @abstractmethod
       async def embed_query(self, query: str) -> List[float]:
           pass
       
       @abstractmethod
       async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
           pass
   ```

2. **HTTP RAG 시스템 클라이언트**
   ```python
   # app/features/systems/http_client.py
   class HTTPRAGSystem(RAGSystemInterface):
       def __init__(self, base_url: str, api_key: str = None):
           self.base_url = base_url
           self.api_key = api_key
           
       async def embed_query(self, query: str) -> List[float]:
           # HTTP API 호출 구현
           pass
           
       async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
           # HTTP API 호출 구현
           pass
   ```

3. **Mock RAG 시스템 (테스트용)**
   ```python
   # app/features/systems/mock_client.py
   class MockRAGSystem(RAGSystemInterface):
       async def embed_query(self, query: str) -> List[float]:
           # 더미 임베딩 반환
           return [0.1] * 768
           
       async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
           # 더미 검색 결과 반환
           pass
   ```

#### 완료 조건
- [ ] 인터페이스 정의 완료
- [ ] HTTP 클라이언트 구현 및 테스트 통과
- [ ] Mock 시스템 구현 및 테스트 통과

---

### Task 1.4: 테스트 데이터셋 관리 구현
**담당자**: 개발자  
**예상 소요 시간**: 3시간  
**우선순위**: High  

#### 작업 내용
- [ ] 테스트 데이터셋 인터페이스 정의
- [ ] JSONL 파일 기반 데이터셋 로더 구현
- [ ] 샘플 테스트 데이터셋 생성

#### 세부 작업
1. **데이터셋 인터페이스 정의**
   ```python
   # app/features/datasets/interface.py
   from abc import ABC, abstractmethod
   
   class TestDatasetInterface(ABC):
       @abstractmethod
       def load_dataset(self) -> TestDataset:
           pass
           
       @abstractmethod
       def get_queries(self) -> List[Query]:
           pass
           
       @abstractmethod
       def get_ground_truth(self, query_id: str) -> List[str]:
           pass
   ```

2. **JSONL 데이터셋 로더**
   ```python
   # app/features/datasets/jsonl_loader.py
   class JSONLDatasetLoader(TestDatasetInterface):
       def __init__(self, dataset_path: str):
           self.dataset_path = dataset_path
           
       def load_dataset(self) -> TestDataset:
           # metadata.json 파일 읽기
           pass
           
       def get_queries(self) -> List[Query]:
           # queries.jsonl 파일 읽기
           pass
           
       def get_ground_truth(self, query_id: str) -> List[str]:
           # ground_truth.jsonl 파일에서 해당 쿼리의 정답 반환
           pass
   ```

3. **샘플 데이터셋 생성**
   ```
   datasets/
   └── sample-dataset/
       ├── metadata.json
       ├── queries.jsonl
       └── ground_truth.jsonl
   ```

#### 완료 조건
- [ ] 데이터셋 인터페이스 정의 완료
- [ ] JSONL 로더 구현 및 테스트 통과
- [ ] 샘플 데이터셋으로 정상 로딩 확인

---

### Task 1.5: 평가 메트릭 구현
**담당자**: 개발자  
**예상 소요 시간**: 4시간  
**우선순위**: High  

#### 작업 내용
- [ ] 기본 평가 메트릭 구현 (Recall@K, Precision@K, Hit@K)
- [ ] 메트릭 계산기 클래스 구현
- [ ] 메트릭 검증 테스트 작성

#### 세부 작업
1. **메트릭 계산기 인터페이스**
   ```python
   # app/features/metrics/interface.py
   from abc import ABC, abstractmethod
   
   class MetricCalculator(ABC):
       @abstractmethod
       def calculate(self, predictions: List[str], ground_truth: List[str], k: int) -> float:
           pass
   ```

2. **기본 메트릭 구현**
   ```python
   # app/features/metrics/basic_metrics.py
   class RecallAtK(MetricCalculator):
       def calculate(self, predictions: List[str], ground_truth: List[str], k: int) -> float:
           # Recall@K 계산 로직
           pass
   
   class PrecisionAtK(MetricCalculator):
       def calculate(self, predictions: List[str], ground_truth: List[str], k: int) -> float:
           # Precision@K 계산 로직
           pass
   
   class HitAtK(MetricCalculator):
       def calculate(self, predictions: List[str], ground_truth: List[str], k: int) -> float:
           # Hit@K 계산 로직 (0 또는 1)
           pass
   ```

3. **메트릭 매니저**
   ```python
   # app/features/metrics/manager.py
   class MetricsManager:
       def __init__(self):
           self.metrics = {
               'recall': RecallAtK(),
               'precision': PrecisionAtK(),
               'hit': HitAtK()
           }
           
       def calculate_all(self, predictions: List[str], ground_truth: List[str], k_values: List[int]) -> dict:
           # 모든 메트릭에 대해 K값별로 계산
           pass
   ```

#### 완료 조건
- [ ] 모든 기본 메트릭 구현 완료
- [ ] 메트릭 계산 정확성 테스트 통과
- [ ] 매니저 클래스 구현 및 테스트 통과

---

### Task 1.6: 평가 실행 서비스 구현
**담당자**: 개발자  
**예상 소요 시간**: 5시간  
**우선순위**: High  

#### 작업 내용
- [ ] 평가 실행 서비스 구현
- [ ] 평가 결과 저장 로직 구현
- [ ] 비동기 평가 처리

#### 세부 작업
1. **평가 서비스 구현**
   ```python
   # app/features/evaluations/service.py
   class EvaluationService:
       def __init__(self, metrics_manager: MetricsManager):
           self.metrics_manager = metrics_manager
           
       async def run_evaluation(
           self,
           rag_system: RAGSystemInterface,
           dataset: TestDatasetInterface,
           config: EvaluationConfig
       ) -> EvaluationResult:
           # 평가 실행 로직
           pass
           
       async def evaluate_single_query(
           self,
           rag_system: RAGSystemInterface,
           query: str,
           ground_truth: List[str],
           k: int
       ) -> dict:
           # 단일 쿼리 평가
           pass
   ```

2. **평가 설정 스키마**
   ```python
   # app/features/evaluations/schema.py
   class EvaluationConfig(BaseModel):
       k_values: List[int] = [1, 3, 5, 10]
       metrics: List[str] = ['recall', 'precision', 'hit']
       
   class EvaluationRequest(BaseModel):
       system_id: int
       dataset_id: str
       config: EvaluationConfig
   ```

3. **결과 저장 로직**
   ```python
   # app/features/evaluations/repository.py
   class EvaluationRepository:
       def save_result(self, evaluation_result: EvaluationResult) -> int:
           # 평가 결과 데이터베이스 저장
           pass
           
       def get_result(self, evaluation_id: int) -> EvaluationResult:
           # 평가 결과 조회
           pass
   ```

#### 완료 조건
- [ ] 평가 서비스 구현 완료
- [ ] 평가 결과 저장 및 조회 기능 동작
- [ ] 단위 테스트 및 통합 테스트 통과

---

### Task 1.7: API 엔드포인트 구현
**담당자**: 개발자  
**예상 소요 시간**: 4시간  
**우선순위**: High  

#### 작업 내용
- [ ] 평가 실행 API 구현
- [ ] 평가 결과 조회 API 구현
- [ ] 시스템 관리 API 구현

#### 세부 작업
1. **평가 라우터 구현**
   ```python
   # app/features/evaluations/router.py
   @router.post("/run", response_model=EvaluationResponse)
   async def run_evaluation(request: EvaluationRequest):
       # 평가 실행
       pass
       
   @router.get("/{evaluation_id}", response_model=EvaluationResponse)
   async def get_evaluation(evaluation_id: int):
       # 평가 결과 조회
       pass
       
   @router.get("/", response_model=List[EvaluationResponse])
   async def list_evaluations():
       # 평가 이력 조회
       pass
   ```

2. **시스템 관리 라우터**
   ```python
   # app/features/systems/router.py
   @router.post("/", response_model=SystemResponse)
   async def create_system(request: SystemCreateRequest):
       # RAG 시스템 등록
       pass
       
   @router.get("/", response_model=List[SystemResponse])
   async def list_systems():
       # 등록된 시스템 목록
       pass
   ```

3. **데이터셋 라우터**
   ```python
   # app/features/datasets/router.py
   @router.get("/", response_model=List[DatasetResponse])
   async def list_datasets():
       # 사용 가능한 데이터셋 목록
       pass
       
   @router.get("/{dataset_id}", response_model=DatasetResponse)
   async def get_dataset(dataset_id: str):
       # 데이터셋 상세 정보
       pass
   ```

#### 완료 조건
- [ ] 모든 API 엔드포인트 구현 완료
- [ ] API 문서 자동 생성 확인
- [ ] Postman/curl 테스트 성공

---

### Task 1.8: 통합 테스트 및 문서화
**담당자**: 개발자  
**예상 소요 시간**: 3시간  
**우선순위**: Medium  

#### 작업 내용
- [ ] End-to-End 테스트 작성
- [ ] API 문서 보완
- [ ] 샘플 사용 예시 작성

#### 세부 작업
1. **E2E 테스트 시나리오**
   - 시스템 등록 → 데이터셋 로딩 → 평가 실행 → 결과 조회

2. **API 문서 보완**
   - 각 엔드포인트별 상세 설명
   - 요청/응답 예시
   - 에러 코드 설명

3. **사용 예시 작성**
   ```python
   # 샘플 평가 실행 코드
   import httpx
   
   # 시스템 등록
   system_data = {
       "name": "Test RAG System",
       "base_url": "http://localhost:8001",
       "system_type": "external"
   }
   
   # 평가 실행
   evaluation_data = {
       "system_id": 1,
       "dataset_id": "sample-dataset",
       "config": {
           "k_values": [1, 3, 5],
           "metrics": ["recall", "precision", "hit"]
       }
   }
   ```

#### 완료 조건
- [ ] E2E 테스트 시나리오 통과
- [ ] API 문서 완성
- [ ] 사용 예시 동작 확인

## 🎯 Phase 1 완료 조건

### 기능적 요구사항
- [ ] RAG 시스템을 등록하고 평가를 실행할 수 있음
- [ ] 기본 메트릭(Recall@K, Precision@K, Hit@K)이 정확하게 계산됨
- [ ] 평가 결과가 데이터베이스에 저장되고 조회 가능함
- [ ] 샘플 데이터셋으로 전체 워크플로우 동작 확인

### 기술적 요구사항
- [ ] TDD 방식으로 모든 코드 작성
- [ ] 단위 테스트 커버리지 90% 이상
- [ ] Docker 컨테이너로 정상 실행
- [ ] API 문서 자동 생성

### 성능 요구사항
- [ ] 100개 쿼리 평가가 30초 이내 완료
- [ ] API 응답 시간 5초 이내
- [ ] 메모리 사용량 1GB 이내

## 📅 예상 일정
**총 소요 시간**: 28시간 (약 3.5일)

1. **Day 1**: Task 1.1, 1.2 (프로젝트 설정, DB 모델)
2. **Day 2**: Task 1.3, 1.4 (인터페이스, 데이터셋)
3. **Day 3**: Task 1.5, 1.6 (메트릭, 평가 서비스)
4. **Day 4**: Task 1.7, 1.8 (API, 테스트) 