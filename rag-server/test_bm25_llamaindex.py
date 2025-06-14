#!/usr/bin/env python3
"""
LlamaIndex BM25Retriever 점수 계산 테스트
"""
import sys
sys.path.append('/app')

try:
    from llama_index.retrievers.bm25 import BM25Retriever
    from llama_index.core.schema import TextNode
    print("✅ LlamaIndex import 성공")
except ImportError as e:
    print(f"❌ LlamaIndex import 실패: {e}")
    sys.exit(1)

def test_bm25_direct():
    """LlamaIndex BM25Retriever 직접 테스트"""
    print("=== LlamaIndex BM25Retriever 직접 테스트 ===")
    
    try:
        # 테스트 노드들 생성
        nodes = [
            TextNode(text="public class BookController { public String createBook() { return book created; } }", id_="1"),
            TextNode(text="public class UserController { public void createUser() { System.out.println(user created); } }", id_="2"),
            TextNode(text="public class ProductService { public Product getProduct() { return new Product(); } }", id_="3"),
        ]
        
        print(f"노드 수: {len(nodes)}")
        for i, node in enumerate(nodes):
            print(f"노드 {i+1}: {node.text[:50]}...")
        
        # BM25Retriever 생성
        print("\nBM25Retriever 생성 중...")
        retriever = BM25Retriever.from_defaults(
            nodes=nodes,
            similarity_top_k=5
        )
        
        print(f"✅ BM25Retriever 생성 완료")
        print(f"Retriever type: {type(retriever)}")
        
        if hasattr(retriever, 'bm25'):
            print(f"BM25 객체: {type(retriever.bm25)}")
            if hasattr(retriever.bm25, 'k1') and hasattr(retriever.bm25, 'b'):
                print(f"BM25 파라미터: k1={retriever.bm25.k1}, b={retriever.bm25.b}")
        
        # 검색 테스트
        test_queries = ["BookController", "createBook", "book", "class"]
        
        for query in test_queries:
            print(f"\n--- 쿼리: '{query}' ---")
            
            try:
                results = retriever.retrieve(query)
                print(f"결과 수: {len(results)}")
                
                for j, result in enumerate(results):
                    print(f"  결과 {j+1}:")
                    print(f"    ID: {result.node.id_}")
                    print(f"    점수: {result.score}")
                    print(f"    내용: {result.node.text[:50]}...")
                    
                    # 점수가 None이거나 0인지 확인
                    if result.score is None:
                        print(f"    ⚠️ 점수가 None!")
                    elif result.score == 0.0:
                        print(f"    ⚠️ 점수가 0.0!")
                    else:
                        print(f"    ✅ 정상 점수: {result.score}")
                
            except Exception as e:
                print(f"❌ 검색 실패: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bm25_direct() 