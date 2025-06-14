"""
RAG 서버 어댑터 사용 예제

이 파일은 새로 추가된 RAG 서버 어댑터들(벡터, BM25, 하이브리드)의 
사용법을 보여주는 예제입니다.
"""
import asyncio
from typing import List
from app.features.systems.factory import (
    create_rag_server_vector,
    create_rag_server_bm25, 
    create_rag_server_hybrid,
    create_all_rag_server_systems,
    RAGSystemTemplates
)
from app.features.systems.interface import RetrievalResult


async def demo_vector_search():
    """벡터 검색 예제"""
    print("=== 벡터 검색 예제 ===")
    
    # 벡터 검색 시스템 생성
    vector_system = create_rag_server_vector(
        base_url="http://localhost:8000",
        collection_name="code_chunks"
    )
    
    try:
        # 헬스체크
        is_healthy = await vector_system.health_check()
        print(f"벡터 검색 시스템 상태: {'정상' if is_healthy else '비정상'}")
        
        if is_healthy:
            # 검색 수행
            query = "파이썬 함수 정의 방법"
            results = await vector_system.retrieve(query, top_k=5)
            
            print(f"\n쿼리: {query}")
            print(f"결과 수: {len(results)}")
            
            for i, result in enumerate(results[:3], 1):
                print(f"\n{i}. 점수: {result.score:.4f}")
                print(f"   내용: {result.content[:100]}...")
                print(f"   파일: {result.filepath}")
                print(f"   검색 타입: {result.metadata.get('search_type')}")
        
    finally:
        await vector_system.close()


async def demo_bm25_search():
    """BM25 검색 예제"""
    print("\n=== BM25 검색 예제 ===")
    
    # BM25 검색 시스템 생성
    bm25_system = create_rag_server_bm25(
        base_url="http://localhost:8000",
        index_name="code_index"
    )
    
    try:
        # 헬스체크
        is_healthy = await bm25_system.health_check()
        print(f"BM25 검색 시스템 상태: {'정상' if is_healthy else '비정상'}")
        
        if is_healthy:
            # 검색 수행
            query = "def function class method"
            results = await bm25_system.retrieve(query, top_k=5)
            
            print(f"\n쿼리: {query}")
            print(f"결과 수: {len(results)}")
            
            for i, result in enumerate(results[:3], 1):
                print(f"\n{i}. 점수: {result.score:.4f}")
                print(f"   내용: {result.content[:100]}...")
                print(f"   파일: {result.filepath}")
                print(f"   검색 타입: {result.metadata.get('search_type')}")
        
    finally:
        await bm25_system.close()


async def demo_hybrid_search():
    """하이브리드 검색 예제"""
    print("\n=== 하이브리드 검색 예제 ===")
    
    # 하이브리드 검색 시스템 생성
    hybrid_system = create_rag_server_hybrid(
        base_url="http://localhost:8000",
        collection_name="code_chunks",
        index_name="code_index",
        vector_weight=0.7,
        bm25_weight=0.3,
        use_rrf=True,
        rrf_k=60
    )
    
    try:
        # 헬스체크
        is_healthy = await hybrid_system.health_check()
        print(f"하이브리드 검색 시스템 상태: {'정상' if is_healthy else '비정상'}")
        
        if is_healthy:
            # 검색 수행
            query = "클래스 상속과 메소드 오버라이딩"
            results = await hybrid_system.retrieve(query, top_k=5)
            
            print(f"\n쿼리: {query}")
            print(f"결과 수: {len(results)}")
            
            for i, result in enumerate(results[:3], 1):
                print(f"\n{i}. 점수: {result.score:.4f}")
                print(f"   내용: {result.content[:100]}...")
                print(f"   파일: {result.filepath}")
                print(f"   검색 타입: {result.metadata.get('search_type')}")
                print(f"   융합 방법: {result.metadata.get('fusion_method')}")
                print(f"   가중치: {result.metadata.get('weights_used')}")
        
    finally:
        await hybrid_system.close()


