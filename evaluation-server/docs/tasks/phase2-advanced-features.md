# Phase 2: 확장 기능 개발 태스크

## 📋 개요
Phase 1의 기본 평가 기능을 확장하여 NDCG 메트릭, 다중 데이터셋 지원, 베이스라인 비교 기능을 추가합니다.

## 🎯 목표
- NDCG 메트릭 추가
- 다중 데이터셋 지원
- 베이스라인 등록 및 비교 기능

## 📝 상세 태스크

### Task 2.1: NDCG 메트릭 구현
**담당자**: 개발자  
**예상 소요 시간**: 4시간  
**우선순위**: High  

#### 작업 내용
- [ ] NDCG (Normalized Discounted Cumulative Gain) 메트릭 구현
- [ ] 관련성 점수 처리 로직 추가
- [ ] NDCG 검증 테스트 작성

#### 세부 작업
1. **NDCG 메트릭 구현**
   ```python
   # app/features/metrics/ndcg.py
   import numpy as np
   from typing import List, Dict
   
   class NDCGAtK(MetricCalculator):
       def calculate(self, predictions: List[str], ground_truth: Dict[str, float], k: int) -> float:
           """
           NDCG@K 계산
           
           Args:
               predictions: 검색 결과 문서 ID 리스트 (순서대로)
               ground_truth: {doc_id: relevance_score} 형태의 정답
               k: 상위 k개 결과만 고려
           
           Returns:
               NDCG@K 값 (0.0 ~ 1.0)
           """
           # DCG 계산
           dcg = self._calculate_dcg(predictions[:k], ground_truth)
           
           # IDCG 계산
           ideal_ranking = sorted(ground_truth.items(), key=lambda x: x[1], reverse=True)
           ideal_docs = [doc_id for doc_id, _ in ideal_ranking]
           idcg = self._calculate_dcg(ideal_docs[:k], ground_truth)
           
           # NDCG 계산
           if idcg == 0:
               return 0.0
           return dcg / idcg
       
       def _calculate_dcg(self, doc_ids: List[str], relevance: Dict[str, float]) -> float:
           """DCG (Discounted Cumulative Gain) 계산"""
           dcg = 0.0
           for i, doc_id in enumerate(doc_ids):
               rel_score = relevance.get(doc_id, 0.0)
               # DCG 공식: rel_i / log2(i+2)
               dcg += rel_score / np.log2(i + 2)
           return dcg
   ```

2. **관련성 점수 데이터 형식 확장**
   ```python
   # app/features/datasets/schema.py
   class GroundTruthWithRelevance(BaseModel):
       query_id: str
       relevant_docs: List[str]  # 기존 이진 관련성
       relevance_scores: Optional[Dict[str, float]] = None  # NDCG용 점수
   ```

3. **메트릭 매니저 업데이트**
   ```python
   # app/features/metrics/manager.py (업데이트)
   class MetricsManager:
       def __init__(self):
           self.metrics = {
               'recall': RecallAtK(),
               'precision': PrecisionAtK(),
               'hit': HitAtK(),
               'ndcg': NDCGAtK()  # 새로 추가
           }
   ```

#### 완료 조건
- [ ] NDCG@K 메트릭 정확한 구현
- [ ] 관련성 점수 처리 로직 완성
- [ ] 표준 데이터셋으로 NDCG 값 검증

---

### Task 2.2: 다중 데이터셋 지원 구현
**담당자**: 개발자  
**예상 소요 시간**: 3시간  
**우선순위**: High  

#### 작업 내용
- [ ] 배치 평가 기능 구현
- [ ] 데이터셋 자동 발견 로직
- [ ] 다중 데이터셋 결과 집계

#### 세부 작업
1. **배치 평가 서비스**
   ```python
   # app/features/evaluations/batch_service.py
   class BatchEvaluationService:
       def __init__(self, evaluation_service: EvaluationService):
           self.evaluation_service = evaluation_service
       
       async def run_batch_evaluation(
           self,
           system_id: int,
           dataset_ids: List[str],
           config: EvaluationConfig
       ) -> List[EvaluationResult]:
           """여러 데이터셋에 대해 배치 평가 실행"""
           results = []
           
           for dataset_id in dataset_ids:
               try:
                   result = await self.evaluation_service.run_evaluation(
                       system_id, dataset_id, config
                   )
                   results.append(result)
               except Exception as e:
                   # 개별 데이터셋 실패 시 로그 기록하고 계속 진행
                   logger.error(f"Dataset {dataset_id} evaluation failed: {e}")
           
           return results
       
       def aggregate_results(self, results: List[EvaluationResult]) -> Dict[str, float]:
           """다중 데이터셋 결과 집계 (평균, 가중평균 등)"""
           pass
   ```

