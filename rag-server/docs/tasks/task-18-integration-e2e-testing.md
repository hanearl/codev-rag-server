# 📋 Task 18: 통합 테스트 및 E2E 테스트 구현

---

## 🎯 목표 및 범위

하이브리드 RAG 시스템의 **전체 워크플로우 검증**을 위한 통합 테스트 및 E2E 테스트를 구현합니다.  
구현된 모든 컴포넌트가 올바르게 연동되고 기대한 성능을 발휘하는지 검증합니다.

### 📊 검증 대상 주요 Flow

1. **코드 인덱싱 Flow**: 파싱 → 문서 생성 → 인덱스 저장
2. **하이브리드 검색 Flow**: BM25 + Vector 검색 → 결과 병합
3. **LLM 체인 Flow**: 검색 → 프롬프트 구성 → LLM 응답
4. **통합 API Flow**: 클라이언트 요청 → 최종 응답
5. **성능 및 정확도 검증**: 응답 시간, 검색 품질, 메모리 사용량

---

## 📁 구현할 테스트 구조

```
tests/
├── integration/                      # 통합 테스트
│   ├── test_indexing_flow.py        # 인덱싱 플로우 테스트
│   ├── test_hybrid_search_flow.py   # 하이브리드 검색 플로우 테스트
│   ├── test_llm_chain_flow.py       # LLM 체인 플로우 테스트
│   ├── test_full_pipeline.py        # 전체 파이프라인 테스트
│   └── test_performance.py          # 성능 벤치마크 테스트
├── e2e/                             # E2E 테스트
│   ├── test_api_endpoints.py        # API 엔드포인트 테스트
│   ├── test_user_scenarios.py       # 사용자 시나리오 테스트
│   ├── test_error_handling.py       # 에러 처리 테스트
│   └── test_concurrent_requests.py  # 동시 요청 처리 테스트
├── fixtures/                        # 테스트 데이터
│   ├── sample_java_files/           # 테스트용 Java 파일들
│   ├── expected_responses/          # 기대 응답 데이터
│   └── performance_baseline.json   # 성능 기준값
└── conftest.py                      # 공통 fixture
```

---

## 🔧 세부 구현 사항

### 1. 통합 테스트 구현

#### 1.1 인덱싱 Flow 테스트
```python
# tests/integration/test_indexing_flow.py
import pytest
from app.retriever.ast_parser import JavaASTParser
from app.retriever.document_builder import DocumentBuilder
from app.index.vector_index import CodeVectorIndex
from app.index.bm25_index import CodeBM25Index

class TestIndexingFlow:
    """코드 파싱부터 인덱스 저장까지 전체 플로우 테스트"""
    
    @pytest.fixture
    def sample_java_file(self):
        return "tests/fixtures/sample_java_files/Calculator.java"
    
    async def test_full_indexing_pipeline(self, sample_java_file):
        """Java 파일 → AST 파싱 → Document 생성 → 인덱스 저장"""
        # Given
        parser = JavaASTParser()
        builder = DocumentBuilder()
        vector_index = CodeVectorIndex()
        bm25_index = CodeBM25Index()
        
        # When - 파싱 및 Document 생성
        parsed_methods = parser.parse_java_file(sample_java_file)
        documents = builder.build_from_parsed_methods(parsed_methods)
        
        # Then - Document 검증
        assert len(documents) > 0
        assert all(doc.metadata.get('file_path') for doc in documents)
        assert all(doc.metadata.get('method_name') for doc in documents)
        
        # When - 인덱스 저장
        vector_index.add_documents(documents)
        bm25_index.add_documents(documents)
        
        # Then - 인덱스 검증
        assert vector_index.get_document_count() == len(documents)
        assert bm25_index.get_document_count() == len(documents)
    
    async def test_batch_indexing_performance(self):
        """대용량 파일 배치 인덱싱 성능 테스트"""
        # Given
        java_files = [
            "tests/fixtures/sample_java_files/Calculator.java",
            "tests/fixtures/sample_java_files/StringUtils.java",
            "tests/fixtures/sample_java_files/DatabaseManager.java"
        ]
        
        # When
        start_time = time.time()
        total_documents = 0
        
        for file_path in java_files:
            documents = await self._index_single_file(file_path)
            total_documents += len(documents)
        
        end_time = time.time()
        
        # Then
        indexing_time = end_time - start_time
        assert indexing_time < 30.0  # 30초 이내 완료
        assert total_documents > 0
        
        # 성능 기준 검증
        docs_per_second = total_documents / indexing_time
        assert docs_per_second > 10  # 초당 10개 이상 처리
```

