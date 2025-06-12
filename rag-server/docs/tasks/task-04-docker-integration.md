# Task 04: Docker Compose 통합

## 📋 개요
**목표**: 전체 마이크로서비스 시스템의 컨테이너화 및 서비스 간 통신 구성  
**소요시간**: 2일  
**담당자**: Backend Developer + DevOps  
**우선순위**: High (RAG Server 구현 전 필수)

## 🎯 목표
개별적으로 구현된 마이크로서비스들을 Docker Compose로 통합하여 개발 환경을 구성하고, RAG Server 구현 시 필요한 integration 테스트 환경을 제공합니다.

## 📚 사전 요구사항
- Task 01-03 완료 (Embedding Server, LLM Server, Vector DB)
- Docker, Docker Compose 설치
- 각 서비스의 Dockerfile 준비 완료

## 🏗️ 구현 사항

### 1. Docker Compose 설정
```yaml
# docker-compose.yml
version: '3.8'

services:
  vector-db:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - ./data/qdrant:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333

  embedding-server:
    build: ./embedding-server
    ports:
      - "8001:8001"
    volumes:
      - ./embedding-server:/app
    environment:
      - MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
      - HOST=0.0.0.0
      - PORT=8001
    depends_on:
      - vector-db

  llm-server:
    build: ./llm-server
    ports:
      - "8002:8002"
    volumes:
      - ./llm-server:/app
    environment:
      - MODEL_NAME=gpt-4o-mini
      - HOST=0.0.0.0
      - PORT=8002
      - OPENAI_API_KEY=${OPENAI_API_KEY}

  rag-server:
    build: ./rag-server
    ports:
      - "8000:8000"
    volumes:
      - ./rag-server:/app
      - ./test-codebase:/test-codebase:ro
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - EMBEDDING_SERVER_URL=http://embedding-server:8001
      - LLM_SERVER_URL=http://llm-server:8002
      - VECTOR_DB_URL=http://vector-db:6333
    depends_on:
      - embedding-server
      - llm-server
      - vector-db
```

### 2. 개발 환경 설정
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  vector-db:
    extends:
      file: docker-compose.yml
      service: vector-db

  embedding-server:
    extends:
      file: docker-compose.yml
      service: embedding-server
    volumes:
      - ./embedding-server:/app
      - /app/.venv  # 가상환경 제외
    command: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

  llm-server:
    extends:
      file: docker-compose.yml
      service: llm-server
    volumes:
      - ./llm-server:/app
      - /app/.venv
    command: uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

  rag-server:
    extends:
      file: docker-compose.yml
      service: rag-server
    volumes:
      - ./rag-server:/app
      - ./test-codebase:/test-codebase:ro
      - /app/.venv
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 환경 변수 설정
```bash
# .env
OPENAI_API_KEY=your_openai_api_key_here

# 개발 환경 설정
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# 서비스 URL 설정 (개발용)
EMBEDDING_SERVER_URL=http://localhost:8001
LLM_SERVER_URL=http://localhost:8002
VECTOR_DB_URL=http://localhost:6333
```

### 4. 네트워크 및 볼륨 구성
```yaml
# docker-compose.yml 추가 설정
networks:
  rag-network:
    driver: bridge

volumes:
  qdrant-data:
  embedding-cache:

services:
  # ... 기존 서비스들 ...
  vector-db:
    # ... 기존 설정 ...
    volumes:
      - qdrant-data:/qdrant/storage
    networks:
      - rag-network

  embedding-server:
    # ... 기존 설정 ...
    volumes:
      - ./embedding-server:/app
      - embedding-cache:/app/cache
    networks:
      - rag-network

  # 모든 서비스에 네트워크 추가
```

## 🧪 TDD 구현

### 1. 테스트 구조
```
tests/
├── integration/
│   ├── test_service_communication.py
│   ├── test_docker_health.py
│   └── test_environment_setup.py
├── fixtures/
│   ├── docker_compose.py
│   └── test_data.py
└── conftest.py
```

### 2. 핵심 테스트 케이스

