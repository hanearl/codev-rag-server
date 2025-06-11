# Task 03: Vector DB 구성

## 🎯 목표
Qdrant를 사용하여 코드 임베딩을 저장하고 검색할 수 있는 벡터 데이터베이스를 구성하고, 키워드 인덱스와 통합하여 하이브리드 검색을 지원합니다.

## 📋 MVP 범위
- Qdrant 컨테이너 설정 및 구성
- 코드 임베딩 저장 스키마 설계
- 벡터 검색 기능 구현
- 키워드 인덱스 통합 (간단한 메타데이터 필터링)
- 데이터 백업 및 복원 설정

## 🏗️ 기술 스택
- **벡터 DB**: Qdrant
- **컨테이너**: Docker
- **클라이언트**: qdrant-client (Python)
- **키워드 검색**: 메타데이터 기반 필터링
- **백업**: Qdrant 스냅샷 기능

## 📁 프로젝트 구조

```
vector-db/
├── config/
│   ├── qdrant.yaml             ← Qdrant 설정 파일
│   └── collection_config.json  ← 컬렉션 설정
├── scripts/
│   ├── init_collections.py     ← 컬렉션 초기화 스크립트
│   ├── backup.py              ← 백업 스크립트
│   └── restore.py             ← 복원 스크립트
├── tests/
│   ├── test_vector_operations.py
│   ├── test_keyword_search.py
│   └── conftest.py
├── docker-compose.yml          ← Qdrant 서비스 정의
└── README.md                   ← 설정 및 사용 가이드
```

## 🗃️ 데이터 스키마 설계

### 코드 벡터 컬렉션 구조
```json
{
  "collection_name": "code_embeddings",
  "vector_config": {
    "size": 384,
    "distance": "Cosine"
  },
  "payload_schema": {
    "file_path": "str",      // 파일 경로
    "function_name": "str",   // 함수/클래스명
    "code_type": "str",      // "function", "class", "method"
    "language": "str",       // "python", "javascript", etc.
    "code_content": "str",   // 실제 코드 내용
    "line_start": "int",     // 시작 라인 번호
    "line_end": "int",       // 종료 라인 번호
    "created_at": "str",     // 생성 시간 (ISO 8601)
    "keywords": ["str"]      // 키워드 리스트
  }
}
```

## 🐳 Docker 구성

### docker-compose.yml
```yaml
version: '3.8'
services:
  vector-db:
    image: qdrant/qdrant:v1.7.0
    container_name: qdrant-server
    ports:
      - "6333:6333"
      - "6334:6334"  # gRPC 포트
    volumes:
      - ./data/qdrant:/qdrant/storage
      - ./config/qdrant.yaml:/qdrant/config/production.yaml
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Qdrant 설정 파일
```yaml
# config/qdrant.yaml
service:
  max_request_size_mb: 32
  max_workers: 0
  enable_cors: true

storage:
  storage_path: ./storage
  snapshots_path: ./snapshots
  temp_path: ./temp

log_level: INFO

cluster:
  enabled: false

telemetry_disabled: true
```

## 🔧 컬렉션 초기화

### 컬렉션 생성 스크립트
```python
# scripts/init_collections.py
import asyncio
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, CollectionInfo
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorDBInitializer:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        
    def create_code_embeddings_collection(self):
        """코드 임베딩 컬렉션 생성"""
        collection_name = "code_embeddings"
        
        try:
            # 기존 컬렉션 확인
            collections = self.client.get_collections()
            existing_names = [col.name for col in collections.collections]
            
            if collection_name in existing_names:
                logger.info(f"컬렉션 '{collection_name}'이 이미 존재합니다.")
                return
            
            # 컬렉션 생성
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=384,  # sentence-transformers/all-MiniLM-L6-v2 차원
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"컬렉션 '{collection_name}' 생성 완료")
            
            # 인덱스 설정
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name="file_path",
                field_schema="keyword"
            )
            
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name="language",
                field_schema="keyword"
            )
            
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name="code_type",
                field_schema="keyword"
            )
            
            logger.info("페이로드 인덱스 생성 완료")
            
        except Exception as e:
            logger.error(f"컬렉션 생성 실패: {e}")
            raise
    
    def get_collection_info(self, collection_name: str = "code_embeddings"):
        """컬렉션 정보 조회"""
        try:
            info = self.client.get_collection(collection_name)
            logger.info(f"컬렉션 정보: {info}")
            return info
        except Exception as e:
            logger.error(f"컬렉션 정보 조회 실패: {e}")
            return None

