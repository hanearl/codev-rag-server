from sentence_transformers import SentenceTransformer
from typing import List, Union
import os

class EmbeddingModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        
        # 로컬 모델 경로 확인 (Docker 컨테이너 내부 경로)
        local_model_path = "/app/models/all-MiniLM-L6-v2"
        
        if os.path.exists(local_model_path):
            print(f"✅ 로컬 모델 사용: {local_model_path}")
            self.model = SentenceTransformer(local_model_path)
        else:
            print(f"⚠️ 로컬 모델 없음, 온라인 다운로드 시도: {model_name}")
            # 원래 방식으로 폴백 (네트워크가 되는 환경에서)
            self.model = SentenceTransformer(model_name)
        
        self.tokenizer = self.model.tokenizer
    
    def encode(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """텍스트를 임베딩 벡터로 변환"""
        embeddings = self.model.encode(text)
        
        if isinstance(text, str):
            return embeddings.tolist()
        else:
            return [emb.tolist() for emb in embeddings] 