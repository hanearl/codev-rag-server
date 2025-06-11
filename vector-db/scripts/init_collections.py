import asyncio
import logging
import json
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, CollectionInfo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorDBInitializer:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        
    def load_collection_config(self, config_path: str = "config/collection_config.json"):
        """컬렉션 설정 파일 로드"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"설정 파일 파싱 오류: {e}")
            raise
        
    def create_code_embeddings_collection(self):
        """코드 임베딩 컬렉션 생성"""
        config = self.load_collection_config()
        collection_name = config["collection_name"]
        
        try:
            # 기존 컬렉션 확인
            collections = self.client.get_collections()
            existing_names = [col.name for col in collections.collections]
            
            if collection_name in existing_names:
                logger.info(f"컬렉션 '{collection_name}'이 이미 존재합니다.")
                return
            
            # 컬렉션 생성
            vector_config = config["vector_config"]
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_config["size"],
                    distance=Distance.COSINE if vector_config["distance"] == "Cosine" else Distance.DOT
                )
            )
            
            logger.info(f"컬렉션 '{collection_name}' 생성 완료")
            
            # 인덱스 설정
            for index_config in config.get("indexes", []):
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name=index_config["field_name"],
                    field_schema=index_config["field_schema"]
                )
                logger.info(f"인덱스 생성 완료: {index_config['field_name']}")
            
            logger.info("모든 페이로드 인덱스 생성 완료")
            
        except Exception as e:
            logger.error(f"컬렉션 생성 실패: {e}")
            raise
    
    def get_collection_info(self, collection_name: str = "code_embeddings"):
        """컬렉션 정보 조회"""
        try:
            info = self.client.get_collection(collection_name)
            logger.info(f"컬렉션 정보: {info}")
            return info
        except Exception as e:
            logger.error(f"컬렉션 정보 조회 실패: {e}")
            return None
    
    def delete_collection(self, collection_name: str = "code_embeddings"):
        """컬렉션 삭제 (개발/테스트용)"""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"컬렉션 '{collection_name}' 삭제 완료")
        except Exception as e:
            logger.error(f"컬렉션 삭제 실패: {e}")
            raise


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Qdrant 컬렉션 관리")
    parser.add_argument("--host", default="localhost", help="Qdrant 호스트")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant 포트")
    parser.add_argument("--delete", action="store_true", help="컬렉션 삭제")
    parser.add_argument("--info", action="store_true", help="컬렉션 정보 조회")
    
    args = parser.parse_args()
    
    initializer = VectorDBInitializer(host=args.host, port=args.port)
    
    if args.delete:
        initializer.delete_collection()
    elif args.info:
        initializer.get_collection_info()
    else:
        # 컬렉션 생성
        initializer.create_code_embeddings_collection()
        
        # 컬렉션 정보 확인
        initializer.get_collection_info()


if __name__ == "__main__":
    main() 