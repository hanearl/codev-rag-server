# RAG 성능 평가 서비스 PRD

## 📋 프로덕트 개요

### 목적
RAG(Retrieval-Augmented Generation) 시스템의 성능을 체계적으로 평가하고 비교할 수 있는 마이크로서비스를 개발합니다.

### 핵심 가치
- 다양한 RAG 시스템의 성능을 객관적으로 평가
- 표준화된 평가 메트릭을 통한 일관된 성능 측정
- 시스템 간 성능 비교 및 베이스라인 관리
- 확장 가능한 테스트 데이터셋 관리

## 🎯 비즈니스 요구사항

### 핵심 기능
1. **다중 RAG 시스템 지원**: 표준 인터페이스를 통한 여러 RAG 시스템 평가
2. **Retrieval 성능 평가**: NDCG, Recall@K, Precision@K, Hit@K 등 핵심 메트릭 지원
3. **테스트 데이터셋 관리**: 폴더 기반 데이터셋 관리 및 확장성
4. **결과 저장 및 관리**: 평가 결과의 영구 저장 및 조회
5. **베이스라인 비교**: 기준점 설정 및 성능 변화 추적
6. **시스템 간 비교**: 서로 다른 RAG 시스템 간 성능 비교

### 사용자 스토리
- **데이터 사이언티스트**: "새로운 RAG 모델의 retrieval 성능을 기존 베이스라인과 비교하고 싶습니다"
- **ML 엔지니어**: "여러 테스트 데이터셋에서 RAG 시스템의 성능을 일괄 평가하고 싶습니다"
- **연구원**: "다양한 RAG 시스템들의 성능을 표준화된 메트릭으로 비교하고 싶습니다"

## 🔧 기술적 요구사항

### 시스템 아키텍처
- **서비스명**: evaluation-server
- **포트**: 8003
- **아키텍처**: FastAPI 기반 마이크로서비스
- **데이터베이스**: PostgreSQL (평가 결과 저장)
- **파일 시스템**: 로컬 폴더 기반 테스트 데이터셋 관리

### 핵심 컴포넌트

#### 1. RAG 시스템 인터페이스
```python
class RAGSystemInterface:
    async def embed_query(self, query: str) -> List[float]
    async def retrieve(self, query: str, top_k: int) -> List[RetrievalResult]
```

#### 2. 테스트 데이터셋 인터페이스
```python
class TestDatasetInterface:
    def load_dataset(self) -> TestDataset
    def get_queries(self) -> List[Query]
    def get_ground_truth(self, query_id: str) -> List[str]
```

#### 3. 평가 메트릭
- **NDCG**: Normalized Discounted Cumulative Gain
- **Recall@K**: K개 결과 중 정답 포함 비율
- **Precision@K**: K개 결과 중 정답 정밀도
- **Hit@K**: K개 결과에 정답이 포함되는지 여부

#### 4. 비교 분석
- **베이스라인 비교**: 등록된 베이스라인 대비 성능 변화율
- **시스템 간 비교**: 서로 다른 RAG 시스템 간 성능 차이

### API 엔드포인트

#### 평가 실행
- `POST /api/v1/evaluations/run` - 평가 실행
- `GET /api/v1/evaluations/{evaluation_id}` - 평가 결과 조회
- `GET /api/v1/evaluations` - 평가 이력 조회

#### 시스템 관리
- `POST /api/v1/systems` - RAG 시스템 등록
- `GET /api/v1/systems` - 등록된 시스템 목록
- `PUT /api/v1/systems/{system_id}` - 시스템 정보 수정

#### 데이터셋 관리
- `GET /api/v1/datasets` - 사용 가능한 데이터셋 목록
- `GET /api/v1/datasets/{dataset_id}` - 데이터셋 상세 정보

#### 베이스라인 관리
- `POST /api/v1/baselines` - 베이스라인 등록
- `GET /api/v1/baselines` - 베이스라인 목록
- `GET /api/v1/baselines/{baseline_id}/compare` - 베이스라인 비교

## 📊 데이터 모델

### RAG 시스템
```python
class RAGSystem:
    id: int
    name: str
    description: str
    base_url: str
    api_key: str (optional)
    system_type: str  # 'internal', 'external'
    config: dict  # 시스템별 설정
```