def main():
    """메인 함수"""
    initializer = VectorDBInitializer()
    
    # 컬렉션 생성
    initializer.create_code_embeddings_collection()
    
    # 컬렉션 정보 확인
    initializer.get_collection_info()

if __name__ == "__main__":
    main()
```

## 🔍 벡터 검색 기능

### 벡터 연산 클래스
```python
# scripts/vector_operations.py
from typing import List, Dict, Any, Optional, Union
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, Range
import uuid
from datetime import datetime

class VectorOperations:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = "code_embeddings"
    
    def insert_code_embedding(
        self,
        embedding: List[float],
        file_path: str,
        function_name: str,
        code_content: str,
        code_type: str = "function",
        language: str = "python",
        line_start: int = 1,
        line_end: int = 1,
        keywords: Optional[List[str]] = None
    ) -> str:
        """코드 임베딩 삽입"""
        point_id = str(uuid.uuid4())
        
        payload = {
            "file_path": file_path,
            "function_name": function_name,
            "code_content": code_content,
            "code_type": code_type,
            "language": language,
            "line_start": line_start,
            "line_end": line_end,
            "created_at": datetime.utcnow().isoformat(),
            "keywords": keywords or []
        }
        
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload=payload
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        return point_id
    
    def search_similar_code(
        self,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: float = 0.7,
        language_filter: Optional[str] = None,
        code_type_filter: Optional[str] = None,
        file_path_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """유사한 코드 검색"""
        
        # 필터 구성
        filters = []
        if language_filter:
            filters.append(FieldCondition(
                key="language",
                match={"value": language_filter}
            ))
        
        if code_type_filter:
            filters.append(FieldCondition(
                key="code_type",
                match={"value": code_type_filter}
            ))
        
        if file_path_filter:
            filters.append(FieldCondition(
                key="file_path",
                match={"value": file_path_filter}
            ))
        
        search_filter = Filter(must=filters) if filters else None
        
        # 검색 실행
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True
        )
        
        # 결과 포맷팅
        results = []
        for hit in search_results:
            result = {
                "id": hit.id,
                "score": hit.score,
                "file_path": hit.payload.get("file_path"),
                "function_name": hit.payload.get("function_name"),
                "code_content": hit.payload.get("code_content"),
                "code_type": hit.payload.get("code_type"),
                "language": hit.payload.get("language"),
                "line_start": hit.payload.get("line_start"),
                "line_end": hit.payload.get("line_end"),
                "keywords": hit.payload.get("keywords", [])
            }
            results.append(result)
        
        return results
    
    def keyword_search(
        self,
        keywords: List[str],
        language: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """키워드 기반 검색"""
        
        filters = []
        
        # 키워드 필터 (OR 조건)
        for keyword in keywords:
            filters.append(FieldCondition(
                key="keywords",
                match={"value": keyword}
            ))
        
        # 언어 필터
        must_filters = []
        if language:
            must_filters.append(FieldCondition(
                key="language",
                match={"value": language}
            ))
        
        search_filter = Filter(
            should=filters,  # 키워드 중 하나라도 매치
            must=must_filters  # 반드시 만족해야 하는 조건
        )
        
        # 키워드 검색 (임베딩 없이)
        search_results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=search_filter,
            limit=limit,
            with_payload=True
        )
        
        results = []
        for point in search_results[0]:  # scroll 결과의 첫 번째 요소
            result = {
                "id": point.id,
                "file_path": point.payload.get("file_path"),
                "function_name": point.payload.get("function_name"),
                "code_content": point.payload.get("code_content"),
                "code_type": point.payload.get("code_type"),
                "language": point.payload.get("language"),
                "keywords": point.payload.get("keywords", [])
            }
            results.append(result)
        
        return results
    
    def hybrid_search(
        self,
        query_embedding: List[float],
        keywords: List[str],
        limit: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """하이브리드 검색 (벡터 + 키워드)"""
        
        # 벡터 검색 결과
        vector_results = self.search_similar_code(
            query_embedding=query_embedding,
            limit=limit * 2  # 더 많은 결과를 가져와서 재랭킹
        )
        
        # 키워드 검색 결과
        keyword_results = self.keyword_search(
            keywords=keywords,
            limit=limit * 2
        )
        
        # 결과 결합 및 점수 계산
        combined_results = {}
        
        # 벡터 검색 결과 추가
        for i, result in enumerate(vector_results):
            result_id = result["id"]
            vector_score = result["score"] * vector_weight
            combined_results[result_id] = {
                **result,
                "vector_score": result["score"],
                "keyword_score": 0.0,
                "combined_score": vector_score
            }
        
        # 키워드 검색 결과 추가/업데이트
        for i, result in enumerate(keyword_results):
            result_id = result["id"]
            keyword_score = (1.0 - i / len(keyword_results)) * keyword_weight
            
            if result_id in combined_results:
                combined_results[result_id]["keyword_score"] = keyword_score
                combined_results[result_id]["combined_score"] += keyword_score
            else:
                combined_results[result_id] = {
                    **result,
                    "vector_score": 0.0,
                    "keyword_score": keyword_score,
                    "combined_score": keyword_score
                }
        
        # 점수 순으로 정렬
        sorted_results = sorted(
            combined_results.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )
        
        return sorted_results[:limit]
    
    def delete_by_file_path(self, file_path: str) -> int:
        """파일 경로로 관련 벡터 삭제"""
        filter_condition = Filter(
            must=[FieldCondition(
                key="file_path",
                match={"value": file_path}
            )]
        )
        
        result = self.client.delete(
            collection_name=self.collection_name,
            points_selector=filter_condition
        )
        
        return result.operation_id
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 정보"""
        info = self.client.get_collection(self.collection_name)
        return {
            "points_count": info.points_count,
            "segments_count": info.segments_count,
            "vector_size": info.config.params.vectors.size,
            "distance": info.config.params.vectors.distance
        }
```

## 🧪 테스트 구성

### 벡터 연산 테스트
```python
# tests/test_vector_operations.py
import pytest
from scripts.vector_operations import VectorOperations
import numpy as np

@pytest.fixture
def vector_ops():
    return VectorOperations()

@pytest.fixture
def sample_embedding():
    # 384차원 랜덤 임베딩 생성
    return np.random.rand(384).tolist()

def test_insert_code_embedding_should_return_point_id(vector_ops, sample_embedding):
    """코드 임베딩 삽입 시 포인트 ID를 반환해야 함"""
    # Given
    file_path = "test/sample.py"
    function_name = "test_function"
    code_content = "def test_function():\n    pass"
    
    # When
    point_id = vector_ops.insert_code_embedding(
        embedding=sample_embedding,
        file_path=file_path,
        function_name=function_name,
        code_content=code_content,
        keywords=["test", "function"]
    )
    
    # Then
    assert point_id is not None
    assert isinstance(point_id, str)

def test_search_similar_code_should_return_results(vector_ops, sample_embedding):
    """유사한 코드 검색 시 결과를 반환해야 함"""
    # Given
    # 먼저 데이터 삽입
    vector_ops.insert_code_embedding(
        embedding=sample_embedding,
        file_path="test/example.py",
        function_name="example_function",
        code_content="def example_function():\n    return True",
        keywords=["example", "function"]
    )
    
    # When
    results = vector_ops.search_similar_code(
        query_embedding=sample_embedding,
        limit=5
    )
    
    # Then
    assert len(results) > 0
    assert "score" in results[0]
    assert "file_path" in results[0]
    assert "function_name" in results[0]

def test_keyword_search_should_return_matching_results(vector_ops, sample_embedding):
    """키워드 검색 시 매칭되는 결과를 반환해야 함"""
    # Given
    keywords = ["example", "test"]
    vector_ops.insert_code_embedding(
        embedding=sample_embedding,
        file_path="test/keyword_test.py",
        function_name="keyword_function",
        code_content="def keyword_function():\n    pass",
        keywords=keywords
    )
    
    # When
    results = vector_ops.keyword_search(keywords=["example"])
    
    # Then
    assert len(results) > 0
    first_result = results[0]
    assert "example" in first_result["keywords"]

def test_hybrid_search_should_combine_vector_and_keyword_results(vector_ops, sample_embedding):
    """하이브리드 검색 시 벡터와 키워드 결과를 결합해야 함"""
    # Given
    vector_ops.insert_code_embedding(
        embedding=sample_embedding,
        file_path="test/hybrid_test.py",
        function_name="hybrid_function",
        code_content="def hybrid_function():\n    return 'hybrid'",
        keywords=["hybrid", "test"]
    )
    
    # When
    results = vector_ops.hybrid_search(
        query_embedding=sample_embedding,
        keywords=["hybrid"],
        limit=5
    )
    
    # Then
    assert len(results) > 0
    first_result = results[0]
    assert "combined_score" in first_result
    assert "vector_score" in first_result
    assert "keyword_score" in first_result
```

## 💾 백업 및 복원

### 백업 스크립트
```python
# scripts/backup.py
import os
import shutil
from datetime import datetime
from qdrant_client import QdrantClient

class VectorDBBackup:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self.backup_dir = "./backups"
        
    def create_backup(self, collection_name: str = "code_embeddings") -> str:
        """컬렉션 백업 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.backup_dir}/{collection_name}_{timestamp}"
        
        os.makedirs(backup_path, exist_ok=True)
        
        # 스냅샷 생성
        snapshot_info = self.client.create_snapshot(collection_name)
        
        print(f"백업 완료: {backup_path}")
        return backup_path

