# Phase 3: 고급 기능 개발 태스크

## 📋 개요
시스템 간 성능 비교, 동적 시스템 등록, 배치 평가 등 고급 기능을 구현하여 RAG 평가 서비스를 완성합니다.

## 🎯 목표
- 시스템 간 성능 비교 및 순위 매기기
- API를 통한 동적 시스템 등록
- 배치 평가 및 스케줄링 기능
- 고급 분석 및 시각화 지원

## 📝 상세 태스크

### Task 3.1: 시스템 간 성능 비교 구현
**담당자**: 개발자  
**예상 소요 시간**: 5시간  
**우선순위**: High  

#### 작업 내용
- [ ] 다중 시스템 비교 로직 구현
- [ ] 시스템 순위 매기기 알고리즘
- [ ] 통계적 유의성 검정 추가

#### 세부 작업
1. **시스템 비교 서비스**
   ```python
   # app/features/comparisons/service.py
   from typing import List, Dict
   from scipy import stats
   
   class SystemComparisonService:
       def __init__(self, evaluation_repository: EvaluationRepository):
           self.evaluation_repository = evaluation_repository
       
       async def compare_systems(
           self,
           system_ids: List[int],
           dataset_id: str,
           metric_name: str,
           k_value: int = 5
       ) -> SystemComparison:
           """여러 시스템의 성능을 비교"""
           
           # 각 시스템의 최신 평가 결과 수집
           system_results = {}
           for system_id in system_ids:
               latest_result = await self.evaluation_repository.get_latest_by_system_and_dataset(
                   system_id, dataset_id
               )
               if latest_result:
                   metric_key = f"{metric_name}@{k_value}"
                   system_results[system_id] = {
                       'value': latest_result.metrics.get(metric_key, 0.0),
                       'evaluation_id': latest_result.id,
                       'created_at': latest_result.created_at
                   }
           
           # 순위 계산
           ranking = self._calculate_ranking(system_results, metric_name)
           
           # 통계적 유의성 검정 (페어와이즈 비교)
           significance_tests = self._perform_significance_tests(system_results)
           
           return SystemComparison(
               dataset_id=dataset_id,
               metric=metric_name,
               k_value=k_value,
               systems=system_results,
               ranking=ranking,
               significance_tests=significance_tests,
               comparison_timestamp=datetime.utcnow()
           )
       
       def _calculate_ranking(self, system_results: Dict, metric_name: str) -> List[Dict]:
           """시스템 순위 계산"""
           # 메트릭 값 기준으로 정렬 (높은 값이 좋은 메트릭이라고 가정)
           sorted_systems = sorted(
               system_results.items(),
               key=lambda x: x[1]['value'],
               reverse=True
           )
           
           ranking = []
           for rank, (system_id, result) in enumerate(sorted_systems, 1):
               ranking.append({
                   'rank': rank,
                   'system_id': system_id,
                   'value': result['value'],
                   'evaluation_id': result['evaluation_id']
               })
           
           return ranking
       
       def _perform_significance_tests(self, system_results: Dict) -> Dict:
           """통계적 유의성 검정 (t-test)"""
           # 실제로는 쿼리별 상세 결과가 필요하지만, 
           # 여기서는 시스템 레벨 비교로 단순화
           significance_tests = {}
           
           system_ids = list(system_results.keys())
           for i, system_a in enumerate(system_ids):
               for system_b in system_ids[i+1:]:
                   # 쌍별 비교
                   value_a = system_results[system_a]['value']
                   value_b = system_results[system_b]['value']
                   
                   # 단순한 차이 계산 (실제로는 분포 기반 검정 필요)
                   difference = abs(value_a - value_b)
                   p_value = 0.05 if difference > 0.1 else 0.5  # 임의의 기준
                   
                   significance_tests[f"{system_a}_vs_{system_b}"] = {
                       'difference': value_a - value_b,
                       'p_value': p_value,
                       'is_significant': p_value < 0.05
                   }
           
           return significance_tests
   ```

