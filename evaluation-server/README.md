# RAG Evaluation Server

RAG(Retrieval-Augmented Generation) 시스템의 성능을 평가하기 위한 마이크로서비스입니다. 

## 🎯 주요 기능

### ✨ 핵심 평가 기능
- **RAG 시스템 성능 평가**: Recall@k, Precision@k, Hit@k, NDCG@k, MRR 메트릭 지원
- **다중 데이터셋 지원**: 여러 데이터셋을 사용한 평가 
- **배치 평가**: 여러 질문에 대한 일괄 평가
- **결과 저장 및 관리**: 평가 결과 영구 저장

### 🔧 Java 개발 특화 기능
- **Java 클래스패스 변환**: 파일 경로를 Java 클래스패스로 자동 변환
- **메서드명 제외 옵션**: 함수 이름을 제외하고 클래스까지만 비교 (기본값: true)
- **대소문자 구분 옵션**: 클래스패스 비교 시 대소문자 구분 설정
- **다중 정답 지원**: 하나의 질문에 여러 개의 정답 클래스패스 지원

### 📊 지원하는 데이터셋 형식
- **Inline 형식**: 질문과 정답이 같은 파일에 포함 (JSON/JSONL)
- **난이도 레벨**: 하/중/상 난이도 분류
- **유연한 파일 형식**: `queries.jsonl`, `questions.json` 등 다양한 파일명 지원

## 📁 프로젝트 구조

```
evaluation-server/
├── app/                           # 애플리케이션 코드
│   ├── features/
│   │   └── evaluation/           # 평가 기능
│   │       ├── router.py         # API 엔드포인트
│   │       ├── service.py        # 비즈니스 로직
│   │       ├── schema.py         # 데이터 스키마
│   │       └── dataset_loader.py # 데이터셋 로더
│   ├── core/
│   │   ├── config.py            # 설정 관리
│   │   └── classpath_utils.py   # Java 클래스패스 유틸리티
│   └── main.py                  # FastAPI 애플리케이션
├── datasets/                    # 평가용 데이터셋
│   └── sample-dataset/
│       ├── metadata.json        # 데이터셋 메타데이터
│       └── queries.jsonl        # 질문 및 정답 데이터
├── tests/                       # 테스트 코드
└── docs/                        # 문서
```

## 📝 데이터셋 형식

### 새로운 Inline 형식 (권장)

#### 1. 메타데이터 파일 (`metadata.json`)
```json
{
  "name": "Java Development RAG Evaluation Dataset",
  "description": "Java 개발 질문에 대한 RAG 시스템 평가용 데이터셋",
  "version": "2.0.0",
  "language": "ko",
  "domain": "java_development",
  "query_count": 100,
  "ground_truth_format": "inline",
  "data_format": {
    "fields": ["difficulty", "question", "answer"],
    "answer_type": "java_classpath",
    "supports_multiple_answers": true
  },
  "evaluation_options": {
    "convert_filepath_to_classpath": true,
    "ignore_method_names": true,
    "case_sensitive": false,
    "java_source_root": "src/main/java",
    "java_test_root": "src/test/java"
  },
  "difficulty_levels": ["하", "중", "상"]
}
```

#### 2. 질문 데이터 파일 (`queries.jsonl`)
```jsonl
{"difficulty": "하", "question": "도서 관리를 담당하는 컨트롤러 클래스는 무엇인가요?", "answer": "com.skax.library.controller.BookController"}
{"difficulty": "중", "question": "도서 대출 처리 시 호출되는 클래스들은 무엇인가요?", "answer": ["com.skax.library.controller.LoanController", "com.skax.library.service.impl.LoanServiceImpl.checkoutBook", "com.skax.library.repository.LoanRepository"]}
{"difficulty": "상", "question": "도서 추천 시스템을 구현하는 클래스들은 무엇인가요?", "answer": ["com.skax.library.service.impl.BookServiceImpl.getRecommendedBooks", "com.skax.library.config.RecommendationConfig"]}
```