if __name__ == "__main__":
    backup = VectorDBBackup()
    backup.create_backup()
```

## ✅ 성공 기준

### 기능적 요구사항
- [ ] Qdrant 컨테이너 정상 실행
- [ ] 코드 임베딩 컬렉션 생성 및 설정
- [ ] 벡터 검색 기능 동작
- [ ] 키워드 기반 검색 기능 동작
- [ ] 하이브리드 검색 기능 동작
- [ ] 데이터 백업 및 복원 기능

### 비기능적 요구사항
- [ ] 검색 응답 시간 < 1초 (10k 벡터 기준)
- [ ] 컨테이너 재시작 시 데이터 보존
- [ ] 적절한 메모리 사용량 (< 2GB)
- [ ] 헬스 체크 정상 동작

### 데이터 품질
- [ ] 적절한 벡터 인덱싱 성능
- [ ] 메타데이터 필터링 정확성
- [ ] 점수 계산의 일관성

## 🚀 실행 방법

### Docker Compose로 실행
```bash
# Qdrant 서비스 시작
docker-compose up -d vector-db

# 헬스 체크
curl http://localhost:6333/health

# 컬렉션 초기화
python scripts/init_collections.py
```

### 개발 환경 설정
```bash
# Python 클라이언트 설치
pip install qdrant-client

