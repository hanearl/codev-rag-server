#!/usr/bin/env python3
"""
HuggingFace 모델을 로컬에 다운로드하는 스크립트
"""

from sentence_transformers import SentenceTransformer
import os

def download_model():
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    save_path = "./models/all-MiniLM-L6-v2"
    
    # 모델 디렉토리 생성
    os.makedirs("./models", exist_ok=True)
    
    print(f"🔄 모델 다운로드 시작: {model_name}")
    print(f"📂 저장 경로: {os.path.abspath(save_path)}")
    
    try:
        # 모델 다운로드 및 저장
        model = SentenceTransformer(model_name)
        model.save(save_path)
        
        print("✅ 모델 다운로드 완료!")
        print(f"📁 모델 파일 위치: {os.path.abspath(save_path)}")
        
        # 테스트 임베딩
        test_text = "Hello world"
        embedding = model.encode(test_text)
        print(f"🧪 테스트 임베딩 차원: {len(embedding)}")
        
    except Exception as e:
        print(f"❌ 모델 다운로드 실패: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = download_model()
    exit(0 if success else 1) 