#### 1.2 하이브리드 검색 Flow 테스트
```python
# tests/integration/test_hybrid_search_flow.py
import pytest
from app.retriever.hybrid_retriever import CodeHybridRetriever
from app.index.vector_index import CodeVectorIndex
from app.index.bm25_index import CodeBM25Index

class TestHybridSearchFlow:
    """BM25 + Vector 하이브리드 검색 플로우 테스트"""
    
    @pytest.fixture
    async def indexed_system(self):
        """인덱싱된 테스트 시스템 준비"""
        vector_index = CodeVectorIndex()
        bm25_index = CodeBM25Index()
        
        # 테스트 문서들 인덱싱
        await self._index_test_documents(vector_index, bm25_index)
        
        retriever = CodeHybridRetriever(
            vector_retriever=vector_index.as_retriever(),
            bm25_retriever=bm25_index.as_retriever()
        )
        
        return retriever
    
    async def test_hybrid_search_accuracy(self, indexed_system):
        """하이브리드 검색 정확도 테스트"""
        # Given
        retriever = indexed_system
        test_queries = [
            "calculate sum of two numbers",
            "string validation method",
            "database connection setup"
        ]
        
        for query in test_queries:
            # When
            results = await retriever.retrieve(query)
            
            # Then
            assert len(results) > 0
            assert len(results) <= 10  # 최대 10개 결과
            
            # 관련성 점수 검증
            for result in results:
                assert result.score > 0.0
                assert result.node.metadata.get('method_name')
                assert result.node.text
            
            # 점수 순 정렬 검증
            scores = [result.score for result in results]
            assert scores == sorted(scores, reverse=True)
    
    async def test_search_performance_benchmark(self, indexed_system):
        """검색 성능 벤치마크 테스트"""
        # Given
        retriever = indexed_system
        queries = [
            "find method for sorting array",
            "validate email format",
            "parse JSON response"
        ]
        
        # When
        total_time = 0
        total_queries = 0
        
        for query in queries:
            start_time = time.time()
            results = await retriever.retrieve(query)
            end_time = time.time()
            
            query_time = end_time - start_time
            total_time += query_time
            total_queries += 1
            
            # 개별 쿼리 성능 검증
            assert query_time < 2.0  # 2초 이내 응답
            assert len(results) > 0
        
        # Then
        avg_response_time = total_time / total_queries
        assert avg_response_time < 1.0  # 평균 1초 이내
```

#### 1.3 LLM 체인 Flow 테스트
```python
# tests/integration/test_llm_chain_flow.py
import pytest
from app.llm.langchain_prompt import CodePromptBuilder
from app.llm.llm_chain import CodeLLMChain
from app.retriever.hybrid_retriever import CodeHybridRetriever

class TestLLMChainFlow:
    """검색 → 프롬프트 구성 → LLM 응답 플로우 테스트"""
    
    @pytest.fixture
    def llm_chain_setup(self):
        """LLM 체인 테스트 환경 준비"""
        prompt_builder = CodePromptBuilder()
        llm_chain = CodeLLMChain()
        
        return prompt_builder, llm_chain
    
    async def test_prompt_generation_flow(self, llm_chain_setup):
        """검색 결과 기반 프롬프트 생성 테스트"""
        # Given
        prompt_builder, _ = llm_chain_setup
        
        mock_search_results = [
            {
                "method_name": "calculateSum",
                "code": "public int calculateSum(int a, int b) { return a + b; }",
                "file_path": "Calculator.java"
            }
        ]
        
        query = "두 숫자를 더하는 방법"
        
        # When
        prompt = prompt_builder.build_explanation_prompt(
            query=query,
            search_results=mock_search_results
        )
        
        # Then
        assert query in prompt
        assert "calculateSum" in prompt
        assert "Calculator.java" in prompt
        assert "public int calculateSum" in prompt
    
    async def test_llm_response_quality(self, llm_chain_setup):
        """LLM 응답 품질 테스트"""
        # Given
        prompt_builder, llm_chain = llm_chain_setup
        
        # Mock 검색 결과
        search_results = [
            {
                "method_name": "validateEmail",
                "code": """
                public boolean validateEmail(String email) {
                    return email.contains("@") && email.contains(".");
                }
                """,
                "file_path": "ValidationUtils.java"
            }
        ]
        
        query = "이메일 유효성 검사하는 방법"
        
        # When
        prompt = prompt_builder.build_explanation_prompt(query, search_results)
        response = await llm_chain.generate_response(prompt)
        
        # Then
        assert response
        assert len(response) > 50  # 충분한 길이의 응답
        assert "email" in response.lower()
        assert "validation" in response.lower() or "유효성" in response
        
        # 응답 구조 검증
        assert not response.startswith("Error:")
        assert "validateEmail" in response
```

