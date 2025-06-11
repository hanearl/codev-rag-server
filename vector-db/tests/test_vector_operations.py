import pytest
import time
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


@pytest.fixture
def qdrant_client():
    """Qdrant 클라이언트 fixture"""
    return QdrantClient(host="localhost", port=6333)


@pytest.fixture
def test_collection_name():
    """테스트 컬렉션 이름"""
    return "test_code_embeddings"


@pytest.fixture
def setup_test_collection(qdrant_client, test_collection_name):
    """테스트 컬렉션 설정"""
    # 기존 컬렉션 삭제 (있다면)
    try:
        qdrant_client.delete_collection(test_collection_name)
    except:
        pass
    
    # 테스트 컬렉션 생성
    qdrant_client.create_collection(
        collection_name=test_collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )
    
    # 인덱스 생성
    qdrant_client.create_payload_index(
        collection_name=test_collection_name,
        field_name="file_path",
        field_schema="keyword"
    )
    
    yield test_collection_name
    
    # 정리
    try:
        qdrant_client.delete_collection(test_collection_name)
    except:
        pass


def test_collection_creation(qdrant_client, setup_test_collection):
    """컬렉션 생성 테스트"""
    collection_name = setup_test_collection
    
    # 컬렉션 정보 조회
    info = qdrant_client.get_collection(collection_name)
    
    assert info.config.params.vectors.size == 384
    assert info.config.params.vectors.distance == Distance.COSINE


def test_vector_insertion(qdrant_client, setup_test_collection):
    """벡터 삽입 테스트"""
    collection_name = setup_test_collection
    
    # 테스트 데이터
    test_vector = [0.1] * 384
    test_payload = {
        "file_path": "test/example.py",
        "function_name": "test_function",
        "code_type": "function",
        "language": "python",
        "code_content": "def test_function():\n    pass",
        "line_start": 1,
        "line_end": 2,
        "created_at": "2023-01-01T00:00:00Z",
        "keywords": ["test", "function"]
    }
    
    # 벡터 삽입
    qdrant_client.upsert(
        collection_name=collection_name,
        points=[
            PointStruct(
                id=1,
                vector=test_vector,
                payload=test_payload
            )
        ]
    )
    
    # 삽입 확인
    points = qdrant_client.retrieve(
        collection_name=collection_name,
        ids=[1]
    )
    
    assert len(points) == 1
    assert points[0].payload["file_path"] == "test/example.py"
    assert points[0].payload["function_name"] == "test_function"


def test_vector_search(qdrant_client, setup_test_collection):
    """벡터 검색 테스트"""
    collection_name = setup_test_collection
    
    # 테스트 데이터 삽입
    test_vectors = [
        ([0.1] * 384, {"file_path": "test1.py", "function_name": "func1"}),
        ([0.2] * 384, {"file_path": "test2.py", "function_name": "func2"}),
        ([0.3] * 384, {"file_path": "test3.py", "function_name": "func3"})
    ]
    
    points = []
    for i, (vector, payload) in enumerate(test_vectors):
        points.append(PointStruct(
            id=i + 1,
            vector=vector,
            payload=payload
        ))
    
    qdrant_client.upsert(collection_name=collection_name, points=points)
    
    # 검색 쿼리
    query_vector = [0.15] * 384
    
    # 벡터 검색
    search_results = qdrant_client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=2
    )
    
    assert len(search_results) == 2
    assert all(result.score is not None for result in search_results)


def test_filtered_search(qdrant_client, setup_test_collection):
    """필터링된 검색 테스트"""
    collection_name = setup_test_collection
    
    # 테스트 데이터 삽입
    test_data = [
        ([0.1] * 384, {"file_path": "python/test1.py", "language": "python"}),
        ([0.2] * 384, {"file_path": "javascript/test2.js", "language": "javascript"}),
        ([0.3] * 384, {"file_path": "python/test3.py", "language": "python"})
    ]
    
    points = []
    for i, (vector, payload) in enumerate(test_data):
        points.append(PointStruct(
            id=i + 1,
            vector=vector,
            payload=payload
        ))
    
    qdrant_client.upsert(collection_name=collection_name, points=points)
    
    # 필터링된 검색
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    search_results = qdrant_client.search(
        collection_name=collection_name,
        query_vector=[0.15] * 384,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="language",
                    match=MatchValue(value="python")
                )
            ]
        ),
        limit=10
    )
    
    assert len(search_results) == 2
    assert all(result.payload["language"] == "python" for result in search_results) 