또는 JSON 배열 형식 (`questions.json`):
```json
[
  {
    "difficulty": "하",
    "question": "도서 관리를 담당하는 컨트롤러 클래스는 무엇인가요?",
    "answer": "com.skax.library.controller.BookController"
  },
  {
    "difficulty": "중", 
    "question": "도서 대출 처리 시 호출되는 클래스들은 무엇인가요?",
    "answer": [
      "com.skax.library.controller.LoanController",
      "com.skax.library.service.impl.LoanServiceImpl.checkoutBook",
      "com.skax.library.repository.LoanRepository"
    ]
  }
]
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp env.example .env
# .env 파일을 편집하여 필요한 설정 입력
```

### 2. 서버 실행

```bash
# 개발 모드로 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8003
```

### 3. API 문서 확인

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8003/docs
- ReDoc: http://localhost:8003/redoc

## 📡 API 사용법

### 1. 데이터셋 목록 조회

```bash
curl -X GET "http://localhost:8003/api/v1/evaluation/datasets"
```

### 2. RAG 시스템 평가 실행

```bash
curl -X POST "http://localhost:8003/api/v1/evaluation/evaluate" \
     -H "Content-Type: application/json" \
     -d '{
       "rag_system_id": "my-rag-system",
       "dataset_name": "sample-dataset",
       "k_values": [1, 3, 5, 10],
       "evaluation_options": {
         "convert_filepath_to_classpath": true,
         "ignore_method_names": true,
         "case_sensitive": false,
         "java_source_root": "src/main/java"
       }
     }'
```

### 3. 클래스패스 변환 테스트

```bash
curl -X POST "http://localhost:8003/api/v1/evaluation/test-classpath-conversion" \
     -H "Content-Type: application/json" \
     -d '{
       "filepaths": [
         "src/main/java/com/skax/library/controller/BookController.java",
         "src/main/java/com/skax/library/service/impl/BookServiceImpl.java"
       ],
       "expected_classpaths": [
         "com.skax.library.controller.BookController",
         "com.skax.library.service.impl.BookServiceImpl"
       ],
       "options": {
         "convert_filepath_to_classpath": true,
         "ignore_method_names": true,
         "case_sensitive": false
       }
     }'
```

## ⚙️ 평가 옵션 설명

### Java 클래스패스 변환 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `convert_filepath_to_classpath` | `true` | 파일 경로를 Java 클래스패스로 자동 변환 |
| `ignore_method_names` | `true` | 메서드명을 제외하고 클래스까지만 비교 |
| `case_sensitive` | `false` | 클래스패스 비교 시 대소문자 구분 |
| `java_source_root` | `"src/main/java"` | Java 소스 루트 디렉토리 |
| `java_test_root` | `"src/test/java"` | Java 테스트 루트 디렉토리 |

### 클래스패스 변환 예시

```
파일 경로: "src/main/java/com/skax/library/controller/BookController.java"
변환 결과: "com.skax.library.controller.BookController"

정답(메서드 포함): "com.skax.library.service.impl.BookServiceImpl.createBook"
ignore_method_names=true: "com.skax.library.service.impl.BookServiceImpl"로 비교
ignore_method_names=false: "com.skax.library.service.impl.BookServiceImpl.createBook"로 비교
```

## 📊 평가 메트릭

### 지원하는 메트릭
- **Recall@k**: 상위 k개 결과에서 찾은 관련 문서 수 / 전체 관련 문서 수
- **Precision@k**: 상위 k개 결과에서 찾은 관련 문서 수 / k
- **Hit@k**: 상위 k개 결과에 관련 문서가 하나라도 있으면 1, 없으면 0
- **NDCG@k**: Normalized Discounted Cumulative Gain at k
- **MRR**: Mean Reciprocal Rank (첫 번째 관련 문서의 평균 역순위)

### 평가 결과 예시

```json
{
  "id": "eval-12345",
  "rag_system_id": "my-rag-system",
  "dataset_name": "sample-dataset",
  "metrics": {
    "recall_at_k": {
      "1": 0.3,
      "3": 0.6,
      "5": 0.8,
      "10": 0.9
    },
    "precision_at_k": {
      "1": 0.3,
      "3": 0.2,
      "5": 0.16,
      "10": 0.09
    },
    "hit_at_k": {
      "1": 0.3,
      "3": 0.6,
      "5": 0.8,
      "10": 0.9
    },
    "ndcg_at_k": {
      "1": 0.3,
      "3": 0.45,
      "5": 0.62,
      "10": 0.71
    },
    "mrr": 0.52,
    "total_questions": 100,
    "processed_questions": 100
  },
  "evaluation_options": {
    "convert_filepath_to_classpath": true,
    "ignore_method_names": true,
    "case_sensitive": false
  },
  "created_at": "2024-01-15T10:30:00Z",
  "execution_time_seconds": 45.2
}
```

