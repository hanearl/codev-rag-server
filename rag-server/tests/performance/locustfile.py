#!/usr/bin/env python3
"""
RAG 시스템 성능 테스트 - Locust
실제 구현된 엔드포인트에 맞춰 수정됨
"""

from locust import HttpUser, task, between
import random
import json


class RAGSystemUser(HttpUser):
    """일반 사용자 행동 시뮬레이션"""
    wait_time = between(1, 3)
    host = "http://localhost:8000"
    
    def on_start(self):
        """테스트 시작 시 실행"""
        self.search_queries = [
            "pandas DataFrame 처리",
            "API 클라이언트 구현", 
            "데이터베이스 연결",
            "에러 핸들링",
            "비동기 함수",
            "파일 입출력",
            "JSON 파싱",
            "HTTP 요청",
            "데이터 변환",
            "테스트 함수"
        ]
        
        self.generation_prompts = [
            "간단한 유틸리티 함수를 작성해주세요",
            "데이터 처리 클래스를 만들어주세요", 
            "API 호출 함수를 구현해주세요",
            "파일 입출력 함수를 작성해주세요",
            "Hello World 함수를 만들어주세요",
            "간단한 계산기 함수를 작성해주세요"
        ]
        
        self.languages = ["python", "javascript", "java"]
    
    @task(4)
    def search_code(self):
        """코드 검색 태스크 (높은 빈도)"""
        query = random.choice(self.search_queries)
        response = self.client.post("/api/v1/search/", json={
            "query": query,
            "limit": random.randint(3, 10),
            "vector_weight": random.uniform(0.5, 0.8),
            "keyword_weight": random.uniform(0.2, 0.5)
        })
        
        if response.status_code == 200:
            results = response.json()
            # 검색 결과 수 확인
            result_count = len(results.get("results", []))
            if result_count > 0:
                self.client.events.request.fire(
                    request_type="POST",
                    name="/api/v1/search/ (with results)",
                    response_time=response.elapsed.total_seconds() * 1000,
                    response_length=len(response.content)
                )
    
    @task(1) 
    def generate_code(self):
        """코드 생성 태스크 (낮은 빈도)"""
        prompt = random.choice(self.generation_prompts)
        language = random.choice(self.languages)
        
        self.client.post("/api/v1/generate/", json={
            "query": prompt,
            "language": language,
            "max_tokens": random.randint(100, 300),
            "temperature": random.uniform(0.3, 0.8)
        }, timeout=60)  # 생성은 시간이 걸릴 수 있음
    
    @task(3)
    def health_check(self):
        """헬스체크 태스크"""
        self.client.get("/health")
    
    @task(2)
    def api_documentation(self):
        """API 문서 접근"""
        endpoints = ["/docs", "/openapi.json", "/redoc"]
        endpoint = random.choice(endpoints)
        self.client.get(endpoint)
    
    @task(1)
    def service_health_checks(self):
        """개별 서비스 헬스체크"""
        services = [
            "/api/v1/generate/health",
            "/api/v1/search/health", 
            "/api/v1/indexing/health"
        ]
        service = random.choice(services)
        self.client.get(service)
    
    @task(1)
    def get_supported_languages(self):
        """지원 언어 목록 조회"""
        self.client.get("/api/v1/generate/languages")
    
    @task(1)
    def get_prompt_templates(self):
        """프롬프트 템플릿 목록 조회"""
        self.client.get("/api/v1/prompts/templates")


class HeavyLoadUser(HttpUser):
    """고부하 테스트용 사용자"""
    wait_time = between(0.5, 1.5)
    host = "http://localhost:8000"
    
    def on_start(self):
        """테스트 시작 시 실행"""
        self.search_queries = [
            "function", "class", "import", "def", "async", 
            "return", "if", "for", "while", "try"
        ]
    
    @task(5)
    def rapid_search(self):
        """빠른 연속 검색"""
        query = random.choice(self.search_queries)
        self.client.post("/api/v1/search/", json={
            "query": query,
            "limit": 5
        })
    
    @task(2)
    def health_check(self):
        """빈번한 헬스체크"""
        self.client.get("/health")
    
    @task(1)
    def concurrent_generation(self):
        """동시 코드 생성 요청"""
        self.client.post("/api/v1/generate/", json={
            "query": "simple function", 
            "language": "python",
            "max_tokens": 100
        }, timeout=30)


class SearchOnlyUser(HttpUser):
    """검색 전용 사용자"""
    wait_time = between(0.1, 0.5)
    host = "http://localhost:8000"
    
    def on_start(self):
        """테스트 시작 시 실행"""
        self.queries = [
            "", "a", "function", "class", "import", "def", "async",
            "pandas", "numpy", "requests", "json", "api", "database",
            "file", "data", "process", "handle", "create", "update"
        ]
    
    @task(1)
    def search_performance(self):
        """검색 성능 테스트"""
        query = random.choice(self.queries)
        self.client.post("/api/v1/search/", json={
            "query": query,
            "limit": random.randint(1, 20)
        })


# Locust 설정
class WebsiteUser(HttpUser):
    """기본 웹사이트 사용자 (실제 사용 패턴)"""
    wait_time = between(2, 8)
    host = "http://localhost:8000"
    
    tasks = {
        RAGSystemUser: 3,  # 70% - 일반 사용자
        SearchOnlyUser: 2,  # 20% - 검색 중심 사용자  
        HeavyLoadUser: 1   # 10% - 고부하 사용자
    }
    
    def on_start(self):
        """사용자 세션 시작"""
        # 세션 시작 시 기본 확인
        self.client.get("/health")
        self.client.get("/docs")
    
    def on_stop(self):
        """사용자 세션 종료"""
        # 세션 종료 시 정리
        pass


if __name__ == "__main__":
    # 단독 실행 시 기본 설정
    import os
    os.system("locust -f locustfile.py --host=http://localhost:8000") 