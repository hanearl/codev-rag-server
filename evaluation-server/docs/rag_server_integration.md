# 🚀 codev-rag-server 연동 가이드

## 📋 개요

`evaluation-server`에 `codev-rag-server`가 성공적으로 연동되었습니다. 이제 하이브리드 검색(벡터 + 키워드)과 RRF(Reciprocal Rank Fusion) 기능을 활용한 고품질 RAG 시스템 평가가 가능합니다.

## 🎯 주요 기능

### rag-server의 특징
- **하이브리드 검색**: 벡터 검색 + 키워드 검색 결합
- **RRF 융합**: Reciprocal Rank Fusion으로 검색 결과 최적화
- **코드 생성**: 검색된 컨텍스트 기반 코드 생성
- **다중 언어 지원**: Python, Java, JavaScript, TypeScript, Go
- **실시간 인덱싱**: 코드 파일 자동 파싱 및 인덱싱

### evaluation-server 연동 기능
- **자동 어댑터**: rag-server API 형식에 맞는 자동 변환
- **메타데이터 보존**: 함수명, 파일 경로, 언어 정보 등 상세 정보 유지
- **성능 모니터링**: 검색 시간, 점수 분석 등 상세 메트릭 제공

## 🔧 사용법

### 1. 지원하는 RAG 시스템 타입 확인

```bash
curl -X GET "http://localhost:8003/api/v1/evaluation/rag-systems/types"
```

**응답:**
```json
{
  "supported_types": [
    "RAGSystemType.RAG_SERVER",
    // ... 기타 타입들
  ],
  "descriptions": {
    "rag_server": "codev-rag-server (하이브리드 검색 + 코드 생성)"
  }
}
```

### 2. rag-server 설정 템플릿 조회

```bash
curl -X GET "http://localhost:8003/api/v1/evaluation/rag-systems/templates/rag_server"
```

**응답:**
```json
{
  "name": "codev-rag-server",
  "system_type": "rag_server",
  "base_url": "http://rag-server:8000",
  "api_key": "optional-api-key",
  "timeout": 30.0,
  "features": {
    "hybrid_search": true,
    "rrf_fusion": true,
    "code_generation": true,
    "multi_language": true,
    "vector_search": true,
    "keyword_search": true
  },
  "search_params": {
    "vector_weight": 0.7,
    "keyword_weight": 0.3,
    "use_rrf": true,
    "rrf_k": 60,
    "collection_name": "code_chunks"
  },
  "required_fields": ["base_url"],
  "optional_fields": ["api_key", "timeout"]
}
```

### 3. 평가 실행

#### 기본 설정으로 평가

```bash
curl -X POST "http://localhost:8003/api/v1/evaluation/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name": "sample-dataset",
    "system_config": {
      "name": "codev-rag-server",
      "system_type": "rag_server",
      "base_url": "http://localhost:8000"
    },
    "k_values": [1, 3, 5, 10],
    "metrics": ["recall", "precision", "hit", "mrr", "ndcg"],
    "save_results": true
  }'
```

#### 고급 설정으로 평가

```bash
curl -X POST "http://localhost:8003/api/v1/evaluation/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_name": "sample-dataset",
    "system_config": {
      "name": "codev-rag-server-optimized",
      "system_type": "rag_server",
      "base_url": "http://localhost:8000",
      "api_key": "your-api-key",
      "timeout": 45.0,
      "custom_headers": {
        "X-Custom-Header": "evaluation-test"
      }
    },
    "k_values": [1, 3, 5, 10, 20],
    "metrics": ["recall", "precision", "hit", "mrr", "ndcg"],
    "options": {
      "convert_filepath_to_classpath": true,
      "ignore_method_names": false,
      "case_sensitive": true,
      "java_source_root": "src/main/java",
      "java_test_root": "src/test/java"
    },
    "save_results": true
  }'
```

## 📊 응답 형식

### 평가 결과 예시

