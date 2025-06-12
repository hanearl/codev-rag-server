import pytest
import httpx
import asyncio
import subprocess
import time
import docker
import os
from typing import Dict, Optional


@pytest.mark.asyncio
class TestFailureScenarios:
    """장애 시나리오 및 복구 테스트"""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """테스트 셋업"""
        self.base_url = "http://localhost:8000"
        self.timeout = 60
        self.max_retry = 5
        self.retry_delay = 10
        
        # Docker 클라이언트 초기화
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            pytest.skip(f"Docker가 사용할 수 없습니다: {e}")
    
    async def test_embedding_service_failure_recovery(self):
        """임베딩 서비스 장애 및 복구 테스트"""
        print("\n🔧 임베딩 서비스 장애 복구 테스트 시작")
        
        # 초기 상태 확인
        await self.verify_service_health("embedding-server")
        
        try:
            # 1. 임베딩 서비스 중단
            print("⚠️ 임베딩 서비스 중단 중...")
            await self.stop_service("embedding-server")
            await asyncio.sleep(5)  # 서비스 중단 대기
            
            # 2. 인덱싱 요청 실패 확인
            print("❌ 인덱싱 요청 실패 확인 중...")
            with pytest.raises((httpx.HTTPStatusError, httpx.RequestError)):
                await self.index_sample_code()
            print("✅ 예상대로 인덱싱 실패")
            
            # 3. RAG 서비스는 여전히 살아있어야 함
            await self.verify_service_health("rag-server")
            
            # 4. 임베딩 서비스 재시작
            print("🔄 임베딩 서비스 재시작 중...")
            await self.start_service("embedding-server")
            await self.wait_for_service_health("embedding-server")
            
            # 5. 복구 후 정상 작동 확인
            print("✅ 복구 후 정상 작동 확인 중...")
            await self.index_sample_code()
            print("🎉 임베딩 서비스 장애 복구 테스트 성공!")
            
        except Exception as e:
            print(f"테스트 중 오류 발생: {e}")
            # 복구 시도
            await self.start_service("embedding-server")
            raise

    async def test_vector_db_failure_recovery(self):
        """Vector DB 장애 및 복구 테스트"""
        print("\n🗄️ Vector DB 장애 복구 테스트 시작")
        
        # 초기 상태 확인
        await self.verify_service_health("vector-db")
        
        try:
            # 1. Vector DB 중단
            print("⚠️ Vector DB 중단 중...")
            await self.stop_service("vector-db")
            await asyncio.sleep(5)
            
            # 2. 검색 요청 실패 확인
            print("❌ 검색 요청 실패 확인 중...")
            search_failed = False
            try:
                await self.search_code_with_timeout("test query")
            except (httpx.HTTPStatusError, httpx.RequestError):
                search_failed = True
            
            assert search_failed, "Vector DB 중단 시 검색이 실패해야 합니다"
            print("✅ 예상대로 검색 실패")
            
            # 3. Vector DB 재시작
            print("🔄 Vector DB 재시작 중...")
            await self.start_service("vector-db")
            await self.wait_for_service_health("vector-db")
            
            # 4. 복구 후 검색 가능 확인
            print("✅ 복구 후 검색 기능 확인 중...")
            results = await self.search_code_with_timeout("test query")
            # 결과가 없어도 에러가 발생하지 않으면 성공
            assert isinstance(results, list), "검색 결과가 리스트 형태여야 합니다"
            print("🎉 Vector DB 장애 복구 테스트 성공!")
            
        except Exception as e:
            print(f"테스트 중 오류 발생: {e}")
            # 복구 시도
            await self.start_service("vector-db")
            raise

    async def test_llm_service_failure_recovery(self):
        """LLM 서비스 장애 및 복구 테스트"""
        print("\n🤖 LLM 서비스 장애 복구 테스트 시작")
        
        # 초기 상태 확인
        await self.verify_service_health("llm-server")
        
        try:
            # 1. LLM 서비스 중단
            print("⚠️ LLM 서비스 중단 중...")
            await self.stop_service("llm-server")
            await asyncio.sleep(5)
            
            # 2. 코드 생성 요청 실패 확인
            print("❌ 코드 생성 요청 실패 확인 중...")
            generation_failed = False
            try:
                await self.generate_code_with_timeout("간단한 함수 작성")
            except (httpx.HTTPStatusError, httpx.RequestError):
                generation_failed = True
                
            assert generation_failed, "LLM 서비스 중단 시 코드 생성이 실패해야 합니다"
            print("✅ 예상대로 코드 생성 실패")
            
            # 3. 검색은 여전히 가능해야 함
            try:
                await self.search_code_with_timeout("test query")
                print("✅ 검색 기능은 정상 작동")
            except Exception:
                print("⚠️ 검색 기능도 영향을 받음")
            
            # 4. LLM 서비스 재시작
            print("🔄 LLM 서비스 재시작 중...")
            await self.start_service("llm-server")
            await self.wait_for_service_health("llm-server")
            
            # 5. 복구 후 코드 생성 가능 확인
            print("✅ 복구 후 코드 생성 기능 확인 중...")
            generated_code = await self.generate_code_with_timeout("Hello World 함수")
            assert isinstance(generated_code, str) and len(generated_code) > 0, \
                "생성된 코드가 유효해야 합니다"
            print("🎉 LLM 서비스 장애 복구 테스트 성공!")
            
        except Exception as e:
            print(f"테스트 중 오류 발생: {e}")
            # 복구 시도
            await self.start_service("llm-server")
            raise

    async def test_multiple_service_failure(self):
        """다중 서비스 장애 테스트"""
        print("\n💥 다중 서비스 장애 테스트 시작")
        
        services_to_test = ["embedding-server", "llm-server"]
        
        try:
            # 1. 여러 서비스 동시 중단
            print("⚠️ 여러 서비스 동시 중단 중...")
            for service in services_to_test:
                await self.stop_service(service)
            
            await asyncio.sleep(10)  # 모든 서비스 중단 대기
            
            # 2. RAG 서버 상태 확인 (여전히 살아있어야 함)
            await self.verify_service_health("rag-server")
            print("✅ RAG 서버는 여전히 응답 중")
            
            # 3. 모든 서비스 재시작
            print("🔄 모든 서비스 재시작 중...")
            for service in services_to_test:
                await self.start_service(service)
            
            # 4. 모든 서비스 복구 대기
            for service in services_to_test:
                await self.wait_for_service_health(service)
            
            # 5. 전체 시스템 정상 작동 확인
            print("✅ 전체 시스템 정상 작동 확인 중...")
            await self.verify_full_pipeline()
            print("🎉 다중 서비스 장애 복구 테스트 성공!")
            
        except Exception as e:
            print(f"테스트 중 오류 발생: {e}")
            # 모든 서비스 복구 시도
            for service in services_to_test:
                await self.start_service(service)
            raise

    async def test_network_partition_simulation(self):
        """네트워크 분할 시뮬레이션 테스트"""
        print("\n🌐 네트워크 분할 시뮬레이션 테스트 시작")
        
        # 네트워크 문제 시뮬레이션을 위해 잘못된 URL로 요청
        original_base_url = self.base_url
        
        try:
            # 잘못된 포트로 요청
            self.base_url = "http://localhost:9999"  # 존재하지 않는 포트
            
            # 연결 실패 확인
            connection_failed = False
            try:
                async with httpx.AsyncClient() as client:
                    await client.get(f"{self.base_url}/health", timeout=5.0)
            except (httpx.ConnectError, httpx.TimeoutException):
                connection_failed = True
            
            assert connection_failed, "네트워크 연결이 실패해야 합니다"
            print("✅ 네트워크 연결 실패 시뮬레이션 성공")
            
            # 원래 URL로 복구
            self.base_url = original_base_url
            
            # 복구 후 정상 연결 확인
            await self.verify_service_health("rag-server")
            print("🎉 네트워크 복구 시뮬레이션 성공!")
            
        finally:
            self.base_url = original_base_url

    # Helper 메서드들
    async def stop_service(self, service_name: str):
        """Docker Compose 서비스 중단"""
        result = subprocess.run(
            ["docker-compose", "stop", service_name],
            capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to stop {service_name}: {result.stderr}")
        print(f"🛑 {service_name} 서비스 중단됨")

    async def start_service(self, service_name: str):
        """Docker Compose 서비스 시작"""
        result = subprocess.run(
            ["docker-compose", "start", service_name],
            capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start {service_name}: {result.stderr}")
        print(f"🟢 {service_name} 서비스 시작됨")

    async def wait_for_service_health(self, service_name: str, max_wait: int = 120):
        """서비스가 정상 상태가 될 때까지 대기"""
        health_urls = {
            "embedding-server": "http://localhost:8001/health",
            "llm-server": "http://localhost:8002/health",
            "vector-db": "http://localhost:6333/health",
            "rag-server": "http://localhost:8000/health"
        }
        
        url = health_urls.get(service_name)
        if not url:
            raise ValueError(f"Unknown service: {service_name}")
        
        print(f"⏳ {service_name} 헬스체크 대기 중...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=10.0)
                    if response.status_code == 200:
                        print(f"✅ {service_name} 정상 상태 확인")
                        return True
            except (httpx.RequestError, httpx.HTTPStatusError):
                pass
            
            await asyncio.sleep(5)
        
        raise TimeoutError(f"Service {service_name} did not become healthy in {max_wait}s")

    async def verify_service_health(self, service_name: str):
        """서비스 헬스체크 검증"""
        health_urls = {
            "embedding-server": "http://localhost:8001/health",
            "llm-server": "http://localhost:8002/health", 
            "vector-db": "http://localhost:6333/health",
            "rag-server": "http://localhost:8000/health"
        }
        
        url = health_urls.get(service_name)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            assert response.status_code == 200, f"{service_name} 헬스체크 실패"

    async def index_sample_code(self):
        """샘플 코드 인덱싱"""
        sample_code = '''
def hello_world():
    """간단한 Hello World 함수"""
    return "Hello, World!"
'''
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
            f"{self.base_url}/api/v1/indexing/file",
                json={
                    "file_path": "test_sample.py",
                    "content": sample_code,
                    "language": "python"
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

    async def search_code_with_timeout(self, query: str) -> list:
        """타임아웃을 가진 코드 검색"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/search/search",
                json={"query": query, "limit": 3},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()["results"]

    async def generate_code_with_timeout(self, prompt: str) -> str:
        """타임아웃을 가진 코드 생성"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/generate/",
                json={
                    "query": prompt,
                    "language": "python",
                    "max_tokens": 100
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            return result.get("generated_code", result.get("code", ""))

    async def verify_full_pipeline(self):
        """전체 파이프라인 검증"""
        # 간단한 전체 워크플로우 테스트
        await self.index_sample_code()
        await self.search_code_with_timeout("hello")
        await self.generate_code_with_timeout("간단한 함수") 