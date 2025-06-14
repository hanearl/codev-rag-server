import asyncio
import logging
from app.features.systems.factory import create_rag_server_vector, create_rag_server_bm25, create_rag_server_hybrid
from app.features.evaluation.service import EvaluationService, EvaluationOptions
import json

logging.basicConfig(level=logging.INFO)

async def debug_rag_systems():
    """RAG 서버들의 검색 결과를 디버깅"""
    
    # 샘플 질문 (combined-dataset에서 가져온 실제 질문)
    sample_questions = [
        {
            "question": "회원이 연체료를 납부하면 대출 가능 상태로 변경하는 시스템을 구현해줘",
            "ground_truth": ["com.skax.library.service.impl.FineServiceImpl", "com.skax.library.service.impl.MemberServiceImpl"]
        },
        {
            "question": "BookController에 신간 도서 목록 조회 API를 구현해줘", 
            "ground_truth": ["com.skax.library.controller.BookController"]
        }
    ]
    
    # 벡터 시스템 테스트
    print("=== 벡터 검색 시스템 디버깅 ===")
    vector_system = create_rag_server_vector(
        base_url='http://localhost:8000',
        collection_name='springboot-real-test',
        name='debug-vector'
    )
    
    for i, q in enumerate(sample_questions):
        print(f"\n--- 질문 {i+1}: {q['question'][:50]}... ---")
        
        # 검색 수행
        results = await vector_system.retrieve(q['question'], top_k=5)
        print(f"검색 결과 수: {len(results)}")
        
        if results:
            for j, result in enumerate(results):
                print(f"  결과 {j+1}:")
                print(f"    filepath: {result.filepath}")
                print(f"    content: {result.content[:50]}...")
                print(f"    score: {result.score}")
                print(f"    metadata: {result.metadata}")
        else:
            print("  검색 결과 없음!")
        
        # 클래스패스 변환 테스트
        eval_service = EvaluationService()
        options = EvaluationOptions(
            convert_to_classpath=True,
            remove_method_names=True
        )
        
        try:
            # 예측값 변환
            predictions = [r.filepath for r in results if r.filepath]
            print(f"  원본 predictions: {predictions}")
            
            if predictions:
                converted_predictions = eval_service._convert_predictions_to_classpaths(predictions, results, options)
                print(f"  변환된 predictions: {converted_predictions}")
            else:
                print("  predictions가 비어있음!")
                
            # 정답 변환  
            converted_ground_truth = eval_service._convert_ground_truth_to_classpaths(q['ground_truth'], options)
            print(f"  변환된 ground_truth: {converted_ground_truth}")
            
        except Exception as e:
            print(f"  변환 오류: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_rag_systems()) 