## 🧪 테스트 실행

```bash
# 모든 테스트 실행
pytest tests/ -v

# 특정 테스트 파일 실행
pytest tests/test_classpath_utils.py -v

# 커버리지 포함 테스트
pytest tests/ --cov=app --cov-report=html
```

## 🐳 Docker 실행

```bash
# Docker 이미지 빌드
docker build -t evaluation-server .

# 컨테이너 실행
docker run -p 8003:8000 \
  -v $(pwd)/datasets:/app/datasets \
  evaluation-server
```

## 🔧 설정

### 환경 변수

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| `HOST` | `0.0.0.0` | 서버 호스트 |
| `PORT` | `8000` | 서버 포트 |
| `RAG_SERVER_URL` | `http://rag-server:8000` | RAG 서버 URL |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |

## 🤝 기여하기

1. 이 리포지토리를 포크합니다
2. 피처 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 📜 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 지원

문의사항이나 버그 리포트는 GitHub Issues를 사용해 주세요.

---

**RAG Evaluation Server**는 Java 개발 환경에 특화된 RAG 시스템 평가 도구입니다. 파일 경로를 클래스패스로 자동 변환하고, 메서드명 제외 옵션 등을 통해 보다 정확한 평가를 제공합니다. 

## 🔧 지원하는 RAG 시스템

### 1. RAG 서버 어댑터 (신규)

**rag-server**의 새로운 API 구조에 맞춰 3가지 검색 타입을 지원합니다:

#### 벡터 검색 (Vector Search)
- **시스템 타입**: `RAG_SERVER_VECTOR`
- **특징**: 의미 기반 유사도 검색
- **엔드포인트**: `/api/v1/search/vector`
- **사용 사례**: 자연어 의미 이해가 중요한 검색

#### BM25 검색 (Keyword Search)  
- **시스템 타입**: `RAG_SERVER_BM25`
- **특징**: 키워드 기반 통계적 검색
- **엔드포인트**: `/api/v1/search/bm25`
- **사용 사례**: 정확한 키워드 매칭이 중요한 검색

#### 하이브리드 검색 (Hybrid Search)
- **시스템 타입**: `RAG_SERVER_HYBRID`
- **특징**: 벡터 + BM25 검색 결합
- **엔드포인트**: `/api/v1/search/hybrid`
- **사용 사례**: 의미와 키워드를 모두 고려한 정확한 검색

### 2. 기타 지원 시스템

- OpenAI RAG
- LangChain RAG  
- LlamaIndex RAG
- 커스텀 HTTP RAG
- Codev V1 RAG
- Mock RAG (테스트용)

## 📖 사용 방법

### 빠른 시작

```python
from app.features.systems.factory import (
    create_rag_server_vector,
    create_rag_server_bm25,
    create_rag_server_hybrid,
    create_all_rag_server_systems
)

# 1. 벡터 검색 시스템
vector_system = create_rag_server_vector(
    base_url="http://rag-server:8000",
    collection_name="code_chunks"
)

# 2. BM25 검색 시스템  
bm25_system = create_rag_server_bm25(
    base_url="http://rag-server:8000",
    index_name="code_index"
)

# 3. 하이브리드 검색 시스템
hybrid_system = create_rag_server_hybrid(
    base_url="http://rag-server:8000",
    collection_name="code_chunks",
    index_name="code_index",
    vector_weight=0.7,
    bm25_weight=0.3,
    use_rrf=True
)

# 4. 모든 시스템 한번에 생성
all_systems = create_all_rag_server_systems(
    base_url="http://rag-server:8000"
)

# 검색 수행
async def search_example():
    query = "파이썬 함수 정의"
    
    # 벡터 검색
    vector_results = await vector_system.retrieve(query, top_k=10)
    
    # BM25 검색
    bm25_results = await bm25_system.retrieve(query, top_k=10)
    
    # 하이브리드 검색
    hybrid_results = await hybrid_system.retrieve(query, top_k=10)
    
    # 시스템 정리
    await vector_system.close()
    await bm25_system.close()
    await hybrid_system.close()
```