2. **시스템 비교 스키마**
   ```python
   # app/features/comparisons/schema.py
   class SystemComparisonRequest(BaseModel):
       system_ids: List[int]
       dataset_id: str
       metric_name: str = "recall"
       k_value: int = 5
   
   class SystemComparison(BaseModel):
       dataset_id: str
       metric: str
       k_value: int
       systems: Dict[int, Dict[str, Any]]
       ranking: List[Dict[str, Any]]
       significance_tests: Dict[str, Dict[str, float]]
       comparison_timestamp: datetime
       
       class Config:
           schema_extra = {
               "example": {
                   "dataset_id": "ms-marco",
                   "metric": "recall",
                   "k_value": 5,
                   "ranking": [
                       {"rank": 1, "system_id": 2, "value": 0.85},
                       {"rank": 2, "system_id": 1, "value": 0.78},
                       {"rank": 3, "system_id": 3, "value": 0.72}
                   ]
               }
           }
   ```

3. **시스템 비교 API**
   ```python
   # app/features/comparisons/router.py
   router = APIRouter(prefix="/api/v1/comparisons", tags=["comparisons"])
   
   @router.post("/systems", response_model=SystemComparison)
   async def compare_systems(request: SystemComparisonRequest):
       """여러 시스템 성능 비교"""
       pass
   
   @router.get("/leaderboard/{dataset_id}", response_model=List[Dict])
   async def get_leaderboard(dataset_id: str, metric: str = "recall", k: int = 5):
       """데이터셋별 리더보드"""
       pass
   ```

#### 완료 조건
- [ ] 다중 시스템 비교 기능 동작
- [ ] 순위 계산 정확성 검증
- [ ] 통계적 유의성 검정 구현

---

### Task 3.2: 동적 시스템 등록 및 검증
**담당자**: 개발자  
**예상 소요 시간**: 4시간  
**우선순위**: High  

#### 작업 내용
- [ ] 시스템 등록 시 자동 검증
- [ ] API 호환성 테스트
- [ ] 시스템 헬스체크 기능

#### 세부 작업
1. **시스템 검증 서비스**
   ```python
   # app/features/systems/validator.py
   class SystemValidator:
       def __init__(self, http_client: httpx.AsyncClient):
           self.http_client = http_client
       
       async def validate_system(self, system_config: dict) -> ValidationResult:
           """시스템 등록 전 검증"""
           result = ValidationResult()
           
           # 1. 기본 연결 테스트
           result.connectivity = await self._test_connectivity(system_config['base_url'])
           
           # 2. API 엔드포인트 존재 확인
           result.api_endpoints = await self._test_api_endpoints(system_config)
           
           # 3. 응답 형식 검증
           result.response_format = await self._test_response_format(system_config)
           
           # 4. 성능 기본 테스트
           result.performance = await self._test_basic_performance(system_config)
           
           result.is_valid = all([
               result.connectivity,
               result.api_endpoints['embed_query'],
               result.api_endpoints['retrieve'],
               result.response_format
           ])
           
           return result
       
       async def _test_connectivity(self, base_url: str) -> bool:
           """기본 연결 테스트"""
           try:
               response = await self.http_client.get(f"{base_url}/health", timeout=5.0)
               return response.status_code == 200
           except:
               return False
       
       async def _test_api_endpoints(self, system_config: dict) -> dict:
           """필수 API 엔드포인트 테스트"""
           base_url = system_config['base_url']
           
           endpoints = {
               'embed_query': f"{base_url}/api/v1/embed",
               'retrieve': f"{base_url}/api/v1/retrieve"
           }
           
           results = {}
           for name, url in endpoints.items():
               try:
                   # OPTIONS 요청으로 엔드포인트 존재 확인
                   response = await self.http_client.options(url, timeout=5.0)
                   results[name] = response.status_code in [200, 405]  # 405도 존재함을 의미
               except:
                   results[name] = False
           
           return results
       
       async def _test_response_format(self, system_config: dict) -> bool:
           """응답 형식 검증"""
           try:
               # 테스트 쿼리로 실제 API 호출
               test_query = "test query"
               rag_system = HTTPRAGSystem(
                   system_config['base_url'],
                   system_config.get('api_key')
               )
               
               # 임베딩 테스트
               embedding = await rag_system.embed_query(test_query)
               if not isinstance(embedding, list) or len(embedding) == 0:
                   return False
               
               # 검색 테스트
               results = await rag_system.retrieve(test_query, top_k=5)
               if not isinstance(results, list):
                   return False
               
               return True
           except:
               return False
   ```

