import asyncio
import logging
from app.features.systems.factory import create_rag_server_vector, create_rag_server_bm25, create_rag_server_hybrid

logging.basicConfig(level=logging.INFO)

async def test_all_rag_systems():
    """모든 RAG 시스템 테스트"""
    
    print("=== 벡터 검색 시스템 테스트 ===")
    vector_system = create_rag_server_vector(
        base_url='http://localhost:8000',
        collection_name='springboot-real-test',
        name='test-vector'
    )
    
    results = await vector_system.retrieve('UserService', top_k=2)
    print(f"벡터 검색 결과 수: {len(results)}")
    for i, result in enumerate(results):
        print(f"  {i+1}. filepath: {result.filepath}")
        print(f"     content: {result.content[:50]}...")
        print(f"     metadata: {result.metadata.get('full_class_name', 'N/A')}")
    
    print("\n=== BM25 검색 시스템 테스트 ===")
    bm25_system = create_rag_server_bm25(
        base_url='http://localhost:8000',
        index_name='springboot-real-test',
        name='test-bm25'
    )
    
    results = await bm25_system.retrieve('UserService', top_k=2)
    print(f"BM25 검색 결과 수: {len(results)}")
    for i, result in enumerate(results):
        print(f"  {i+1}. filepath: {result.filepath}")
        print(f"     content: {result.content[:50]}...")
        print(f"     metadata: {result.metadata.get('full_class_name', 'N/A')}")
    
    print("\n=== 하이브리드 검색 시스템 테스트 ===")
    hybrid_system = create_rag_server_hybrid(
        base_url='http://localhost:8000',
        collection_name='springboot-real-test',
        index_name='springboot-real-test',
        vector_weight=0.7,
        bm25_weight=0.3,
        use_rrf=True,
        name='test-hybrid'
    )
    
    results = await hybrid_system.retrieve('UserService', top_k=2)
    print(f"하이브리드 검색 결과 수: {len(results)}")
    for i, result in enumerate(results):
        print(f"  {i+1}. filepath: {result.filepath}")
        print(f"     content: {result.content[:50]}...")
        print(f"     metadata: {result.metadata.get('full_class_name', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(test_all_rag_systems()) 