#### 🔴 Red: Docker Compose 헬스체크 테스트
```python
# tests/integration/test_docker_health.py
import pytest
import requests
import time
from docker import DockerClient

class TestDockerHealth:
    def test_all_services_healthy(self, docker_compose_up):
        """모든 서비스가 정상적으로 시작되는지 테스트"""
        # Given: Docker Compose가 실행된 상태
        
        # When: 서비스 헬스체크 수행
        services = ['embedding-server', 'llm-server', 'vector-db']
        health_checks = {}
        
        for service in services:
            health_checks[service] = self._wait_for_service_health(service)
        
        # Then: 모든 서비스가 healthy 상태여야 함
        for service, is_healthy in health_checks.items():
            assert is_healthy, f"{service} is not healthy"
    
    def _wait_for_service_health(self, service: str, timeout: int = 60) -> bool:
        """서비스가 healthy 상태가 될 때까지 대기"""
        # 서비스별 헬스체크 URL
        health_urls = {
            'embedding-server': 'http://localhost:8001/health',
            'llm-server': 'http://localhost:8002/health',
            'vector-db': 'http://localhost:6333/health'
        }
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(health_urls[service], timeout=5)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        
        return False
```

#### 🔴 Red: 서비스 간 통신 테스트
```python
# tests/integration/test_service_communication.py
import pytest
import requests

class TestServiceCommunication:
    def test_embedding_server_communication(self):
        """Embedding Server 통신 테스트"""
        # Given: Embedding Server가 실행 중
        
        # When: 텍스트 임베딩 요청
        response = requests.post(
            'http://localhost:8001/embed',
            json={'text': 'def hello_world():\n    print("Hello, World!")'}
        )
        
        # Then: 정상적인 임베딩 결과 반환
        assert response.status_code == 200
        data = response.json()
        assert 'embedding' in data
        assert len(data['embedding']) > 0
    
    def test_llm_server_communication(self):
        """LLM Server 통신 테스트"""
        # Given: LLM Server가 실행 중
        
        # When: 코드 생성 요청
        response = requests.post(
            'http://localhost:8002/chat/completions',
            json={
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'user', 'content': 'Write a simple Python function'}
                ]
            }
        )
        
        # Then: 정상적인 응답 반환
        assert response.status_code == 200
        data = response.json()
        assert 'choices' in data
    
    def test_vector_db_communication(self):
        """Vector DB 통신 테스트"""
        # Given: Vector DB가 실행 중
        
        # When: 컬렉션 리스트 요청
        response = requests.get('http://localhost:6333/collections')
        
        # Then: 정상적인 응답 반환
        assert response.status_code == 200
```

#### 🔴 Red: 환경 설정 테스트
```python
# tests/integration/test_environment_setup.py
import pytest
import os
import docker

class TestEnvironmentSetup:
    def test_environment_variables_loaded(self):
        """환경 변수가 올바르게 로드되는지 테스트"""
        # Given: Docker Compose 환경
        
        # When: 환경 변수 확인
        client = docker.from_env()
        containers = client.containers.list()
        
        # Then: 각 서비스의 환경 변수가 올바르게 설정됨
        for container in containers:
            if 'embedding-server' in container.name:
                env_vars = container.attrs['Config']['Env']
                assert any('HOST=0.0.0.0' in env for env in env_vars)
                assert any('PORT=8001' in env for env in env_vars)
    
    def test_volume_mounts(self):
        """볼륨 마운트가 올바르게 설정되는지 테스트"""
        # Given: Docker Compose 환경
        
        # When: 컨테이너 볼륨 확인
        client = docker.from_env()
        containers = client.containers.list()
        
        # Then: 각 서비스의 볼륨이 올바르게 마운트됨
        for container in containers:
            if 'rag-server' in container.name:
                mounts = container.attrs['Mounts']
                app_mount = next((m for m in mounts if m['Destination'] == '/app'), None)
                assert app_mount is not None
                assert app_mount['Type'] == 'bind'
```

### 3. 테스트 Fixtures
```python
# tests/conftest.py
import pytest
import subprocess
import time
import requests

@pytest.fixture(scope="session")
def docker_compose_up():
    """Docker Compose 환경을 시작하고 정리하는 fixture"""
    # Setup: Docker Compose 시작
    subprocess.run(['docker-compose', '-f', 'docker-compose.dev.yml', 'up', '-d'], 
                   check=True)
    
    # 서비스들이 시작될 때까지 대기
    time.sleep(30)
    
    # 모든 서비스가 ready 상태인지 확인
    _wait_for_services_ready()
    
    yield
    
    # Teardown: Docker Compose 정리
    subprocess.run(['docker-compose', '-f', 'docker-compose.dev.yml', 'down', '-v'], 
                   check=True)

def _wait_for_services_ready(timeout=120):
    """모든 서비스가 ready 상태가 될 때까지 대기"""
    services = [
        'http://localhost:8001/health',
        'http://localhost:8002/health',
        'http://localhost:6333/health'
    ]
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        ready_count = 0
        for service_url in services:
            try:
                response = requests.get(service_url, timeout=5)
                if response.status_code == 200:
                    ready_count += 1
            except requests.exceptions.RequestException:
                pass
        
        if ready_count == len(services):
            return
        
        time.sleep(5)
    
    raise TimeoutError("Services did not become ready in time")
```