2. **시스템 등록 서비스 확장**
   ```python
   # app/features/systems/service.py (확장)
   class SystemService:
       def __init__(self, validator: SystemValidator, repository: SystemRepository):
           self.validator = validator
           self.repository = repository
       
       async def register_system(self, system_data: SystemCreateRequest) -> SystemResponse:
           """시스템 등록 (검증 포함)"""
           
           # 1. 시스템 검증
           validation_result = await self.validator.validate_system(system_data.dict())
           
           if not validation_result.is_valid:
               raise SystemValidationError(
                   "시스템 검증 실패",
                   details=validation_result.dict()
               )
           
           # 2. 시스템 등록
           system = await self.repository.create(system_data.dict())
           
           # 3. 초기 헬스체크 스케줄링
           await self._schedule_health_check(system.id)
           
           return SystemResponse.from_orm(system)
       
       async def health_check(self, system_id: int) -> HealthCheckResult:
           """시스템 헬스체크"""
           system = await self.repository.get_by_id(system_id)
           if not system:
               raise SystemNotFoundException(f"System {system_id} not found")
           
           validation_result = await self.validator.validate_system({
               'base_url': system.base_url,
               'api_key': system.api_key
           })
           
           # 헬스체크 결과 저장
           health_check = SystemHealthCheck(
               system_id=system_id,
               is_healthy=validation_result.is_valid,
               response_time=validation_result.performance.get('response_time', 0),
               details=validation_result.dict(),
               checked_at=datetime.utcnow()
           )
           
           await self.repository.save_health_check(health_check)
           
           return HealthCheckResult.from_orm(health_check)
   ```

3. **시스템 관리 API 확장**
   ```python
   # app/features/systems/router.py (확장)
   @router.post("/validate", response_model=ValidationResult)
   async def validate_system(request: SystemCreateRequest):
       """시스템 등록 전 검증"""
       pass
   
   @router.get("/{system_id}/health", response_model=HealthCheckResult)
   async def system_health_check(system_id: int):
       """시스템 헬스체크"""
       pass
   
   @router.get("/{system_id}/health/history", response_model=List[HealthCheckResult])
   async def system_health_history(system_id: int, limit: int = 10):
       """시스템 헬스체크 이력"""
       pass
   ```

#### 완료 조건
- [ ] 시스템 등록 시 자동 검증 동작
- [ ] API 호환성 테스트 통과
- [ ] 헬스체크 기능 정상 동작

---

### Task 3.3: 배치 평가 및 스케줄링 시스템
**담당자**: 개발자  
**예상 소요 시간**: 6시간  
**우선순위**: Medium  

#### 작업 내용
- [ ] 비동기 배치 평가 시스템
- [ ] 평가 작업 큐 및 스케줄러
- [ ] 진행 상황 추적 및 모니터링

#### 세부 작업
1. **배치 평가 작업 시스템**
   ```python
   # app/features/batch/models.py
   class BatchEvaluationJob(Base):
       __tablename__ = "batch_evaluation_jobs"
       
       id = Column(Integer, primary_key=True)
       name = Column(String, nullable=False)
       description = Column(Text)
       
       # 작업 설정
       system_ids = Column(JSON)  # List[int]
       dataset_ids = Column(JSON)  # List[str]
       evaluation_config = Column(JSON)
       
       # 작업 상태
       status = Column(String, default="pending")  # pending, running, completed, failed
       progress = Column(Integer, default=0)  # 0-100
       
       # 실행 정보
       started_at = Column(DateTime)
       completed_at = Column(DateTime)
       error_message = Column(Text)
       
       # 결과
       evaluation_result_ids = Column(JSON)  # List[int]
       
       created_at = Column(DateTime(timezone=True), server_default=func.now())
   
   class BatchEvaluationTask(Base):
       __tablename__ = "batch_evaluation_tasks"
       
       id = Column(Integer, primary_key=True)
       job_id = Column(Integer, ForeignKey("batch_evaluation_jobs.id"))
       system_id = Column(Integer)
       dataset_id = Column(String)
       
       status = Column(String, default="pending")
       started_at = Column(DateTime)
       completed_at = Column(DateTime)
       evaluation_result_id = Column(Integer, ForeignKey("evaluation_results.id"))
       error_message = Column(Text)
   ```