### 설정 템플릿 사용

```python
from app.features.systems.factory import RAGSystemTemplates, create_rag_system

# 벡터 검색 설정
vector_config = RAGSystemTemplates.rag_server_vector(
    base_url="http://localhost:8000",
    collection_name="my_collection"
)

# BM25 검색 설정
bm25_config = RAGSystemTemplates.rag_server_bm25(
    base_url="http://localhost:8000", 
    index_name="my_index"
)

# 하이브리드 검색 설정 (고급)
hybrid_config = RAGSystemTemplates.rag_server_hybrid(
    base_url="http://localhost:8000",
    vector_weight=0.8,
    bm25_weight=0.2,
    use_rrf=False  # RRF 대신 가중합 사용
)

# 시스템 생성
vector_system = create_rag_system(vector_config)
bm25_system = create_rag_system(bm25_config)
hybrid_system = create_rag_system(hybrid_config)
```

### 평가 실행

```python
from app.features.evaluations.service import evaluation_service

# 모든 RAG 시스템 등록
systems = {
    "rag-server-vector": create_rag_server_vector(),
    "rag-server-bm25": create_rag_server_bm25(),
    "rag-server-hybrid": create_rag_server_hybrid(),
}

# 평가 실행
results = []
for name, system in systems.items():
    result = await evaluation_service.run_evaluation(
        system=system,
        dataset_name="code_search_dataset",
        metrics=["precision", "recall", "f1", "mrr"]
    )
    results.append(result)

# 결과 비교
comparison = await evaluation_service.compare_systems(results)
```

## ⚙️ 하이브리드 검색 설정

하이브리드 검색은 다양한 융합 방법과 가중치를 지원합니다:

### 융합 방법 (Fusion Methods)

1. **RRF (Reciprocal Rank Fusion)** - 권장
   ```python
   hybrid_config = RAGSystemTemplates.rag_server_hybrid(
       use_rrf=True,
       rrf_k=60  # RRF 파라미터
   )
   ```

2. **가중합 (Weighted Sum)**
   ```python
   hybrid_config = RAGSystemTemplates.rag_server_hybrid(
       use_rrf=False,
       vector_weight=0.7,
       bm25_weight=0.3
   )
   ```

### 권장 가중치 설정

| 사용 사례 | 벡터 가중치 | BM25 가중치 | 설명 |
|----------|------------|------------|------|
| 의미 중심 검색 | 0.8 | 0.2 | 자연어 질의에 적합 |
| 균형 잡힌 검색 | 0.7 | 0.3 | 일반적인 코드 검색 |
| 키워드 중심 검색 | 0.4 | 0.6 | 정확한 함수/클래스명 검색 |

## 🔍 검색 결과 분석

각 어댑터는 다음과 같은 메타데이터를 제공합니다:

### 벡터 검색 결과
```python
{
    "search_type": "vector",
    "search_time_ms": 120,
    "document_id": "doc_123",
    "similarity_score": 0.85
}
```

### BM25 검색 결과  
```python
{
    "search_type": "bm25", 
    "search_time_ms": 80,
    "document_id": "doc_456",
    "bm25_score": 12.34
}
```

### 하이브리드 검색 결과
```python
{
    "search_type": "hybrid",
    "fusion_method": "rrf",
    "weights_used": {"vector": 0.7, "bm25": 0.3},
    "vector_results_count": 15,
    "bm25_results_count": 12,
    "search_time_ms": 150
}
```

## 🧪 예제 실행

전체 사용 예제는 다음 파일에서 확인할 수 있습니다:

```bash
python docs/rag_server_adapters_usage.py
```

이 예제는 다음을 포함합니다:
- 각 검색 타입별 사용법
- 시스템 비교 방법
- 설정 템플릿 활용법
- 시스템 정보 조회 방법