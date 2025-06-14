#!/usr/bin/env python3
"""
실제 인덱싱된 데이터 디버깅 스크립트
"""
import sys
sys.path.append('/app')

try:
    from app.index.bm25_service import BM25IndexService
    from app.index.bm25_index import CodeTokenizer
    print("✅ 모듈 import 성공")
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    sys.exit(1)

async def debug_real_index():
    """실제 인덱싱된 데이터 확인"""
    print("=== 실제 BM25 인덱스 데이터 확인 ===")
    
    # BM25 서비스 인스턴스 생성
    service = BM25IndexService()
    collection_name = "springboot-real-test"
    
    try:
        # 해당 컬렉션 초기화
        await service.initialize(collection_name)
        
        if collection_name not in service.indexes:
            print(f"❌ 컬렉션 '{collection_name}'을 찾을 수 없음")
            return
            
        index = service.indexes[collection_name]
        
        print(f"인덱스 노드 수: {len(index.nodes)}")
        print(f"문서 맵 크기: {len(index.documents_map)}")
        
        # 각 노드 정보 출력
        for i, node in enumerate(index.nodes):
            print(f"\n--- 노드 {i+1} ---")
            print(f"ID: {node.id_}")
            print(f"메타데이터: {node.metadata}")
            print(f"텍스트 길이: {len(node.text)}")
            print(f"텍스트 미리보기: {node.text[:200]}...")
            
            # 토크나이저로 실제 토큰 확인
            tokenizer = CodeTokenizer()
            tokens = tokenizer.tokenize(node.text)
            print(f"토큰 수: {len(tokens)}")
            print(f"토큰 미리보기: {tokens[:20]}...")
            
            if i >= 2:  # 최대 3개까지만 출력
                break
        
        # 검색 테스트
        print("\n=== 실제 검색 테스트 ===")
        test_queries = ["BookController", "createBook", "book", "control"]
        
        for query in test_queries:
            print(f"\n쿼리: '{query}'")
            results = await service.search_keywords(
                query=query,
                collection_name=collection_name,
                limit=3
            )
            print(f"결과 수: {len(results)}")
            
            for j, result in enumerate(results):
                print(f"  결과 {j+1}: 점수={result.get('score', 'N/A')}, ID={result.get('id', 'N/A')}")
                content = result.get('content', '')
                print(f"  내용: {content[:100]}...")
                print()
        
    except Exception as e:
        print(f"❌ 디버깅 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_real_index()) 