### 2. E2E 테스트 구현

#### 2.1 API 엔드포인트 테스트
```python
# tests/e2e/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestAPIEndpoints:
    """통합 API 엔드포인트 E2E 테스트"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    async def test_search_snippet_endpoint(self, client):
        """코드 스니펫 검색 API 테스트"""
        # Given
        query = "calculate sum of two numbers"
        
        # When
        response = client.get(f"/api/v1/search-snippet?query={query}")
        
        # Then
        assert response.status_code == 200
        
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0
        
        # 결과 구조 검증
        result = data["results"][0]
        assert "method_name" in result
        assert "code" in result
        assert "file_path" in result
        assert "score" in result
    
    async def test_explain_code_endpoint(self, client):
        """코드 설명 생성 API 테스트"""
        # Given
        request_data = {
            "query": "두 숫자를 더하는 방법을 설명해주세요",
            "max_results": 5
        }
        
        # When
        response = client.post("/api/v1/explain", json=request_data)
        
        # Then
        assert response.status_code == 200
        
        data = response.json()
        assert "explanation" in data
        assert "search_results" in data
        assert "metadata" in data
        
        # 설명 내용 검증
        explanation = data["explanation"]
        assert len(explanation) > 100  # 충분한 설명
        assert "더하기" in explanation or "sum" in explanation.lower()
    
    async def test_index_code_endpoint(self, client):
        """코드 인덱싱 API 테스트"""
        # Given
        index_request = {
            "file_path": "tests/fixtures/sample_java_files/Calculator.java",
            "language": "java"
        }
        
        # When
        response = client.post("/api/v1/index", json=index_request)
        
        # Then
        assert response.status_code == 201
        
        data = response.json()
        assert "indexed_methods" in data
        assert "processing_time" in data
        assert data["indexed_methods"] > 0
```

#### 2.2 사용자 시나리오 테스트
```python
# tests/e2e/test_user_scenarios.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestUserScenarios:
    """실제 사용자 시나리오 기반 E2E 테스트"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    async def test_developer_workflow_scenario(self, client):
        """개발자 워크플로우 시나리오 테스트"""
        # 시나리오: 새 프로젝트 파일 인덱싱 → 코드 검색 → 설명 요청
        
        # Step 1: 코드 파일 인덱싱
        index_response = client.post("/api/v1/index", json={
            "file_path": "tests/fixtures/sample_java_files/Calculator.java",
            "language": "java"
        })
        assert index_response.status_code == 201
        
        # Step 2: 관련 코드 검색
        search_response = client.get("/api/v1/search-snippet?query=addition method")
        assert search_response.status_code == 200
        
        search_data = search_response.json()
        assert len(search_data["results"]) > 0
        
        # Step 3: 코드 설명 요청
        explain_response = client.post("/api/v1/explain", json={
            "query": "덧셈 메서드의 동작 원리를 설명해주세요"
        })
        assert explain_response.status_code == 200
        
        explain_data = explain_response.json()
        assert "explanation" in explain_data
        assert len(explain_data["explanation"]) > 50
    
    async def test_code_review_scenario(self, client):
        """코드 리뷰 시나리오 테스트"""
        # 시나리오: 코드 검색 → 유사 코드 비교 → 개선 제안
        
        # Step 1: 특정 기능 코드 검색
        search_response = client.get("/api/v1/search-snippet?query=string validation")
        assert search_response.status_code == 200
        
        # Step 2: 코드 리뷰 및 개선 제안 요청
        review_response = client.post("/api/v1/explain", json={
            "query": "이 문자열 검증 코드를 개선할 수 있는 방법은?",
            "include_suggestions": True
        })
        assert review_response.status_code == 200
        
        review_data = review_response.json()
        assert "explanation" in review_data
        assert "suggestions" in review_data.get("metadata", {})
```

