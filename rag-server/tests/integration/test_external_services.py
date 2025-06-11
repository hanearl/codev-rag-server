"""
외부 서비스 통합 테스트

이 테스트들은 실제 서비스들이 Docker Compose로 실행된 상태에서 수행됩니다.
"""
import pytest
import httpx
from app.core.clients import EmbeddingClient, LLMClient, VectorClient
from app.core.exceptions import EmbeddingServiceError, LLMServiceError, VectorDBError


@pytest.mark.integration
@pytest.mark.asyncio
async def test_embedding_service_integration():
    """임베딩 서비스와의 실제 통합 테스트"""
    # Given: Docker Compose로 embedding-server가 실행된 상태
    client = EmbeddingClient("http://localhost:8001")
    
    try:
        # When: 실제 임베딩 요청
        result = await client.embed_single({
            "text": "def hello_world(): print('Hello, World!')"
        })
        
        # Then: 임베딩 결과 검증
        assert "embedding" in result
        assert isinstance(result["embedding"], list)
        assert len(result["embedding"]) > 0
        
    except EmbeddingServiceError:
        # 서비스가 실행되지 않은 경우 건너뛰기
        pytest.skip("Embedding service not available")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_llm_service_integration():
    """LLM 서비스와의 실제 통합 테스트"""
    # Given: Docker Compose로 llm-server가 실행된 상태
    client = LLMClient("http://localhost:8002")
    
    try:
        # When: 실제 LLM 요청
        result = await client.chat_completion({
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "Write a simple Python function"}
            ]
        })
        
        # Then: LLM 응답 검증
        assert "choices" in result
        assert len(result["choices"]) > 0
        assert "message" in result["choices"][0]
        
    except LLMServiceError:
        # 서비스가 실행되지 않은 경우 건너뛰기
        pytest.skip("LLM service not available")


@pytest.mark.integration
def test_vector_db_integration():
    """벡터 DB와의 실제 통합 테스트"""
    # Given: Docker Compose로 Qdrant가 실행된 상태
    client = VectorClient("localhost", 6333)
    
    try:
        # When: 테스트 컬렉션 생성
        collection_name = "test_integration"
        collection_created = client.create_collection(collection_name, 384)
        
        # Then: 컬렉션 생성 검증
        assert collection_created is True
        
        # When: 임베딩 삽입
        test_embedding = [0.1] * 384  # 384차원 더미 임베딩
        point_id = client.insert_code_embedding(
            collection_name,
            test_embedding,
            {"file_path": "test.py", "function_name": "hello_world"}
        )
        
        # Then: 삽입 결과 검증
        assert point_id is not None
        
        # When: 하이브리드 검색
        search_results = client.hybrid_search(
            collection_name,
            test_embedding,
            keywords=["hello"],
            limit=5
        )
        
        # Then: 검색 결과 검증
        assert isinstance(search_results, list)
        assert len(search_results) >= 1
        assert "id" in search_results[0]
        assert "vector_score" in search_results[0]
        
    except VectorDBError:
        # 서비스가 실행되지 않은 경우 건너뛰기
        pytest.skip("Vector DB service not available")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling_integration():
    """에러 처리 integration 테스트"""
    # Given: 잘못된 URL의 클라이언트들
    embedding_client = EmbeddingClient("http://localhost:9999")  # 존재하지 않는 포트
    llm_client = LLMClient("http://localhost:9998")
    
    # When & Then: 연결 실패 시 적절한 예외 발생
    with pytest.raises(EmbeddingServiceError):
        await embedding_client.embed_single({"text": "test"})
    
    with pytest.raises(LLMServiceError):
        await llm_client.chat_completion({"messages": []})


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_retry_mechanism_integration():
    """재시도 메커니즘 integration 테스트"""
    # Given: 재시도 설정이 있는 클라이언트
    client = EmbeddingClient("http://localhost:8001", max_retries=2)
    
    try:
        # When: 정상적인 요청 (재시도 없이 성공해야 함)
        result = await client.embed_single({"text": "retry test"})
        
        # Then: 성공적으로 결과 반환
        assert "embedding" in result
        
    except EmbeddingServiceError:
        # 서비스가 불안정하거나 실행되지 않은 경우
        pytest.skip("Embedding service not available or unstable")


@pytest.mark.integration
@pytest.mark.slow
def test_vector_search_performance():
    """벡터 검색 성능 테스트"""
    try:
        # Given: 벡터 DB 클라이언트
        client = VectorClient()
        
        # When: 검색 수행 및 시간 측정
        import time
        start_time = time.time()
        
        # 더미 검색 (실제 데이터가 있다고 가정)
        results = client.hybrid_search(
            "test_performance",
            [0.1] * 384,  # 더미 임베딩
            keywords=["test", "function"],
            limit=100
        )
        
        end_time = time.time()
        search_time = end_time - start_time
        
        # Then: 성능 기준 검증
        assert search_time < 2.0  # 2초 이내
        assert isinstance(results, list)
        
    except VectorDBError:
        pytest.skip("Vector DB service not available")


# 테스트용 conftest.py도 함께 생성
"""
tests/conftest.py에 추가할 내용:

@pytest.fixture(scope="session")
def docker_services():
    '''Docker Compose 서비스 관리'''
    # Docker Compose 서비스 시작
    subprocess.run(["docker-compose", "up", "-d"], check=True)
    
    # 서비스가 준비될 때까지 대기
    time.sleep(10)
    
    yield
    
    # 테스트 완료 후 서비스 정리
    subprocess.run(["docker-compose", "down"], check=True)
""" 