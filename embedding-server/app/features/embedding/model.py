from sentence_transformers import SentenceTransformer
from typing import List, Union


class EmbeddingModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.tokenizer = self.model.tokenizer
    
    def encode(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """텍스트를 임베딩 벡터로 변환"""
        embeddings = self.model.encode(text)
        
        if isinstance(text, str):
            return embeddings.tolist()
        else:
            return [emb.tolist() for emb in embeddings] 