### 평가 결과
```python
class EvaluationResult:
    id: int
    system_id: int
    dataset_id: str
    metrics: dict  # NDCG, Recall@K 등
    execution_time: float
    created_at: datetime
    config: dict  # 평가 설정
```

### 베이스라인
```python
class Baseline:
    id: int
    name: str
    system_id: int
    dataset_id: str
    evaluation_result_id: int
    description: str
    created_at: datetime
```

### 테스트 데이터셋
```python
class TestDataset:
    id: str
    name: str
    description: str
    file_path: str
    query_count: int
    ground_truth_format: str
```

## 🔄 워크플로우

### 평가 실행 프로세스
1. **시스템 선택**: 평가할 RAG 시스템 선택
2. **데이터셋 선택**: 사용할 테스트 데이터셋 선택
3. **평가 설정**: 메트릭 종류, K값 등 설정
4. **평가 실행**: 
   - 쿼리별로 RAG 시스템 호출
   - Retrieval 결과 수집
   - 메트릭 계산
5. **결과 저장**: 평가 결과 데이터베이스 저장
6. **비교 분석**: 베이스라인/다른 시스템과 비교
7. **결과 반환**: API 응답으로 결과 제공

### 베이스라인 등록 프로세스
1. **평가 결과 선택**: 베이스라인으로 등록할 평가 결과 선택
2. **베이스라인 정보 입력**: 이름, 설명 등
3. **베이스라인 등록**: 데이터베이스에 베이스라인 정보 저장

## 📁 파일 시스템 구조

### 테스트 데이터셋 폴더 구조
```
evaluation-server/
├── datasets/
│   ├── ms-marco/
│   │   ├── queries.jsonl
│   │   ├── ground_truth.jsonl
│   │   └── metadata.json
│   ├── natural-questions/
│   │   ├── queries.jsonl
│   │   ├── ground_truth.jsonl
│   │   └── metadata.json
│   └── custom-dataset/
│       ├── queries.jsonl
│       ├── ground_truth.jsonl
│       └── metadata.json
```

### 데이터 형식
```json
// queries.jsonl
{"query_id": "q1", "query": "파이썬 리스트 정렬 방법"}

// ground_truth.jsonl  
{"query_id": "q1", "relevant_docs": ["doc1", "doc3", "doc5"]}

// metadata.json
{
  "name": "MS MARCO",
  "description": "Microsoft Machine Reading Comprehension Dataset",
  "query_count": 1000,
  "language": "ko",
  "domain": "general"
}
```

## 🚀 MVP (Minimum Viable Product)

### Phase 1: 기본 평가 기능
- [ ] RAG 시스템 인터페이스 구현
- [ ] 기본 메트릭 계산 (Recall@K, Precision@K, Hit@K)
- [ ] 단일 데이터셋 평가
- [ ] 평가 결과 저장

### Phase 2: 확장 기능
- [ ] NDCG 메트릭 추가
- [ ] 다중 데이터셋 지원
- [ ] 베이스라인 등록 및 비교

### Phase 3: 고급 기능
- [ ] 시스템 간 성능 비교
- [ ] API를 통한 동적 시스템 등록
- [ ] 배치 평가 기능

## 🔍 성공 지표

### 기능적 지표
- 평가 실행 성공률 > 99%
- 메트릭 계산 정확도 100%
- API 응답 시간 < 5초 (일반적인 평가)

### 운영 지표
- 시스템 가용성 > 99.9%
- 동시 평가 요청 처리 > 10개
- 데이터셋 로딩 시간 < 1초

## 🛡️ 제약사항 및 고려사항

### 기술적 제약사항
- 메모리 사용량: 대용량 데이터셋 처리 시 메모리 최적화 필요
- 네트워크 의존성: 외부 RAG 시스템 호출 시 네트워크 지연 고려
- 동시성: 다중 평가 요청 처리 시 리소스 관리

### 보안 고려사항
- API 키 안전한 저장 및 관리
- 외부 시스템 호출 시 인증 처리
- 평가 결과 데이터 접근 권한 관리

### 확장성 고려사항
- 새로운 메트릭 추가 용이성
- 다양한 RAG 시스템 인터페이스 지원
- 대용량 데이터셋 처리 성능

이 PRD를 기반으로 구체적인 개발 태스크들을 정의하여 단계별로 구현을 진행합니다. 