2. **데이터셋 자동 발견**
   ```python
   # app/features/datasets/discovery.py
   class DatasetDiscovery:
       def __init__(self, datasets_path: str):
           self.datasets_path = datasets_path
       
       def discover_datasets(self) -> List[str]:
           """datasets 폴더에서 사용 가능한 데이터셋 자동 발견"""
           datasets = []
           for item in os.listdir(self.datasets_path):
               dataset_path = os.path.join(self.datasets_path, item)
               if self._is_valid_dataset(dataset_path):
                   datasets.append(item)
           return datasets
       
       def _is_valid_dataset(self, path: str) -> bool:
           """데이터셋 폴더가 유효한지 검증"""
           required_files = ['queries.jsonl', 'ground_truth.jsonl', 'metadata.json']
           return all(os.path.exists(os.path.join(path, f)) for f in required_files)
   ```

3. **배치 평가 API**
   ```python
   # app/features/evaluations/router.py (확장)
   @router.post("/batch", response_model=BatchEvaluationResponse)
   async def run_batch_evaluation(request: BatchEvaluationRequest):
       """다중 데이터셋 배치 평가"""
       pass
   
   @router.get("/batch/{batch_id}", response_model=BatchEvaluationResponse)
   async def get_batch_evaluation(batch_id: int):
       """배치 평가 결과 조회"""
       pass
   ```

#### 완료 조건
- [ ] 다중 데이터셋 배치 평가 동작
- [ ] 데이터셋 자동 발견 기능 동작
- [ ] 결과 집계 로직 구현

---

### Task 2.3: 베이스라인 관리 시스템 구현
**담당자**: 개발자  
**예상 소요 시간**: 5시간  
**우선순위**: High  

#### 작업 내용
- [ ] 베이스라인 데이터 모델 구현
- [ ] 베이스라인 등록 서비스
- [ ] 베이스라인 비교 로직

#### 세부 작업
1. **베이스라인 모델 구현**
   ```python
   # app/features/baselines/model.py
   class Baseline(Base):
       __tablename__ = "baselines"
       
       id = Column(Integer, primary_key=True, index=True)
       name = Column(String, nullable=False)
       description = Column(Text)
       system_id = Column(Integer, ForeignKey("rag_systems.id"))
       dataset_id = Column(String, nullable=False)
       evaluation_result_id = Column(Integer, ForeignKey("evaluation_results.id"))
       is_active = Column(Boolean, default=True)
       created_at = Column(DateTime(timezone=True), server_default=func.now())
       
       # 관계 설정
       system = relationship("RAGSystem")
       evaluation_result = relationship("EvaluationResult")
   ```

2. **베이스라인 서비스**
   ```python
   # app/features/baselines/service.py
   class BaselineService:
       def __init__(self, baseline_repository: BaselineRepository):
           self.baseline_repository = baseline_repository
       
       async def register_baseline(
           self,
           name: str,
           description: str,
           evaluation_result_id: int
       ) -> Baseline:
           """평가 결과를 베이스라인으로 등록"""
           pass
       
       async def compare_with_baseline(
           self,
           baseline_id: int,
           current_result: EvaluationResult
       ) -> BaselineComparison:
           """현재 결과를 베이스라인과 비교"""
           baseline = await self.baseline_repository.get_by_id(baseline_id)
           baseline_result = baseline.evaluation_result
           
           comparison = self._calculate_comparison(baseline_result, current_result)
           return comparison
       
       def _calculate_comparison(
           self,
           baseline_result: EvaluationResult,
           current_result: EvaluationResult
       ) -> BaselineComparison:
           """메트릭별 변화율 계산"""
           comparison = {}
           
           for metric_name in baseline_result.metrics:
               if metric_name in current_result.metrics:
                   baseline_value = baseline_result.metrics[metric_name]
                   current_value = current_result.metrics[metric_name]
                   
                   # 변화율 계산 (%)
                   if baseline_value != 0:
                       change_rate = ((current_value - baseline_value) / baseline_value) * 100
                   else:
                       change_rate = 0.0
                   
                   comparison[metric_name] = {
                       'baseline': baseline_value,
                       'current': current_value,
                       'change': current_value - baseline_value,
                       'change_rate': change_rate
                   }
           
           return BaselineComparison(
               baseline_id=baseline_result.id,
               current_result_id=current_result.id,
               metrics_comparison=comparison
           )
   ```

