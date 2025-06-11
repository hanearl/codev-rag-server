# Task 06: 전체 시스템 통합 테스트 및 검증

## 🎯 목표
전체 마이크로서비스 시스템의 통합 테스트, 성능 검증, 운영 준비성 확인을 통해 MVP의 완성도를 보장합니다.

## 📋 MVP 범위
- 전체 시스템 E2E 테스트
- 성능 및 부하 테스트
- 장애 복구 테스트
- 운영 환경 배포 준비
- 사용자 시나리오 검증

## 🏗️ 기술 스택
- **E2E 테스트**: pytest, httpx, Docker Compose
- **성능 테스트**: locust, k6
- **모니터링**: Prometheus, Grafana
- **로그 관리**: ELK Stack (선택적)

## 📁 프로젝트 구조

```
integration-tests/
├── e2e/
│   ├── __init__.py
│   ├── test_complete_workflow.py    ← 전체 워크플로우 테스트
│   ├── test_service_integration.py  ← 서비스 간 통합 테스트
│   └── test_error_scenarios.py      ← 에러 시나리오 테스트
├── performance/
│   ├── locustfile.py               ← 부하 테스트 시나리오
│   ├── k6-scripts/                 ← k6 성능 테스트
│   └── results/                    ← 테스트 결과 저장
├── monitoring/
│   ├── prometheus.yml              ← Prometheus 설정
│   ├── grafana/                    ← Grafana 대시보드
│   └── alerts.yml                  ← 알림 규칙
└── deployment/
    ├── production.yml              ← 운영 환경 설정
    └── staging.yml                 ← 스테이징 환경 설정
```

## 🧪 TDD 개발 과정

### Phase 1: E2E 테스트 프레임워크 구축 (0.5일)

**RED**: E2E 테스트 실패 확인
```python
# tests/e2e/test_complete_workflow.py
import pytest
import httpx
import asyncio
import tempfile
import os
from pathlib import Path

@pytest.mark.asyncio 
class TestCompleteWorkflow:
    """완전한 시스템 워크플로우 테스트"""
    
    async def test_full_rag_pipeline(self):
        """전체 RAG 파이프라인 E2E 테스트"""
        # 1. 모든 서비스 상태 확인
        await self.verify_all_services_healthy()
        
        # 2. 샘플 코드 인덱싱
        file_path = await self.create_sample_code_file()
        await self.index_code_file(file_path)
        
        # 3. 검색 수행
        search_results = await self.search_code("pandas DataFrame")
        
        # 4. 코드 생성
        generated_code = await self.generate_code_with_context(
            "CSV 파일을 읽는 함수를 만들어주세요"
        )
        
        # 5. 결과 검증
        assert len(search_results) > 0
        assert "pandas" in generated_code.lower()
        assert "csv" in generated_code.lower()
```

**GREEN**: 최소 구현
```python
async def verify_all_services_healthy(self):
    """모든 서비스 상태 확인"""
    services = {
        "embedding": "http://localhost:8001/health",
        "llm": "http://localhost:8002/health",
        "vector_db": "http://localhost:6333/health",
        "rag": "http://localhost:8000/health"
    }
    
    async with httpx.AsyncClient() as client:
        for service, url in services.items():
            response = await client.get(url, timeout=30.0)
            assert response.status_code == 200, f"{service} 서비스 비정상"
```

**REFACTOR**: 견고한 E2E 테스트 구현

### Phase 2: 성능 테스트 구현 (1일)

**RED**: 성능 테스트 실패 확인
```python
# tests/performance/test_performance.py
@pytest.mark.performance
class TestSystemPerformance:
    """시스템 성능 테스트"""
    
    async def test_search_performance(self):
        """검색 성능 테스트"""
        # 100개 동시 검색 요청
        # 평균 응답시간 < 3초
        # 95% 요청 < 5초
        pass
    
    async def test_generation_performance(self):
        """생성 성능 테스트"""
        # 10개 동시 생성 요청
        # 평균 응답시간 < 30초
        # 95% 요청 < 60초
        pass
```

**GREEN**: Locust 부하 테스트 구현
```python
# integration-tests/performance/locustfile.py
from locust import HttpUser, task, between
import random

class RAGSystemUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """테스트 시작 시 실행"""
        self.search_queries = [
            "pandas DataFrame",
            "API client",
            "database connection",
            "error handling",
            "async function"
        ]
    
    @task(3)
    def search_code(self):
        """코드 검색 태스크"""
        query = random.choice(self.search_queries)
        self.client.post("/api/v1/search/search", json={
            "query": query,
            "limit": 5
        })
    
    @task(1) 
    def generate_code(self):
        """코드 생성 태스크"""
        prompts = [
            "간단한 유틸리티 함수를 작성해주세요",
            "데이터 처리 클래스를 만들어주세요",
            "API 호출 함수를 구현해주세요"
        ]
        prompt = random.choice(prompts)
        self.client.post("/api/v1/generation/generate", json={
            "prompt": prompt,
            "max_tokens": 200
        })
```

**REFACTOR**: 성능 모니터링 대시보드 구성

### Phase 3: 장애 복구 테스트 (1일)

