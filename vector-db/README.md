# Vector DB (Qdrant) 설정 및 사용 가이드

## 개요
Qdrant를 사용하여 코드 임베딩을 저장하고 검색할 수 있는 벡터 데이터베이스 구성

## 시작하기

### 1. Qdrant 서버 시작
```bash
cd vector-db
docker-compose up -d
```

### 2. 컬렉션 초기화
```bash
cd vector-db
python scripts/init_collections.py
```

### 3. 헬스체크
```bash
curl http://localhost:6333/health
```

## 컬렉션 구조

### code_embeddings 컬렉션
- **벡터 차원**: 384 (sentence-transformers/all-MiniLM-L6-v2)
- **거리 메트릭**: Cosine
- **페이로드 스키마**:
  - `file_path`: 파일 경로
  - `function_name`: 함수/클래스명
  - `code_type`: 코드 타입 (function, class, method)
  - `language`: 프로그래밍 언어
  - `code_content`: 실제 코드 내용
  - `line_start`: 시작 라인 번호
  - `line_end`: 종료 라인 번호
  - `created_at`: 생성 시간
  - `keywords`: 키워드 리스트

## 스크립트 사용법

### 컬렉션 관리
```bash
# 컬렉션 생성
python scripts/init_collections.py

# 컬렉션 정보 조회
python scripts/init_collections.py --info

# 컬렉션 삭제
python scripts/init_collections.py --delete
```

### 백업
```bash
# 백업 생성
python scripts/backup.py

# 스냅샷 목록 조회
python scripts/backup.py --list

# 특정 디렉토리에 백업
python scripts/backup.py --output-dir /path/to/backup
```

### 복원
```bash
# 백업에서 복원
python scripts/restore.py --snapshot-path /path/to/snapshot.tar
```

## API 사용 예제

### Python 클라이언트
```python
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

client = QdrantClient(host="localhost", port=6333)

# 벡터 삽입
client.upsert(
    collection_name="code_embeddings",
    points=[
        PointStruct(
            id=1,
            vector=[0.1] * 384,
            payload={
                "file_path": "src/main.py",
                "function_name": "main",
                "code_type": "function",
                "language": "python",
                "code_content": "def main():\n    print('Hello')",
                "line_start": 1,
                "line_end": 2,
                "created_at": "2023-01-01T00:00:00Z",
                "keywords": ["main", "function"]
            }
        )
    ]
)

# 벡터 검색
results = client.search(
    collection_name="code_embeddings",
    query_vector=[0.1] * 384,
    limit=5
)
```

### 필터링된 검색
```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Python 파일만 검색
results = client.search(
    collection_name="code_embeddings",
    query_vector=[0.1] * 384,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="language",
                match=MatchValue(value="python")
            )
        ]
    ),
    limit=5
)
```

## 테스트 실행
```bash
cd vector-db
pytest tests/ -v
```

## 모니터링

### Qdrant 대시보드
- URL: http://localhost:6333/dashboard
- 컬렉션 상태, 메트릭, 검색 등을 웹 UI에서 확인 가능

### 로그 확인
```bash
docker-compose logs -f vector-db
```

## 성능 튜닝

### 인덱스 최적화
- 자주 사용되는 필터 필드에 대해 인덱스 생성
- 현재 설정된 인덱스: file_path, language, code_type, function_name

### 메모리 설정
- `config/qdrant.yaml`에서 메모리 관련 설정 조정 가능

## 문제 해결

### 연결 오류
1. Docker 컨테이너 상태 확인: `docker-compose ps`
2. 포트 충돌 확인: `lsof -i :6333`
3. 로그 확인: `docker-compose logs vector-db`

### 성능 이슈
1. 인덱스 상태 확인
2. 메모리 사용량 모니터링
3. 벡터 차원 및 데이터 크기 검토 