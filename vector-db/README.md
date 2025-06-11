# Vector Database 설정

## 개요
Qdrant를 사용한 벡터 데이터베이스 설정 및 관리

## 구조
```
vector-db/
├── config/
│   ├── qdrant.yaml              ← Qdrant 서버 설정
│   └── collection_config.json   ← 컬렉션 설정
└── scripts/
    └── init_collections.py      ← 컬렉션 초기화 스크립트
```

## 사용법

### 1. 서비스 시작
```bash
# 프로젝트 루트에서
docker-compose up -d vector-db
```

### 2. 컬렉션 초기화
```bash
cd vector-db
python scripts/init_collections.py
```

### 3. 헬스체크
```bash
curl http://localhost:6333/healthz
```

## 컬렉션 정보
- **이름**: `code_embeddings`
- **벡터 차원**: 384 (sentence-transformers/all-MiniLM-L6-v2)
- **거리 메트릭**: Cosine
- **포트**: 6333 (HTTP), 6334 (gRPC) 