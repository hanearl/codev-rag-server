#!/usr/bin/env python3
"""
중복 인덱싱 문제 해결 스크립트
"""
import sys
import os
import shutil
sys.path.append('/app')

async def fix_duplicate_index():
    """중복 인덱싱 문제 해결"""
    print("=== 중복 인덱싱 문제 해결 ===")
    
    collection_name = "springboot-real-test"
    
    try:
        from app.index.bm25_service import BM25IndexService
        
        service = BM25IndexService()
        
        # 1. 기존 인덱스 완전 삭제
        print("1. 기존 인덱스 완전 삭제...")
        index_dir = f"/app/data/bm25_indexes/{collection_name}"
        if os.path.exists(index_dir):
            shutil.rmtree(index_dir)
            print(f"✅ 디렉토리 삭제: {index_dir}")
        
        # 2. 메모리에서도 제거
        if collection_name in service.indexes:
            del service.indexes[collection_name]
            print(f"✅ 메모리에서 인덱스 제거")
        
        # 3. 새로 초기화
        print("2. 새로운 인덱스 초기화...")
        await service.initialize(collection_name)
        
        # 4. 확인
        if collection_name in service.indexes:
            index = service.indexes[collection_name]
            print(f"✅ 새 인덱스 생성됨")
            print(f"   노드 수: {len(index.nodes)}")
            print(f"   문서 맵 크기: {len(index.documents_map)}")
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
    asyncio.run(fix_duplicate_index()) 