### 3. 성능 및 부하 테스트
```python
# tests/integration/test_performance.py
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.main import app

class TestPerformance:
    """성능 및 부하 테스트"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    async def test_concurrent_search_requests(self, client):
        """동시 검색 요청 처리 테스트"""
        # Given
        queries = [
            "calculate sum",
            "validate email",
            "parse json",
            "sort array",
            "handle exception"
        ]
        
        # When
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(
                    client.get, 
                    f"/api/v1/search-snippet?query={query}"
                )
                for query in queries * 4  # 20개 동시 요청
            ]
            
            responses = [future.result() for future in futures]
        
        end_time = time.time()
        
        # Then
        total_time = end_time - start_time
        assert total_time < 10.0  # 10초 이내 완료
        
        # 모든 요청 성공 검증
        for response in responses:
            assert response.status_code == 200
    
    async def test_memory_usage_monitoring(self, client):
        """메모리 사용량 모니터링 테스트"""
        import psutil
        import os
        
        # Given
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # When - 대량 요청 처리
        for i in range(100):
            response = client.get(f"/api/v1/search-snippet?query=test query {i}")
            assert response.status_code == 200
        
        # Then
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # 메모리 증가량 제한 (100MB 이내)
        assert memory_increase < 100
```

---

## ✅ 완료 기준

### 1. 기능 검증 완료
- [ ] 모든 주요 Flow 통합 테스트 통과
- [ ] E2E 테스트 시나리오 모두 성공
- [ ] API 엔드포인트 정상 동작 확인
- [ ] 에러 처리 로직 검증

### 2. 성능 기준 달성
- [ ] 단일 검색 요청: 2초 이내 응답
- [ ] 평균 검색 응답 시간: 1초 이내
- [ ] 동시 요청 처리: 10개 이상 동시 처리
- [ ] 메모리 사용량: 100MB 이내 증가

### 3. 품질 기준 충족
- [ ] 테스트 커버리지: 전체 90% 이상
- [ ] 통합 테스트 커버리지: 100%
- [ ] 모든 주요 사용자 시나리오 커버
- [ ] 성능 벤치마크 기준값 달성

### 4. 문서화 완료
- [ ] 테스트 실행 가이드 작성
- [ ] 성능 벤치마크 결과 보고서
- [ ] 테스트 실패 시 디버깅 가이드
- [ ] CI/CD 파이프라인 테스트 통합

---

## 🧪 테스트 실행 방법

```bash
# 전체 통합 테스트 실행
pytest tests/integration/ -v

# E2E 테스트 실행
pytest tests/e2e/ -v

# 성능 테스트 실행
pytest tests/integration/test_performance.py -v

# 커버리지 포함 전체 테스트
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# 특정 시나리오 테스트
pytest tests/e2e/test_user_scenarios.py::TestUserScenarios::test_developer_workflow_scenario -v
```

---

## 📊 성능 벤치마크 기준

| 메트릭 | 목표값 | 측정 방법 |
|-------|-------|----------|
| 검색 응답 시간 | < 2초 | 단일 요청 처리 시간 |
| 평균 응답 시간 | < 1초 | 100회 요청 평균 |
| 동시 처리 능력 | 10+ 요청 | 동시 요청 처리 수 |
| 메모리 사용량 | < 100MB 증가 | 대량 요청 후 메모리 증가량 |
| 인덱싱 처리 속도 | > 10 docs/sec | 문서 인덱싱 속도 |
| 검색 정확도 | > 85% | 관련성 점수 기반 평가 |

---

## 🎯 예상 결과

이 Task를 완료하면:

1. **전체 시스템 안정성** 보장
2. **성능 기준 준수** 확인
3. **사용자 시나리오** 검증 완료
4. **프로덕션 배포** 준비 완료
5. **지속적인 품질 관리** 기반 구축

하이브리드 RAG 시스템이 실제 운영 환경에서 안정적으로 동작할 수 있는 신뢰성을 확보하게 됩니다. 