```json
{
  "evaluation_id": "eval_20241213_123456",
  "dataset_name": "sample-dataset",
  "system_name": "codev-rag-server",
  "total_queries": 10,
  "evaluation_time_ms": 15420,
  "results": {
    "recall@1": 0.85,
    "recall@3": 0.92,
    "recall@5": 0.95,
    "precision@1": 0.85,
    "precision@3": 0.78,
    "precision@5": 0.72,
    "hit@1": 0.85,
    "hit@3": 0.92,
    "hit@5": 0.95,
    "mrr": 0.88,
    "ndcg@1": 0.85,
    "ndcg@3": 0.87,
    "ndcg@5": 0.89
  },
  "detailed_results": [
    {
      "query_id": "q1",
      "query": "BookController 클래스",
      "ground_truth": ["com.skax.library.controller.BookController"],
      "predictions": [
        {
          "content": "Function: getBook\npublic Book getBook(Long id) { ... }",
          "score": 0.95,
          "filepath": "src/main/java/com/skax/library/controller/BookController.java",
          "metadata": {
            "function_name": "getBook",
            "language": "java",
            "vector_score": 0.92,
            "keyword_score": 0.88,
            "search_method": "rrf",
            "search_time_ms": 45
          }
        }
      ],
      "metrics": {
        "recall@1": 1.0,
        "precision@1": 1.0,
        "hit@1": 1.0
      }
    }
  ]
}
```

## 🔍 rag-server 어댑터 내부 동작

### 1. 검색 프로세스

```python
# rag-server API 호출
search_request = {
    "query": "BookController 클래스",
    "limit": 10,
    "vector_weight": 0.7,      # 벡터 검색 가중치
    "keyword_weight": 0.3,     # 키워드 검색 가중치
    "use_rrf": True,           # RRF 융합 사용
    "rrf_k": 60,               # RRF 상수
    "collection_name": "code_chunks"
}
```

### 2. 응답 변환

```python
# rag-server 응답을 RetrievalResult로 변환
for item in rag_response["results"]:
    result = RetrievalResult(
        content=f"Function: {item['function_name']}\n{item['code_content']}",
        score=item["combined_score"],
        filepath=item["file_path"],
        metadata={
            "function_name": item["function_name"],
            "language": item["language"],
            "vector_score": item["vector_score"],
            "keyword_score": item["keyword_score"],
            "search_method": "rrf"
        }
    )
```

### 3. 임베딩 처리

```python
# embedding-server 직접 호출 (rag-server에는 별도 임베딩 엔드포인트 없음)
embedding_url = base_url.replace("rag-server:8000", "embedding-server:8001")
response = await client.post(f"{embedding_url}/api/v1/embed", json={"text": query})
```

## 🚨 주의사항

### 1. 네트워크 설정
- `rag-server`와 `embedding-server`가 같은 Docker 네트워크에 있어야 함
- 포트 설정: rag-server(8000), embedding-server(8001), evaluation-server(8003)

### 2. 데이터 준비
- rag-server에 코드 데이터가 인덱싱되어 있어야 함
- evaluation 데이터셋에 ground_truth가 포함되어 있어야 함

### 3. 성능 고려사항
- 대용량 데이터셋 평가 시 timeout 값 조정 필요
- RRF 사용 시 검색 시간이 약간 증가할 수 있음

## 🔧 트러블슈팅

### 1. 연결 오류
```bash
# rag-server 상태 확인
curl -X GET "http://localhost:8000/health"

# evaluation-server에서 rag-server 접근 확인
docker-compose exec evaluation-server curl -X GET "http://rag-server:8000/health"
```

### 2. 검색 결과 없음
```bash
# rag-server 검색 직접 테스트
curl -X POST "http://localhost:8000/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}'
```

### 3. 임베딩 오류
```bash
# embedding-server 상태 확인
curl -X GET "http://localhost:8001/health"
```

## 📈 성능 최적화 팁

### 1. 검색 파라미터 튜닝
- `vector_weight`: 0.5-0.8 (의미적 유사성 중시)
- `keyword_weight`: 0.2-0.5 (정확한 키워드 매칭 중시)
- `rrf_k`: 30-100 (작을수록 상위 결과에 더 큰 가중치)

### 2. 평가 설정 최적화
- `k_values`: [1, 3, 5, 10] (일반적인 설정)
- `metrics`: ["recall", "precision", "hit", "mrr"] (핵심 메트릭)
- `timeout`: 30-60초 (데이터셋 크기에 따라 조정)

이제 `codev-rag-server`를 활용한 고품질 RAG 시스템 평가가 가능합니다! 🎉 