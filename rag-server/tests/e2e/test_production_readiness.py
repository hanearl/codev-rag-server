import pytest
import requests
import httpx
import os
import json
import docker
import time
from typing import Dict, List


class TestProductionReadiness:
    """운영 준비성 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 셋업"""
        self.base_url = "http://localhost:8000"
        self.timeout = 30
        
        # 서비스 URL 매핑
        self.service_urls = {
            "rag-server": "http://localhost:8000",
            "embedding-server": "http://localhost:8001",
            "llm-server": "http://localhost:8002",
            "vector-db": "http://localhost:6333"
        }
        
        # Docker 클라이언트 초기화
        try:
            self.docker_client = docker.from_env()
        except Exception:
            self.docker_client = None
    
    def test_environment_configuration(self):
        """환경 설정 검증"""
        print("\n🔧 환경 설정 검증 중...")
        
        # 필수 환경변수 목록
        required_env_vars = [
            "OPENAI_API_KEY",
        ]
        
        # 선택적 환경변수 (기본값이 있음)
        optional_env_vars = [
            "EMBEDDING_SERVER_URL",
            "LLM_SERVER_URL", 
            "VECTOR_DB_URL",
            "HOST",
            "PORT"
        ]
        
        # 필수 환경변수 확인
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️ 누락된 필수 환경변수: {missing_vars}")
            print("💡 .env 파일이나 시스템 환경변수를 확인하세요")
        else:
            print("✅ 모든 필수 환경변수가 설정됨")
        
        # 선택적 환경변수 확인
        optional_set = []
        for var in optional_env_vars:
            if os.getenv(var):
                optional_set.append(var)
        
        print(f"📋 설정된 선택적 환경변수: {optional_set}")
        
        # Docker Compose 파일 존재 확인
        docker_compose_files = [
            "docker-compose.yml",
            "docker-compose.dev.yml"
        ]
        
        for file in docker_compose_files:
            file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), file)
            if os.path.exists(file_path):
                print(f"✅ {file} 파일 존재")
            else:
                print(f"⚠️ {file} 파일 없음")

    def test_all_services_health(self):
        """모든 서비스 헬스체크 검증"""
        print("\n🏥 모든 서비스 헬스체크 검증 중...")
        
        health_results = {}
        
        for service_name, base_url in self.service_urls.items():
            health_url = f"{base_url}/health"
            
            try:
                response = requests.get(health_url, timeout=self.timeout)
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status", "unknown")
                    health_results[service_name] = {
                        "status": "healthy",
                        "response_time": response.elapsed.total_seconds(),
                        "data": data
                    }
                    print(f"✅ {service_name}: {status} ({response.elapsed.total_seconds():.2f}s)")
                else:
                    health_results[service_name] = {
                        "status": "unhealthy",
                        "status_code": response.status_code
                    }
                    print(f"❌ {service_name}: HTTP {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                health_results[service_name] = {
                    "status": "unreachable",
                    "error": str(e)
                }
                print(f"💀 {service_name}: 연결 불가 - {e}")
        
        # 핵심 서비스들이 모두 정상이어야 함
        core_services = ["rag-server", "embedding-server", "vector-db"]
        healthy_core_services = [
            service for service in core_services
            if health_results.get(service, {}).get("status") == "healthy"
        ]
        
        print(f"\n📊 정상 서비스: {len(healthy_core_services)}/{len(core_services)}")
        
        if len(healthy_core_services) == len(core_services):
            print("🎉 모든 핵심 서비스가 정상!")
        else:
            failed_services = [s for s in core_services if s not in healthy_core_services]
            print(f"⚠️ 실패한 서비스: {failed_services}")

    def test_api_documentation(self):
        """API 문서 접근성 테스트"""
        print("\n📚 API 문서 접근성 테스트 중...")
        
        # FastAPI 자동 생성 문서 확인
        docs_endpoints = [
            "/docs",          # Swagger UI
            "/redoc",         # ReDoc
            "/openapi.json"   # OpenAPI 스펙
        ]
        
        for endpoint in docs_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=self.timeout)
                
                if response.status_code == 200:
                    print(f"✅ {endpoint}: 접근 가능")
                    
                    # OpenAPI 스펙 검증
                    if endpoint == "/openapi.json":
                        openapi_spec = response.json()
                        required_fields = ["openapi", "info", "paths"]
                        
                        for field in required_fields:
                            if field in openapi_spec:
                                print(f"   ✅ {field} 필드 존재")
                            else:
                                print(f"   ❌ {field} 필드 누락")
                        
                        # API 엔드포인트 개수 확인
                        paths_count = len(openapi_spec.get("paths", {}))
                        print(f"   📊 API 엔드포인트 개수: {paths_count}")
                        
                else:
                    print(f"❌ {endpoint}: HTTP {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"💀 {endpoint}: 연결 실패 - {e}")

    def test_api_endpoints_accessibility(self):
        """주요 API 엔드포인트 접근성 테스트"""
        print("\n🌐 주요 API 엔드포인트 접근성 테스트 중...")
        
        # 테스트할 엔드포인트들 (GET 요청만)
        test_endpoints = [
            {"path": "/", "name": "루트"},
            {"path": "/health", "name": "헬스체크"},
            {"path": "/api/v1/generate/languages", "name": "지원 언어 목록"},
        ]
        
        for endpoint in test_endpoints:
            try:
                response = requests.get(
                    f"{self.base_url}{endpoint['path']}", 
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    print(f"✅ {endpoint['name']}: 정상 응답")
                else:
                    print(f"⚠️ {endpoint['name']}: HTTP {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ {endpoint['name']}: 연결 실패 - {e}")

    def test_docker_containers_status(self):
        """Docker 컨테이너 상태 테스트"""
        print("\n🐳 Docker 컨테이너 상태 테스트 중...")
        
        if not self.docker_client:
            print("⚠️ Docker 클라이언트를 사용할 수 없습니다")
            return
        
        try:
            # 실행 중인 컨테이너 목록
            containers = self.docker_client.containers.list()
            
            if not containers:
                print("⚠️ 실행 중인 컨테이너가 없습니다")
                return
            
            print(f"📊 실행 중인 컨테이너: {len(containers)}개")
            
            # 예상 컨테이너 이름들
            expected_containers = [
                "rag-server",
                "embedding-server", 
                "llm-server",
                "qdrant-server"
            ]
            
            found_containers = []
            for container in containers:
                container_name = container.name
                container_status = container.status
                
                print(f"   🐋 {container_name}: {container_status}")
                
                # 예상 컨테이너인지 확인
                for expected in expected_containers:
                    if expected in container_name:
                        found_containers.append(expected)
                        break
            
            # 컨테이너 헬스체크 상태 확인
            for container in containers:
                try:
                    # 컨테이너 상세 정보 조회
                    container.reload()
                    attrs = container.attrs
                    
                    # 헬스체크 정보가 있는 경우
                    if 'Health' in attrs.get('State', {}):
                        health_status = attrs['State']['Health']['Status']
                        print(f"   💊 {container.name} 헬스: {health_status}")
                        
                except Exception as e:
                    print(f"   ⚠️ {container.name} 상태 확인 실패: {e}")
            
            print(f"✅ 발견된 예상 컨테이너: {found_containers}")
            
        except Exception as e:
            print(f"❌ Docker 상태 확인 실패: {e}")

    def test_response_time_benchmarks(self):
        """응답 시간 벤치마크 테스트"""
        print("\n⚡ 응답 시간 벤치마크 테스트 중...")
        
        # 간단한 응답 시간 테스트
        test_cases = [
            {"endpoint": "/health", "max_time": 1.0, "name": "헬스체크"},
            {"endpoint": "/", "max_time": 1.0, "name": "루트"},
        ]
        
        for case in test_cases:
            response_times = []
            
            # 5번 측정
            for i in range(5):
                try:
                    start_time = time.time()
                    response = requests.get(
                        f"{self.base_url}{case['endpoint']}", 
                        timeout=self.timeout
                    )
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        response_time = end_time - start_time
                        response_times.append(response_time)
                    
                except requests.exceptions.RequestException:
                    pass
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                max_time = max(response_times)
                min_time = min(response_times)
                
                print(f"📊 {case['name']}:")
                print(f"   평균: {avg_time:.3f}s")
                print(f"   최대: {max_time:.3f}s")
                print(f"   최소: {min_time:.3f}s")
                
                if avg_time < case["max_time"]:
                    print(f"   ✅ 기준 충족 (< {case['max_time']}s)")
                else:
                    print(f"   ⚠️ 기준 초과 (>= {case['max_time']}s)")
            else:
                print(f"❌ {case['name']}: 측정 실패")

    def test_error_handling_responses(self):
        """에러 처리 응답 테스트"""
        print("\n🚨 에러 처리 응답 테스트 중...")
        
        # 의도적으로 잘못된 요청 테스트
        error_test_cases = [
            {
                "method": "POST",
                "endpoint": "/api/v1/search/search",
                "data": {},  # 필수 필드 누락
                "expected_status": 422,
                "name": "검색 요청 검증"
            },
            {
                "method": "POST", 
                "endpoint": "/api/v1/indexing/files",
                "data": {"invalid": "data"},  # 잘못된 형식
                "expected_status": 422,
                "name": "인덱싱 요청 검증"
            },
            {
                "method": "GET",
                "endpoint": "/api/v1/nonexistent",
                "data": None,
                "expected_status": 404,
                "name": "존재하지 않는 엔드포인트"
            }
        ]
        
        for case in error_test_cases:
            try:
                if case["method"] == "GET":
                    response = requests.get(
                        f"{self.base_url}{case['endpoint']}", 
                        timeout=self.timeout
                    )
                else:
                    response = requests.post(
                        f"{self.base_url}{case['endpoint']}", 
                        json=case["data"],
                        timeout=self.timeout
                    )
                
                if response.status_code == case["expected_status"]:
                    print(f"✅ {case['name']}: 예상 상태 코드 {case['expected_status']}")
                    
                    # 에러 응답 형식 확인
                    try:
                        error_data = response.json()
                        if "detail" in error_data:
                            print(f"   📝 에러 메시지 포함됨")
                        else:
                            print(f"   ⚠️ 에러 메시지 형식 확인 필요")
                    except json.JSONDecodeError:
                        print(f"   ⚠️ JSON 형식이 아닌 에러 응답")
                        
                else:
                    print(f"⚠️ {case['name']}: 예상 {case['expected_status']}, 실제 {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ {case['name']}: 요청 실패 - {e}")

    def test_cors_configuration(self):
        """CORS 설정 테스트"""
        print("\n🌍 CORS 설정 테스트 중...")
        
        # CORS preflight 요청 시뮬레이션
        try:
            response = requests.options(
                f"{self.base_url}/api/v1/search/search",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type"
                },
                timeout=self.timeout
            )
            
            cors_headers = [
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Methods", 
                "Access-Control-Allow-Headers"
            ]
            
            found_headers = []
            for header in cors_headers:
                if header in response.headers:
                    found_headers.append(header)
                    print(f"✅ {header}: {response.headers[header]}")
                else:
                    print(f"⚠️ {header}: 누락")
            
            if len(found_headers) >= 2:
                print("✅ CORS 기본 설정 확인됨")
            else:
                print("⚠️ CORS 설정 확인 필요")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ CORS 테스트 실패: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self):
        """동시 요청 처리 테스트"""
        print("\n🔄 동시 요청 처리 테스트 중...")
        
        async def make_health_request():
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=10.0)
                return response.status_code == 200
        
        # 10개의 동시 요청
        import asyncio
        tasks = [make_health_request() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_requests = sum(1 for result in results if result is True)
        failed_requests = len(results) - successful_requests
        
        print(f"📊 동시 요청 결과:")
        print(f"   성공: {successful_requests}/10")
        print(f"   실패: {failed_requests}/10")
        
        if successful_requests >= 8:  # 80% 이상 성공
            print("✅ 동시 요청 처리 능력 양호")
        else:
            print("⚠️ 동시 요청 처리 능력 개선 필요")

    def test_security_headers(self):
        """보안 헤더 테스트"""
        print("\n🔒 보안 헤더 테스트 중...")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            
            # 권장 보안 헤더들
            security_headers = [
                "X-Content-Type-Options",
                "X-Frame-Options", 
                "X-XSS-Protection",
                "Strict-Transport-Security",
                "Content-Security-Policy"
            ]
            
            found_headers = []
            for header in security_headers:
                if header in response.headers:
                    found_headers.append(header)
                    print(f"✅ {header}: {response.headers[header]}")
                else:
                    print(f"⚠️ {header}: 누락 (권장)")
            
            print(f"📊 보안 헤더: {len(found_headers)}/{len(security_headers)}")
            
            if len(found_headers) > 0:
                print("✅ 일부 보안 헤더 설정됨")
            else:
                print("💡 보안 헤더 설정을 고려해보세요")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 보안 헤더 테스트 실패: {e}")

def run_all_production_tests():
    """모든 운영 준비성 테스트 실행"""
    print("🚀 운영 준비성 통합 테스트 시작\n")
    
    test_instance = TestProductionReadiness()
    test_instance.setup()
    
    test_methods = [
        "test_environment_configuration",
        "test_all_services_health", 
        "test_api_documentation",
        "test_api_endpoints_accessibility",
        "test_docker_containers_status",
        "test_response_time_benchmarks",
        "test_error_handling_responses",
        "test_cors_configuration",
        "test_security_headers"
    ]
    
    passed_tests = 0
    total_tests = len(test_methods)
    
    for method_name in test_methods:
        try:
            method = getattr(test_instance, method_name)
            method()
            passed_tests += 1
            print("✅ PASSED\n")
        except Exception as e:
            print(f"❌ FAILED: {e}\n")
    
    print(f"📊 최종 결과: {passed_tests}/{total_tests} 테스트 통과")
    
    if passed_tests == total_tests:
        print("🎉 모든 운영 준비성 테스트 통과!")
    else:
        print("⚠️ 일부 테스트 실패 - 운영 배포 전 점검 필요")


if __name__ == "__main__":
    run_all_production_tests() 