**RED**: 장애 시나리오 테스트 실패 확인
```python
# tests/e2e/test_failure_scenarios.py
@pytest.mark.asyncio
class TestFailureScenarios:
    """장애 시나리오 테스트"""
    
    async def test_embedding_service_failure(self):
        """임베딩 서비스 장애 시 복구"""
        # 1. 임베딩 서비스 중단
        # 2. RAG 요청 수행 (실패 예상)
        # 3. 서비스 재시작
        # 4. 복구 확인
        pass
    
    async def test_vector_db_unavailable(self):
        """Vector DB 중단 시 처리"""
        # 1. Vector DB 중단
        # 2. 검색 요청 (적절한 에러 반환)
        # 3. 서비스 재시작
        # 4. 데이터 일관성 확인
        pass
```

**GREEN**: Docker Compose 서비스 제어 구현
```python
async def stop_service(service_name: str):
    """서비스 중단"""
    import subprocess
    subprocess.run(["docker-compose", "stop", service_name])

async def start_service(service_name: str):
    """서비스 시작"""
    import subprocess
    subprocess.run(["docker-compose", "start", service_name])
```

**REFACTOR**: 자동 복구 메커니즘 검증

### Phase 4: 운영 준비성 검증 (1.5일)

**RED**: 운영 환경 배포 테스트 실패
```python
# tests/deployment/test_production_readiness.py
class TestProductionReadiness:
    """운영 준비성 테스트"""
    
    def test_configuration_validation(self):
        """설정 유효성 검증"""
        # 환경변수 검증
        # 보안 설정 확인
        # 로그 레벨 확인
        pass
    
    def test_health_checks(self):
        """헬스체크 엔드포인트 검증"""
        # 모든 서비스 헬스체크
        # 의존성 체크
        # 메트릭 수집 확인
        pass
```

**GREEN**: 운영 환경 설정 구현
```yaml
# deployment/production.yml
version: '3.8'
services:
  rag-server:
    environment:
      - LOG_LEVEL=INFO
      - METRICS_ENABLED=true
      - HEALTH_CHECK_INTERVAL=30
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**REFACTOR**: 모니터링 및 알림 시스템 구성

## 📊 성능 기준 및 SLA

### 응답 시간 목표
- **검색 API**: 평균 < 3초, 95% < 5초
- **생성 API**: 평균 < 30초, 95% < 60초
- **인덱싱 API**: 파일 1개 < 60초

### 처리량 목표
- **동시 검색 요청**: 100 RPS
- **동시 생성 요청**: 10 RPS
- **일일 인덱싱**: 1,000 파일

### 가용성 목표
- **서비스 가용성**: 99%
- **데이터 일관성**: 100%
- **평균 복구 시간**: < 5분

## 🔧 모니터링 설정

### Prometheus 메트릭
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'rag-server'
    static_configs:
      - targets: ['localhost:8000']
  - job_name: 'embedding-server'
    static_configs:
      - targets: ['localhost:8001']
```

### Grafana 대시보드
- API 응답 시간 차트
- 요청 처리량 차트
- 에러율 모니터링
- 시스템 리소스 사용률

## 🚨 알림 규칙
```yaml
# monitoring/alerts.yml
groups:
  - name: rag_system_alerts
    rules:
      - alert: HighResponseTime
        expr: avg(http_request_duration_seconds) > 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "응답 시간이 높습니다"
      
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "서비스가 중단되었습니다"
```

## 📋 검증 체크리스트

### 기능 검증
- [ ] 완전한 RAG 워크플로우 동작
- [ ] 모든 API 엔드포인트 정상 작동
- [ ] 에러 처리 및 복구 메커니즘
- [ ] 데이터 일관성 보장

### 성능 검증  
- [ ] 응답 시간 SLA 충족
- [ ] 처리량 목표 달성
- [ ] 동시 요청 처리 능력
- [ ] 메모리 사용량 적정 수준

### 운영 검증
- [ ] 헬스체크 엔드포인트 구현
- [ ] 로그 수집 및 모니터링
- [ ] 메트릭 수집 및 대시보드
- [ ] 알림 시스템 구성

### 보안 검증
- [ ] API 인증/인가 (선택적)
- [ ] 입력 데이터 검증
- [ ] 에러 메시지 보안
- [ ] 의존성 보안 취약점 점검

## ⏱️ 예상 소요 시간

### 일정별 상세 계획
- **Day 1**: E2E 테스트 프레임워크 구축 (0.5일) + 성능 테스트 구현 (0.5일)
- **Day 2**: 성능 테스트 완료 (0.5일) + 장애 복구 테스트 (0.5일)  
- **Day 3**: 장애 복구 테스트 완료 (0.5일) + 운영 준비성 검증 (0.5일)
- **Day 4**: 운영 준비성 검증 완료 (1일)

**총 소요 시간**: 4일

## 📈 최종 산출물

### 테스트 보고서
- 전체 테스트 커버리지 리포트
- 성능 벤치마크 결과
- 장애 복구 시나리오 검증 결과
- 운영 준비성 체크리스트

### 운영 가이드
- 배포 가이드
- 모니터링 가이드  
- 장애 대응 매뉴얼
- 성능 튜닝 가이드

### 설정 파일
- Docker Compose 운영 설정
- Prometheus/Grafana 설정
- CI/CD 파이프라인 설정
- 환경별 설정 템플릿

## 🔄 다음 단계
시스템 MVP 완료 및 운영 환경 배포 