# 테스트 실행
pytest tests/test_vector_operations.py -v
```

## 📚 API 문서
- Qdrant Web UI: http://localhost:6333/dashboard
- API 문서: http://localhost:6333/docs

## 🧪 Integration 테스트 단계

### Vector DB 통합 테스트

**목표**: Qdrant Vector DB의 실제 환경 동작 및 데이터 일관성 검증

```python
# tests/integration/test_vector_db_integration.py
import pytest
import httpx
import asyncio
import random
import numpy as np

@pytest.mark.asyncio
class TestVectorDBIntegration:
    """Vector DB 통합 테스트"""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Docker Compose 환경에서 Vector DB 시작 확인"""
        async with httpx.AsyncClient() as client:
            # 서비스 준비 대기 (최대 60초)
            for _ in range(60):
                try:
                    response = await client.get("http://localhost:6333/health")
                    if response.status_code == 200:
                        break
                    await asyncio.sleep(1)
                except:
                    await asyncio.sleep(1)
            else:
                pytest.fail("Vector DB 서비스가 시작되지 않았습니다")
        
        # 테스트용 컬렉션 생성
        await self.create_test_collection()
    
    async def create_test_collection(self):
        """테스트용 컬렉션 생성"""
        async with httpx.AsyncClient() as client:
            # 기존 컬렉션 삭제 (있다면)
            await client.delete("http://localhost:6333/collections/test_collection")
            
            # 새 컬렉션 생성
            collection_config = {
                "vectors": {
                    "size": 384,  # sentence-transformers 임베딩 차원
                    "distance": "Cosine"
                }
            }
            response = await client.put(
                "http://localhost:6333/collections/test_collection",
                json=collection_config
            )
            assert response.status_code == 200
    
    async def test_collection_management(self):
        """컬렉션 관리 테스트"""
        async with httpx.AsyncClient() as client:
            # 컬렉션 리스트 조회
            response = await client.get("http://localhost:6333/collections")
            assert response.status_code == 200
            collections = response.json()
            
            collection_names = [c["name"] for c in collections["result"]["collections"]]
            assert "test_collection" in collection_names
            
            # 컬렉션 정보 조회
            response = await client.get("http://localhost:6333/collections/test_collection")
            assert response.status_code == 200
            collection_info = response.json()
            assert collection_info["result"]["config"]["params"]["vectors"]["size"] == 384
            
            print("✅ 컬렉션 관리 테스트 완료")
    
    async def test_vector_crud_operations(self):
        """벡터 CRUD 연산 테스트"""
        async with httpx.AsyncClient() as client:
            # 벡터 추가
            test_vectors = []
            for i in range(10):
                vector = {
                    "id": i,
                    "vector": [random.random() for _ in range(384)],
                    "payload": {
                        "text": f"테스트 문서 {i}",
                        "category": "test",
                        "index": i
                    }
                }
                test_vectors.append(vector)
            
            upsert_data = {"points": test_vectors}
            response = await client.put(
                "http://localhost:6333/collections/test_collection/points",
                json=upsert_data
            )
            assert response.status_code == 200
            
            # 벡터 조회
            response = await client.get(
                "http://localhost:6333/collections/test_collection/points/5"
            )
            assert response.status_code == 200
            point = response.json()["result"]
            assert point["payload"]["text"] == "테스트 문서 5"
            
            # 벡터 업데이트
            update_data = {
                "points": [{
                    "id": 5,
                    "payload": {"text": "업데이트된 문서 5", "updated": True}
                }]
            }
            response = await client.put(
                "http://localhost:6333/collections/test_collection/points",
                json=update_data
            )
            assert response.status_code == 200
            
            # 업데이트 확인
            response = await client.get(
                "http://localhost:6333/collections/test_collection/points/5"
            )
            point = response.json()["result"]
            assert point["payload"]["text"] == "업데이트된 문서 5"
            assert point["payload"]["updated"] is True
            
            # 벡터 삭제
            delete_data = {"points": [0, 1, 2]}
            response = await client.post(
                "http://localhost:6333/collections/test_collection/points/delete",
                json=delete_data
            )
            assert response.status_code == 200
            
            print("✅ 벡터 CRUD 연산 테스트 완료")
    
    async def test_vector_search_performance(self):
        """벡터 검색 성능 테스트"""
        async with httpx.AsyncClient() as client:
            # 대량 벡터 데이터 추가
            batch_size = 100
            test_vectors = []
            for i in range(batch_size):
                vector = {
                    "id": f"perf_{i}",
                    "vector": [random.random() for _ in range(384)],
                    "payload": {
                        "text": f"성능 테스트 문서 {i}",
                        "batch": "performance"
                    }
                }
                test_vectors.append(vector)
            
            upsert_data = {"points": test_vectors}
            response = await client.put(
                "http://localhost:6333/collections/test_collection/points",
                json=upsert_data
            )
            assert response.status_code == 200
            
            # 검색 성능 측정
            search_vector = [random.random() for _ in range(384)]
            search_times = []
            
            for _ in range(5):  # 5회 측정
                start_time = asyncio.get_event_loop().time()
                
                search_data = {
                    "vector": search_vector,
                    "limit": 10,
                    "with_payload": True
                }
                
                response = await client.post(
                    "http://localhost:6333/collections/test_collection/points/search",
                    json=search_data
                )
                
                end_time = asyncio.get_event_loop().time()
                search_time = end_time - start_time
                search_times.append(search_time)
                
                assert response.status_code == 200
                results = response.json()["result"]
                assert len(results) <= 10
            
            avg_search_time = sum(search_times) / len(search_times)
            assert avg_search_time < 1.0  # 평균 검색 시간 1초 이내
            
            print(f"✅ 벡터 검색 성능: 평균 {avg_search_time:.3f}초")
            print(f"개별 측정: {[f'{t:.3f}s' for t in search_times]}")
    
    async def test_hybrid_search(self):
        """하이브리드 검색 테스트 (벡터 + 필터)"""
        async with httpx.AsyncClient() as client:
            # 카테고리별 벡터 추가
            categories = ["python", "javascript", "java"]
            for category in categories:
                test_vectors = []
                for i in range(20):
                    vector = {
                        "id": f"{category}_{i}",
                        "vector": [random.random() for _ in range(384)],
                        "payload": {
                            "text": f"{category} 코드 예제 {i}",
                            "language": category,
                            "complexity": random.choice(["low", "medium", "high"])
                        }
                    }
                    test_vectors.append(vector)
                
                upsert_data = {"points": test_vectors}
                response = await client.put(
                    "http://localhost:6333/collections/test_collection/points",
                    json=upsert_data
                )
                assert response.status_code == 200
            
            # 하이브리드 검색 (python + medium complexity)
            search_vector = [random.random() for _ in range(384)]
            search_data = {
                "vector": search_vector,
                "limit": 10,
                "filter": {
                    "must": [
                        {"key": "language", "match": {"value": "python"}},
                        {"key": "complexity", "match": {"value": "medium"}}
                    ]
                },
                "with_payload": True
            }
            
            response = await client.post(
                "http://localhost:6333/collections/test_collection/points/search",
                json=search_data
            )
            
            assert response.status_code == 200
            results = response.json()["result"]
            
            # 결과 검증
            for result in results:
                payload = result["payload"]
                assert payload["language"] == "python"
                assert payload["complexity"] == "medium"
            
            print(f"✅ 하이브리드 검색 테스트 완료: {len(results)}개 결과")
    
    async def test_concurrent_operations(self):
        """동시 연산 처리 테스트"""
        async with httpx.AsyncClient() as client:
            # 동시 검색 요청
            search_vector = [random.random() for _ in range(384)]
            search_data = {
                "vector": search_vector,
                "limit": 5
            }
            
            tasks = []
            for i in range(20):  # 20개 동시 검색
                task = client.post(
                    "http://localhost:6333/collections/test_collection/points/search",
                    json=search_data
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = 0
            for response in responses:
                if not isinstance(response, Exception) and response.status_code == 200:
                    success_count += 1
            
            assert success_count >= 18, f"동시 검색 실패: {success_count}/20"
            print(f"✅ 동시 검색 성공: {success_count}/20")
    
    async def teardown(self):
        """테스트 정리"""
        async with httpx.AsyncClient() as client:
            # 테스트 컬렉션 삭제
            await client.delete("http://localhost:6333/collections/test_collection")
```

**실행 방법**:
```bash
# Docker Compose 환경 시작
docker-compose up -d vector-db

# Vector DB 준비 대기
sleep 30

# Integration 테스트 실행
pytest tests/integration/test_vector_db_integration.py -v

# 성공 기준
# - 컬렉션 관리 정상 동작
# - 벡터 CRUD 연산 성공
# - 검색 성능 < 1초
# - 하이브리드 검색 정상 동작
# - 동시 연산 성공률 > 90%
```

## 🔄 다음 단계
Task 04: RAG Server 구현 