## 🔧 개발 도구 설정

### 1. Makefile
```makefile
# Makefile
.PHONY: up down build test logs clean

# 개발 환경 시작
up:
	docker-compose -f docker-compose.dev.yml up -d

# 서비스 중지
down:
	docker-compose -f docker-compose.dev.yml down

# 이미지 빌드
build:
	docker-compose -f docker-compose.dev.yml build

# 통합 테스트 실행
test-integration:
	pytest tests/integration/ -v

# 로그 확인
logs:
	docker-compose -f docker-compose.dev.yml logs -f

# 특정 서비스 로그
logs-embedding:
	docker-compose -f docker-compose.dev.yml logs -f embedding-server

logs-llm:
	docker-compose -f docker-compose.dev.yml logs -f llm-server

logs-vector:
	docker-compose -f docker-compose.dev.yml logs -f vector-db

# 환경 정리
clean:
	docker-compose -f docker-compose.dev.yml down -v
	docker system prune -f
```

### 2. 스크립트 설정
```bash
#!/bin/bash
# scripts/setup-dev.sh

echo "🚀 개발 환경 설정 시작..."

# 환경 변수 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다. .env.example을 참고하여 생성해주세요."
    exit 1
fi

# Docker Compose 파일 검증
docker-compose -f docker-compose.dev.yml config

# 서비스 시작
echo "📦 Docker Compose 서비스 시작..."
docker-compose -f docker-compose.dev.yml up -d

# 서비스 헬스체크
echo "🔍 서비스 헬스체크..."
./scripts/health-check.sh

echo "✅ 개발 환경 설정 완료!"
echo "🌐 서비스 URL:"
echo "  - Embedding Server: http://localhost:8001"
echo "  - LLM Server: http://localhost:8002"
echo "  - Vector DB: http://localhost:6333"
echo "  - RAG Server: http://localhost:8000 (구현 후)"
```

```bash
#!/bin/bash
# scripts/health-check.sh

services=(
    "http://localhost:8001/health"
    "http://localhost:8002/health"
    "http://localhost:6333/health"
)

for service in "${services[@]}"; do
    echo "⏳ $service 헬스체크 중..."
    
    for i in {1..30}; do
        if curl -f -s "$service" > /dev/null; then
            echo "✅ $service 정상"
            break
        fi
        
        if [ $i -eq 30 ]; then
            echo "❌ $service 헬스체크 실패"
            exit 1
        fi
        
        sleep 2
    done
done

echo "🎉 모든 서비스 정상 동작!"
```

## 📊 성공 기준
1. **서비스 시작**: 모든 마이크로서비스가 Docker Compose로 정상 시작
2. **네트워크 통신**: 서비스 간 HTTP 통신 정상 동작
3. **볼륨 마운트**: 코드 변경사항이 실시간 반영
4. **환경 설정**: 환경 변수가 올바르게 설정 및 로드
5. **헬스체크**: 모든 서비스의 헬스체크 엔드포인트 정상 응답
6. **개발 환경**: hot-reload가 정상 동작하는 개발 환경 구성

## 📈 다음 단계
이 Task 완료 후:
- Task 05-A: RAG Server 코드 파서 구현 시작
- 모든 외부 서비스가 준비된 상태에서 integration 테스트 가능
- 실시간 코드 변경 및 테스트 환경 활용

## 🔄 TDD 사이클
1. **Red**: Docker Compose 설정 및 통신 테스트 작성 → 실패
2. **Green**: Docker Compose 파일 및 네트워크 설정 구현 → 통과
3. **Refactor**: 성능 최적화 및 개발 편의성 개선

이 Task는 RAG Server 구현의 기반이 되는 중요한 인프라 설정입니다. 