2. **배치 평가 서비스**
   ```python
   # app/features/batch/service.py
   import asyncio
   from celery import Celery
   
   class BatchEvaluationService:
       def __init__(self):
           self.celery_app = Celery('evaluation-server')
       
       async def create_batch_job(
           self,
           name: str,
           system_ids: List[int],
           dataset_ids: List[str],
           evaluation_config: EvaluationConfig
       ) -> BatchEvaluationJob:
           """배치 평가 작업 생성"""
           
           # 1. 작업 생성
           job = BatchEvaluationJob(
               name=name,
               system_ids=system_ids,
               dataset_ids=dataset_ids,
               evaluation_config=evaluation_config.dict(),
               status="pending"
           )
           
           # 2. 개별 태스크 생성
           tasks = []
           for system_id in system_ids:
               for dataset_id in dataset_ids:
                   task = BatchEvaluationTask(
                       job_id=job.id,
                       system_id=system_id,
                       dataset_id=dataset_id
                   )
                   tasks.append(task)
           
           # 3. 데이터베이스 저장
           await self.repository.save_job_and_tasks(job, tasks)
           
           # 4. 비동기 실행 시작
           self._start_batch_execution.delay(job.id)
           
           return job
       
       @celery_app.task
       def _start_batch_execution(self, job_id: int):
           """배치 작업 실행 (Celery 태스크)"""
           asyncio.run(self._execute_batch_job(job_id))
       
       async def _execute_batch_job(self, job_id: int):
           """실제 배치 작업 실행"""
           job = await self.repository.get_job(job_id)
           tasks = await self.repository.get_job_tasks(job_id)
           
           # 작업 상태 업데이트
           job.status = "running"
           job.started_at = datetime.utcnow()
           await self.repository.update_job(job)
           
           completed_tasks = 0
           total_tasks = len(tasks)
           
           try:
               # 병렬 처리 (제한된 동시성)
               semaphore = asyncio.Semaphore(3)  # 최대 3개 동시 실행
               
               async def execute_single_task(task):
                   async with semaphore:
                       await self._execute_single_task(task)
                       nonlocal completed_tasks
                       completed_tasks += 1
                       
                       # 진행 상황 업데이트
                       progress = int((completed_tasks / total_tasks) * 100)
                       await self.repository.update_job_progress(job_id, progress)
               
               # 모든 태스크 병렬 실행
               await asyncio.gather(*[execute_single_task(task) for task in tasks])
               
               # 작업 완료
               job.status = "completed"
               job.completed_at = datetime.utcnow()
               job.progress = 100
               
           except Exception as e:
               job.status = "failed"
               job.error_message = str(e)
               job.completed_at = datetime.utcnow()
           
           await self.repository.update_job(job)
       
       async def _execute_single_task(self, task: BatchEvaluationTask):
           """개별 태스크 실행"""
           try:
               task.status = "running"
               task.started_at = datetime.utcnow()
               await self.repository.update_task(task)
               
               # 평가 실행
               evaluation_result = await self.evaluation_service.run_evaluation(
                   task.system_id,
                   task.dataset_id,
                   EvaluationConfig(**task.job.evaluation_config)
               )
               
               task.status = "completed"
               task.evaluation_result_id = evaluation_result.id
               task.completed_at = datetime.utcnow()
               
           except Exception as e:
               task.status = "failed"
               task.error_message = str(e)
               task.completed_at = datetime.utcnow()
           
           await self.repository.update_task(task)
   ```

3. **배치 평가 API**
   ```python
   # app/features/batch/router.py
   @router.post("/jobs", response_model=BatchJobResponse)
   async def create_batch_job(request: BatchJobCreateRequest):
       """배치 평가 작업 생성"""
       pass
   
   @router.get("/jobs/{job_id}", response_model=BatchJobResponse)
   async def get_batch_job(job_id: int):
       """배치 작업 상태 조회"""
       pass
   
   @router.get("/jobs/{job_id}/progress", response_model=BatchJobProgress)
   async def get_batch_job_progress(job_id: int):
       """배치 작업 진행 상황"""
       pass
   
   @router.post("/jobs/{job_id}/cancel")
   async def cancel_batch_job(job_id: int):
       """배치 작업 취소"""
       pass
   ```

#### 완료 조건
- [ ] 비동기 배치 평가 시스템 동작
- [ ] 작업 큐 및 스케줄러 정상 작동
- [ ] 진행 상황 추적 기능 구현

---

### Task 3.4: 고급 분석 및 리포팅
**담당자**: 개발자  
**예상 소요 시간**: 4시간  
**우선순위**: Medium  

#### 작업 내용
- [ ] 상세 성능 분석 리포트
- [ ] 트렌드 분석 기능
- [ ] 데이터 내보내기 기능

