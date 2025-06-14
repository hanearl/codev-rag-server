#!/usr/bin/env python3
"""
기본 토크나이저 vs 커스텀 토크나이저 비교 테스트
"""
import sys
sys.path.append('/app')

try:
    from llama_index.retrievers.bm25 import BM25Retriever
    from llama_index.core.schema import TextNode
    from app.index.bm25_index import CodeTokenizer
    print("✅ import 성공")
except ImportError as e:
    print(f"❌ import 실패: {e}")
    sys.exit(1)

def test_tokenizer_comparison():
    """토크나이저 비교 테스트"""
    print("=== 기본 토크나이저 vs 커스텀 토크나이저 비교 ===")
    
    # 테스트 코드들
    test_codes = [
        "public class BookController { public String createBook() { return book created; } }",
        "public class UserController { public void createUser() { System.out.println(user created); } }",
        "public class ProductService { public Product getProduct() { return new Product(); } }",
        "@RestController @RequestMapping(\"/api/books\") public class BookController extends BaseController implements BookInterface {}"
    ]
    
    # 커스텀 토크나이저 생성
    custom_tokenizer = CodeTokenizer()
    
    print("\n=== 토크나이저 결과 비교 ===")
    for i, code in enumerate(test_codes):
        print(f"\n--- 테스트 코드 {i+1} ---")
        print(f"원본: {code}")
        
        # 커스텀 토크나이저 결과
        custom_tokens = custom_tokenizer.tokenize(code)
        print(f"커스텀: {custom_tokens}")
        
        # 기본 토크나이저 시뮬레이션 (공백 기반)
        basic_tokens = code.lower().split()
        print(f"기본: {basic_tokens}")
        
        print(f"커스텀 토큰 수: {len(custom_tokens)}, 기본 토큰 수: {len(basic_tokens)}")
    
    print("\n=== BM25 검색 성능 비교 ===")
    
    # 테스트 노드들 생성
    nodes = [
        TextNode(text=test_codes[0], id_="1"),
        TextNode(text=test_codes[1], id_="2"),
        TextNode(text=test_codes[2], id_="3"),
        TextNode(text=test_codes[3], id_="4"),
    ]
    
    # 1. 기본 토크나이저로 BM25
    print("\n--- 기본 토크나이저 BM25 ---")
    basic_retriever = BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=5)
    
    test_queries = ["BookController", "createBook", "RestController", "BaseController"]
    
    for query in test_queries:
        print(f"\n쿼리: '{query}'")
        results = basic_retriever.retrieve(query)
        print(f"기본 BM25 결과:")
        for j, result in enumerate(results[:2]):
            print(f"  {j+1}: 점수={result.score:.4f}, ID={result.node.id_}")
    
    # 2. 커스텀 토크나이저로 BM25
    print("\n--- 커스텀 토크나이저 BM25 ---")
    custom_retriever = BM25Retriever.from_defaults(
        nodes=nodes, 
        tokenizer=custom_tokenizer.tokenize,
        similarity_top_k=5
    )
    
    for query in test_queries:
        print(f"\n쿼리: '{query}'")
        results = custom_retriever.retrieve(query)
        print(f"커스텀 BM25 결과:")
        for j, result in enumerate(results[:2]):
            print(f"  {j+1}: 점수={result.score:.4f}, ID={result.node.id_}")
    
    print("\n=== 코드 특화 기능 테스트 ===")
    
    # CamelCase 분리 테스트
    camel_case_examples = [
        "getUserById",
        "BookController", 
        "createBookMethod",
        "setUserNameAndEmail"
    ]
    
    print("\nCamelCase 분리 테스트:")
    for example in camel_case_examples:
        custom_tokens = custom_tokenizer.tokenize(example)
        basic_tokens = example.lower().split()
        print(f"'{example}' → 커스텀: {custom_tokens}, 기본: {basic_tokens}")

if __name__ == "__main__":
    test_tokenizer_comparison() 