async def demo_all_systems():
    """모든 시스템 비교 예제"""
    print("\n=== 모든 시스템 비교 예제 ===")
    
    # 모든 시스템 생성
    systems = create_all_rag_server_systems(
        base_url="http://localhost:8000",
        collection_name="code_chunks",
        index_name="code_index"
    )
    
    query = "파이썬 리스트 컴프리헨션"
    print(f"쿼리: {query}")
    
    try:
        for system_name, system in systems.items():
            print(f"\n--- {system_name.upper()} 검색 결과 ---")
            
            try:
                results = await system.retrieve(query, top_k=3)
                
                for i, result in enumerate(results, 1):
                    print(f"{i}. 점수: {result.score:.4f} | 파일: {result.filepath}")
                    print(f"   내용: {result.content[:80]}...")
                    
            except Exception as e:
                print(f"검색 실패: {e}")
    
    finally:
        # 모든 시스템 정리
        for system in systems.values():
            await system.close()


async def demo_system_info():
    """시스템 정보 조회 예제"""
    print("\n=== 시스템 정보 조회 예제 ===")
    
    # 하이브리드 시스템으로 예제
    hybrid_system = create_rag_server_hybrid()
    
    try:
        info = await hybrid_system.get_system_info()
        
        print(f"시스템 타입: {info['system_type']}")
        print(f"검색 타입: {info['retrieval_type']}")
        print(f"시스템 이름: {info['name']}")
        print(f"기본 URL: {info['base_url']}")
        
        if "hybrid_search_info" in info:
            hybrid_info = info["hybrid_search_info"]
            print(f"\n하이브리드 검색 상세 정보:")
            print(f"- 검색 서비스 상태: {hybrid_info['search_service']}")
            print(f"- 벡터 가중치: {hybrid_info['vector_weight']}")
            print(f"- BM25 가중치: {hybrid_info['bm25_weight']}")
            print(f"- RRF 사용: {hybrid_info['use_rrf']}")
            print(f"- 현재 컬렉션: {hybrid_info['current_collection']}")
            print(f"- 현재 인덱스: {hybrid_info['current_index']}")
            print(f"- 지원 기능: {list(hybrid_info['features'].keys())}")
    
    finally:
        await hybrid_system.close()


async def demo_config_templates():
    """설정 템플릿 사용 예제"""
    print("\n=== 설정 템플릿 사용 예제 ===")
    
    # 다양한 설정으로 시스템 생성
    configs = [
        RAGSystemTemplates.rag_server_vector("http://localhost:8000", collection_name="test_collection"),
        RAGSystemTemplates.rag_server_bm25("http://localhost:8000", index_name="test_index"),
        RAGSystemTemplates.rag_server_hybrid(
            "http://localhost:8000", 
            vector_weight=0.8, 
            bm25_weight=0.2,
            use_rrf=False
        )
    ]
    
    for config in configs:
        print(f"\n설정: {config.name}")
        print(f"- 시스템 타입: {config.system_type}")
        print(f"- 검색 타입: {config.retrieval_type}")
        print(f"- 컬렉션: {getattr(config, 'collection_name', 'N/A')}")
        print(f"- 인덱스: {getattr(config, 'index_name', 'N/A')}")
        if hasattr(config, 'vector_weight'):
            print(f"- 벡터 가중치: {config.vector_weight}")
            print(f"- BM25 가중치: {config.bm25_weight}")
            print(f"- RRF 사용: {config.use_rrf}")


async def main():
    """메인 데모 함수"""
    print("RAG 서버 어댑터 사용 예제 시작")
    print("=" * 50)
    
    try:
        # 각 검색 타입별 예제
        await demo_vector_search()
        await demo_bm25_search()
        await demo_hybrid_search()
        
        # 시스템 비교 예제
        await demo_all_systems()
        
        # 시스템 정보 조회 예제
        await demo_system_info()
        
        # 설정 템플릿 예제
        await demo_config_templates()
        
    except Exception as e:
        print(f"데모 실행 중 오류 발생: {e}")
    
    print("\n" + "=" * 50)
    print("RAG 서버 어댑터 사용 예제 완료")


if __name__ == "__main__":
    # 비동기 실행
    asyncio.run(main()) 