#### 세부 작업
1. **성능 분석 서비스**
   ```python
   # app/features/analytics/service.py
   class AnalyticsService:
       async def generate_performance_report(
           self,
           system_id: int,
           date_range: DateRange
       ) -> PerformanceReport:
           """시스템 성능 상세 분석 리포트"""
           
           evaluations = await self.repository.get_evaluations_by_date_range(
               system_id, date_range.start_date, date_range.end_date
           )
           
           # 메트릭별 트렌드 분석
           trends = self._analyze_trends(evaluations)
           
           # 데이터셋별 성능 비교
           dataset_performance = self._analyze_dataset_performance(evaluations)
           
           # 성능 변화 포인트 탐지
           change_points = self._detect_change_points(evaluations)
           
           return PerformanceReport(
               system_id=system_id,
               date_range=date_range,
               trends=trends,
               dataset_performance=dataset_performance,
               change_points=change_points,
               summary_statistics=self._calculate_summary_stats(evaluations)
           )
       
       def _analyze_trends(self, evaluations: List[EvaluationResult]) -> Dict:
           """메트릭별 트렌드 분석"""
           trends = {}
           
           # 시간순 정렬
           evaluations.sort(key=lambda x: x.created_at)
           
           # 각 메트릭별 트렌드 계산
           for metric_name in ['recall@5', 'precision@5', 'ndcg@5']:
               values = [e.metrics.get(metric_name, 0) for e in evaluations]
               dates = [e.created_at for e in evaluations]
               
               # 선형 회귀로 트렌드 계산
               trend_slope = self._calculate_trend_slope(dates, values)
               
               trends[metric_name] = {
                   'slope': trend_slope,
                   'direction': 'improving' if trend_slope > 0 else 'declining',
                   'values': values,
                   'dates': dates
               }
           
           return trends
       
       async def generate_comparison_report(
           self,
           system_ids: List[int],
           dataset_id: str
       ) -> ComparisonReport:
           """시스템 간 비교 리포트"""
           
           systems_data = {}
           for system_id in system_ids:
               evaluations = await self.repository.get_evaluations_by_system_and_dataset(
                   system_id, dataset_id
               )
               systems_data[system_id] = evaluations
           
           # 메트릭별 비교 분석
           metric_comparisons = self._compare_metrics(systems_data)
           
           # 안정성 분석 (성능 변동성)
           stability_analysis = self._analyze_stability(systems_data)
           
           return ComparisonReport(
               dataset_id=dataset_id,
               systems=system_ids,
               metric_comparisons=metric_comparisons,
               stability_analysis=stability_analysis
           )
   ```

2. **데이터 내보내기 서비스**
   ```python
   # app/features/export/service.py
   import pandas as pd
   import io
   
   class ExportService:
       async def export_evaluations_csv(
           self,
           filters: EvaluationFilters
       ) -> io.BytesIO:
           """평가 결과 CSV 내보내기"""
           
           evaluations = await self.repository.get_filtered_evaluations(filters)
           
           # 데이터 플랫닝
           rows = []
           for eval_result in evaluations:
               base_data = {
                   'evaluation_id': eval_result.id,
                   'system_id': eval_result.system_id,
                   'dataset_id': eval_result.dataset_id,
                   'created_at': eval_result.created_at,
                   'execution_time': eval_result.execution_time
               }
               
               # 메트릭 데이터 추가
               for metric_name, value in eval_result.metrics.items():
                   base_data[metric_name] = value
               
               rows.append(base_data)
           
           # DataFrame 생성 및 CSV 변환
           df = pd.DataFrame(rows)
           csv_buffer = io.BytesIO()
           df.to_csv(csv_buffer, index=False, encoding='utf-8')
           csv_buffer.seek(0)
           
           return csv_buffer
       
       async def export_comparison_json(
           self,
           comparison_id: int
       ) -> dict:
           """비교 결과 JSON 내보내기"""
           comparison = await self.repository.get_comparison(comparison_id)
           
           return {
               'metadata': {
                   'export_date': datetime.utcnow().isoformat(),
                   'comparison_id': comparison_id,
                   'format_version': '1.0'
               },
               'comparison_data': comparison.dict()
           }
   ```