3. **베이스라인 비교 스키마**
   ```python
   # app/features/baselines/schema.py
   class BaselineCreateRequest(BaseModel):
       name: str
       description: Optional[str] = None
       evaluation_result_id: int
   
   class BaselineComparison(BaseModel):
       baseline_id: int
       current_result_id: int
       metrics_comparison: Dict[str, Dict[str, float]]
       
       class Config:
           schema_extra = {
               "example": {
                   "baseline_id": 1,
                   "current_result_id": 5,
                   "metrics_comparison": {
                       "recall@5": {
                           "baseline": 0.75,
                           "current": 0.80,
                           "change": 0.05,
                           "change_rate": 6.67
                       }
                   }
               }
           }
   ```

4. **베이스라인 API**
   ```python
   # app/features/baselines/router.py
   router = APIRouter(prefix="/api/v1/baselines", tags=["baselines"])
   
   @router.post("/", response_model=BaselineResponse)
   async def create_baseline(request: BaselineCreateRequest):
       """베이스라인 등록"""
       pass
   
   @router.get("/", response_model=List[BaselineResponse])
   async def list_baselines(system_id: Optional[int] = None, dataset_id: Optional[str] = None):
       """베이스라인 목록 조회"""
       pass
   
   @router.get("/{baseline_id}/compare", response_model=BaselineComparison)
   async def compare_baseline(baseline_id: int, evaluation_result_id: int):
       """베이스라인과 평가 결과 비교"""
       pass
   ```

#### 완료 조건
- [ ] 베이스라인 등록 및 조회 기능 동작
- [ ] 베이스라인 비교 로직 정확성 검증
- [ ] API 엔드포인트 테스트 통과

---

### Task 2.4: 평가 결과 확장 및 통계 기능
**담당자**: 개발자  
**예상 소요 시간**: 3시간  
**우선순위**: Medium  

#### 작업 내용
- [ ] 평가 결과 상세 통계 추가
- [ ] 실행 메타데이터 저장
- [ ] 결과 필터링 및 정렬 기능

#### 세부 작업
1. **평가 결과 모델 확장**
   ```python
   # app/features/evaluations/model.py (확장)
   class EvaluationResult(Base):
       # 기존 필드들...
       
       # 새로 추가되는 필드들
       query_count = Column(Integer)  # 평가된 쿼리 수
       failed_queries = Column(Integer, default=0)  # 실패한 쿼리 수
       average_response_time = Column(Float)  # 평균 응답 시간
       median_response_time = Column(Float)  # 중앙값 응답 시간
       std_response_time = Column(Float)  # 응답 시간 표준편차
       
       # 메타데이터
       environment_info = Column(JSON)  # 실행 환경 정보
       version = Column(String)  # 평가 시스템 버전
   ```

2. **통계 계산 서비스**
   ```python
   # app/features/evaluations/statistics.py
   class EvaluationStatistics:
       @staticmethod
       def calculate_query_level_stats(query_results: List[QueryResult]) -> Dict[str, float]:
           """쿼리별 결과의 통계 계산"""
           response_times = [result.response_time for result in query_results]
           
           return {
               'query_count': len(query_results),
               'failed_queries': sum(1 for r in query_results if r.failed),
               'average_response_time': np.mean(response_times),
               'median_response_time': np.median(response_times),
               'std_response_time': np.std(response_times),
               'min_response_time': np.min(response_times),
               'max_response_time': np.max(response_times)
           }
   ```

