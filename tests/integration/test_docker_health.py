import pytest
import requests
import time
import docker
from typing import Dict, List


class TestDockerHealth:
    """Docker 컨테이너 헬스체크 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 설정"""
        self.services = {
            'vector-db': 'http://localhost:6333/health',
            'embedding-server': 'http://localhost:8001/health',
            'llm-server': 'http://localhost:8002/health'
        }
        self.timeout = 120  # 2분 타임아웃
    
    def test_all_services_healthy(self):
        """모든 서비스가 정상적으로 시작되는지 테스트"""
        # Given: Docker Compose가 실행된 상태
        
        # When: 서비스 헬스체크 수행
        health_checks = {}
        
        for service_name, health_url in self.services.items():
            health_checks[service_name] = self._wait_for_service_health(
                service_name, health_url
            )
        
        # Then: 모든 서비스가 healthy 상태여야 함
        for service, is_healthy in health_checks.items():
            assert is_healthy, f"{service} is not healthy"
    
    def test_vector_db_health(self):
        """Vector DB 헬스체크 테스트"""
        # Given: Vector DB 서비스
        service_url = self.services['vector-db']
        
        # When: 헬스체크 요청
        is_healthy = self._wait_for_service_health('vector-db', service_url)
        
        # Then: 정상 응답
        assert is_healthy, "Vector DB is not healthy"
        
        # 추가 검증: Qdrant 특정 엔드포인트
        response = requests.get('http://localhost:6333/collections')
        assert response.status_code == 200
    
    def test_embedding_server_health(self):
        """Embedding Server 헬스체크 테스트"""
        # Given: Embedding Server 서비스
        service_url = self.services['embedding-server']
        
        # When: 헬스체크 요청
        is_healthy = self._wait_for_service_health('embedding-server', service_url)
        
        # Then: 정상 응답
        assert is_healthy, "Embedding Server is not healthy"
    
    def test_llm_server_health(self):
        """LLM Server 헬스체크 테스트"""
        # Given: LLM Server 서비스
        service_url = self.services['llm-server']
        
        # When: 헬스체크 요청
        is_healthy = self._wait_for_service_health('llm-server', service_url)
        
        # Then: 정상 응답
        assert is_healthy, "LLM Server is not healthy"
    
    def test_docker_containers_running(self):
        """Docker 컨테이너가 실행 중인지 테스트"""
        # Given: Docker 클라이언트
        client = docker.from_env()
        
        # When: 컨테이너 목록 조회
        containers = client.containers.list()
        container_names = [container.name for container in containers]
        
        # Then: 필요한 컨테이너들이 실행 중
        expected_containers = ['qdrant-server', 'embedding-server', 'llm-server']
        
        for expected_container in expected_containers:
            assert any(expected_container in name for name in container_names), \
                f"Container {expected_container} is not running"
    
    def test_container_health_status(self):
        """컨테이너 헬스 상태 테스트"""
        # Given: Docker 클라이언트
        client = docker.from_env()
        
        # When: 컨테이너 상태 확인
        containers = client.containers.list()
        
        # Then: 모든 컨테이너가 healthy 상태
        for container in containers:
            if hasattr(container.attrs['State'], 'Health'):
                health_status = container.attrs['State']['Health']['Status']
                assert health_status in ['healthy', 'starting'], \
                    f"Container {container.name} is {health_status}"
    
    def _wait_for_service_health(self, service_name: str, service_url: str) -> bool:
        """서비스가 healthy 상태가 될 때까지 대기"""
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            try:
                response = requests.get(service_url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {service_name} is healthy")
                    return True
            except requests.exceptions.RequestException as e:
                print(f"⏳ Waiting for {service_name}... ({e})")
            
            time.sleep(5)
        
        print(f"❌ {service_name} health check timeout")
        return False 