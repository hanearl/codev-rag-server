import logging
import os
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorDBRestore:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        
    def upload_snapshot(self, collection_name: str, snapshot_path: str):
        """스냅샷 업로드"""
        try:
            if not os.path.exists(snapshot_path):
                raise FileNotFoundError(f"스냅샷 파일을 찾을 수 없습니다: {snapshot_path}")
            
            with open(snapshot_path, 'rb') as f:
                snapshot_data = f.read()
            
            # 스냅샷 업로드
            result = self.client.upload_snapshot(collection_name, snapshot_data)
            logger.info(f"스냅샷 업로드 완료: {result}")
            return result
        except Exception as e:
            logger.error(f"스냅샷 업로드 실패: {e}")
            raise
    
    def restore_from_snapshot(self, collection_name: str, snapshot_name: str):
        """스냅샷에서 복원"""
        try:
            # 스냅샷에서 복원
            result = self.client.restore_snapshot(collection_name, snapshot_name)
            logger.info(f"스냅샷 복원 완료: {result}")
            return result
        except Exception as e:
            logger.error(f"스냅샷 복원 실패: {e}")
            raise
    
    def restore_collection(self, collection_name: str, snapshot_path: str):
        """컬렉션 전체 복원"""
        try:
            # 기존 컬렉션 삭제 (선택사항)
            try:
                self.client.delete_collection(collection_name)
                logger.info(f"기존 컬렉션 '{collection_name}' 삭제 완료")
            except Exception:
                logger.info(f"기존 컬렉션 '{collection_name}'이 존재하지 않음")
            
            # 스냅샷 업로드
            self.upload_snapshot(collection_name, snapshot_path)
            
            # 스냅샷 파일명에서 스냅샷 이름 추출
            snapshot_name = os.path.basename(snapshot_path)
            
            # 스냅샷에서 복원
            self.restore_from_snapshot(collection_name, snapshot_name)
            
            logger.info(f"컬렉션 '{collection_name}' 복원 완료")
        except Exception as e:
            logger.error(f"컬렉션 복원 실패: {e}")
            raise


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Qdrant 복원 관리")
    parser.add_argument("--host", default="localhost", help="Qdrant 호스트")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant 포트")
    parser.add_argument("--collection", default="code_embeddings", help="컬렉션 이름")
    parser.add_argument("--snapshot-path", required=True, help="복원할 스냅샷 파일 경로")
    
    args = parser.parse_args()
    
    restore = VectorDBRestore(host=args.host, port=args.port)
    restore.restore_collection(args.collection, args.snapshot_path)


if __name__ == "__main__":
    main() 