3. **결과 필터링 API**
   ```python
   # app/features/evaluations/router.py (확장)
   @router.get("/", response_model=List[EvaluationResponse])
   async def list_evaluations(
       system_id: Optional[int] = None,
       dataset_id: Optional[str] = None,
       date_from: Optional[datetime] = None,
       date_to: Optional[datetime] = None,
       sort_by: str = "created_at",
       sort_order: str = "desc",
       limit: int = 50,
       offset: int = 0
   ):
       """평가 결과 목록 (필터링, 정렬, 페이지네이션)"""
       pass
   ```

#### 완료 조건
- [ ] 상세 통계 계산 및 저장
- [ ] 결과 필터링 기능 동작
- [ ] 성능 통계 정확성 검증

---

### Task 2.5: 데이터셋 품질 검증 기능
**담당자**: 개발자  
**예상 소요 시간**: 2시간  
**우선순위**: Medium  

#### 작업 내용
- [ ] 데이터셋 유효성 검증
- [ ] 품질 보고서 생성
- [ ] 문제 데이터 식별 및 보고

#### 세부 작업
1. **데이터셋 검증기**
   ```python
   # app/features/datasets/validator.py
   class DatasetValidator:
       def validate_dataset(self, dataset_path: str) -> ValidationReport:
           """데이터셋 전체 검증"""
           report = ValidationReport()
           
           # 필수 파일 존재 확인
           report.file_checks = self._check_required_files(dataset_path)
           
           # 데이터 형식 검증
           report.format_checks = self._check_data_format(dataset_path)
           
           # 데이터 일관성 검증
           report.consistency_checks = self._check_data_consistency(dataset_path)
           
           return report
       
       def _check_required_files(self, dataset_path: str) -> Dict[str, bool]:
           """필수 파일 존재 확인"""
           required_files = ['queries.jsonl', 'ground_truth.jsonl', 'metadata.json']
           return {
               file: os.path.exists(os.path.join(dataset_path, file))
               for file in required_files
           }
       
       def _check_data_format(self, dataset_path: str) -> Dict[str, List[str]]:
           """데이터 형식 오류 검사"""
           errors = []
           
           # queries.jsonl 검증
           queries_errors = self._validate_queries_file(
               os.path.join(dataset_path, 'queries.jsonl')
           )
           errors.extend(queries_errors)
           
           # ground_truth.jsonl 검증
           gt_errors = self._validate_ground_truth_file(
               os.path.join(dataset_path, 'ground_truth.jsonl')
           )
           errors.extend(gt_errors)
           
           return {'errors': errors}
   ```

2. **데이터셋 품질 API**
   ```python
   # app/features/datasets/router.py (확장)
   @router.get("/{dataset_id}/validate", response_model=ValidationReport)
   async def validate_dataset(dataset_id: str):
       """데이터셋 품질 검증"""
       pass
   
   @router.get("/{dataset_id}/stats", response_model=DatasetStats)
   async def get_dataset_stats(dataset_id: str):
       """데이터셋 통계 정보"""
       pass
   ```

#### 완료 조건
- [ ] 데이터셋 검증 로직 구현
- [ ] 품질 보고서 생성 기능
- [ ] 문제 데이터 식별 정확성

## 🎯 Phase 2 완료 조건

### 기능적 요구사항
- [ ] NDCG 메트릭이 정확하게 계산됨
- [ ] 다중 데이터셋 배치 평가 가능
- [ ] 베이스라인 등록 및 비교 기능 동작
- [ ] 평가 결과 상세 통계 제공
- [ ] 데이터셋 품질 검증 가능

### 기술적 요구사항
- [ ] 모든 새 기능에 대한 단위 테스트
- [ ] 통합 테스트 업데이트
- [ ] API 문서 업데이트
- [ ] 베이스라인 비교 정확성 검증

### 성능 요구사항
- [ ] 배치 평가 시 메모리 사용량 최적화
- [ ] NDCG 계산 성능 최적화
- [ ] 다중 데이터셋 병렬 처리

## 📅 예상 일정
**총 소요 시간**: 17시간 (약 2일)

1. **Day 1**: Task 2.1, 2.2 (NDCG, 다중 데이터셋)
2. **Day 2**: Task 2.3, 2.4, 2.5 (베이스라인, 통계, 검증) 