3. **분석 및 내보내기 API**
   ```python
   # app/features/analytics/router.py
   @router.get("/systems/{system_id}/report", response_model=PerformanceReport)
   async def get_performance_report(
       system_id: int,
       start_date: datetime,
       end_date: datetime
   ):
       """성능 분석 리포트"""
       pass
   
   @router.get("/comparisons/{comparison_id}/report", response_model=ComparisonReport)
   async def get_comparison_report(comparison_id: int):
       """비교 분석 리포트"""
       pass
   
   @router.get("/export/evaluations")
   async def export_evaluations(
       format: str = "csv",
       system_id: Optional[int] = None,
       dataset_id: Optional[str] = None
   ):
       """평가 결과 내보내기"""
       pass
   ```

#### 완료 조건
- [ ] 상세 성능 분석 리포트 생성
- [ ] 트렌드 분석 정확성 검증
- [ ] CSV/JSON 내보내기 기능 동작

---

### Task 3.5: 모니터링 및 알림 시스템
**담당자**: 개발자  
**예상 소요 시간**: 3시간  
**우선순위**: Low  

#### 작업 내용
- [ ] 성능 임계값 모니터링
- [ ] 알림 시스템 구현
- [ ] 대시보드 메트릭 수집

#### 세부 작업
1. **모니터링 서비스**
   ```python
   # app/features/monitoring/service.py
   class MonitoringService:
       def __init__(self):
           self.alert_thresholds = {
               'recall@5': {'min': 0.7, 'max': 1.0},
               'precision@5': {'min': 0.6, 'max': 1.0},
               'ndcg@5': {'min': 0.65, 'max': 1.0}
           }
       
       async def check_performance_alerts(self, evaluation_result: EvaluationResult):
           """성능 알림 체크"""
           alerts = []
           
           for metric_name, thresholds in self.alert_thresholds.items():
               if metric_name in evaluation_result.metrics:
                   value = evaluation_result.metrics[metric_name]
                   
                   if value < thresholds['min']:
                       alerts.append(PerformanceAlert(
                           type='performance_degradation',
                           metric=metric_name,
                           value=value,
                           threshold=thresholds['min'],
                           evaluation_id=evaluation_result.id,
                           severity='high' if value < thresholds['min'] * 0.9 else 'medium'
                       ))
           
           # 알림 발송
           for alert in alerts:
               await self.send_alert(alert)
           
           return alerts
       
       async def send_alert(self, alert: PerformanceAlert):
           """알림 발송 (이메일, 슬랙 등)"""
           # 실제로는 이메일, 슬랙, 웹훅 등으로 발송
           logger.warning(f"Performance Alert: {alert.dict()}")
   ```

2. **모니터링 API**
   ```python
   # app/features/monitoring/router.py
   @router.get("/alerts", response_model=List[PerformanceAlert])
   async def get_alerts(limit: int = 50):
       """최근 알림 목록"""
       pass
   
   @router.get("/metrics/dashboard")
   async def get_dashboard_metrics():
       """대시보드용 메트릭"""
       pass
   ```

#### 완료 조건
- [ ] 성능 임계값 모니터링 동작
- [ ] 알림 시스템 구현
- [ ] 대시보드 메트릭 수집 기능

## 🎯 Phase 3 완료 조건

### 기능적 요구사항
- [ ] 시스템 간 성능 비교 및 순위 매기기
- [ ] 동적 시스템 등록 및 검증
- [ ] 배치 평가 및 스케줄링 시스템
- [ ] 고급 분석 리포트 생성
- [ ] 모니터링 및 알림 시스템

### 기술적 요구사항
- [ ] 비동기 처리 최적화
- [ ] 확장 가능한 아키텍처
- [ ] 완전한 API 문서
- [ ] 성능 테스트 통과

### 성능 요구사항
- [ ] 대용량 배치 처리 지원
- [ ] 실시간 모니터링 성능
- [ ] 동시 사용자 지원 (10명 이상)

## 📅 예상 일정
**총 소요 시간**: 22시간 (약 3일)

1. **Day 1**: Task 3.1, 3.2 (시스템 비교, 동적 등록)
2. **Day 2**: Task 3.3 (배치 평가)
3. **Day 3**: Task 3.4, 3.5 (분석, 모니터링)

## 🚀 전체 프로젝트 완료 후 추가 고려사항

### 운영 및 배포
- [ ] Docker Compose 설정 업데이트
- [ ] CI/CD 파이프라인 구성
- [ ] 프로덕션 환경 설정
- [ ] 로그 집계 및 모니터링 설정

### 문서화
- [ ] API 사용 가이드 작성
- [ ] 개발자 문서 완성
- [ ] 사용자 매뉴얼 작성
- [ ] 아키텍처 문서 업데이트 