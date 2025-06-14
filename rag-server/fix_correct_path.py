#!/usr/bin/env python3
"""
올바른 경로로 중복 인덱싱 문제 해결 스크립트
"""
import sys
import os
import shutil
sys.path.append('/app')

async def fix_correct_path():
    """올바른 경로로 중복 인덱싱 문제 해결"""
    print("=== 올바른 경로로 중복 인덱싱 문제 해결 ===")
    
    collection_name = "springboot-real-test"
    
    try:
        from app.index.bm25_service import BM25IndexService
        
        # 1. 모든 가능한 경로 확인 및 삭제
        possible_paths = [
            f"/app/data/bm25_index/{collection_name}",     # 실제 경로
            f"/app/data/bm25_indexes/{collection_name}",   # 잘못된 경로
            f"data/bm25_index/{collection_name}",          # 상대 경로
            f"data/bm25_indexes/{collection_name}"         # 잘못된 상대 경로
        ]
        
        print("1. 모든 가능한 경로에서 기존 인덱스 삭제...")
        for path in possible_paths:
            if os.path.exists(path):
                shutil.rmtree(path)
                print(f"✅ 삭제됨: {path}")
            else:
                print(f"❌ 존재하지 않음: {path}")
        
        # 2. 서비스 인스턴스 새로 생성
        service = BM25IndexService()
        
        # 3. 메모리에서도 제거
        if collection_name in service.indexes:
            del service.indexes[collection_name]
            print(f"✅ 메모리에서 인덱스 제거")
        
        if collection_name in service._initialized:
            del service._initialized[collection_name]
            print(f"✅ 초기화 상태 제거")
        
        # 4. 새로 초기화
        print("2. 완전히 새로운 인덱스 초기화...")
        await service.initialize(collection_name)
        
        # 5. 확인
        if collection_name in service.indexes:
            index = service.indexes[collection_name]
            print(f"✅ 새 인덱스 생성됨")
            print(f"   노드 수: {len(index.nodes)}")
            print(f"   문서 맵 크기: {len(index.documents_map)}")
            print(f"   인덱스 경로: {index.config.index_path}")
        else:
            print("❌ 인덱스 생성 실패")
        
        print("\n=== 해결 완료 ===")
        print("이제 다시 인덱싱을 시도하세요.")
        
    except Exception as e:
        print(f"❌ 수정 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(fix_correct_path()) 