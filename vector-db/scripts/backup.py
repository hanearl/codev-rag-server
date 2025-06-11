import logging
import os
import datetime
from qdrant_client import QdrantClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorDBBackup:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        
    def create_snapshot(self, collection_name: str = "code_embeddings"):
        """컬렉션 스냅샷 생성"""
        try:
            # 스냅샷 생성
            snapshot_info = self.client.create_snapshot(collection_name)
            logger.info(f"스냅샷 생성 완료: {snapshot_info}")
            return snapshot_info
        except Exception as e:
            logger.error(f"스냅샷 생성 실패: {e}")
            raise
    
    def list_snapshots(self, collection_name: str = "code_embeddings"):
        """스냅샷 목록 조회"""
        try:
            snapshots = self.client.list_snapshots(collection_name)
            logger.info(f"스냅샷 목록: {snapshots}")
            return snapshots
        except Exception as e:
            logger.error(f"스냅샷 목록 조회 실패: {e}")
            raise
    
    def download_snapshot(self, collection_name: str, snapshot_name: str, output_dir: str = "backups"):
        """스냅샷 다운로드"""
        try:
            # 출력 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)
            
            # 스냅샷 다운로드
            snapshot_data = self.client.download_snapshot(collection_name, snapshot_name)
            
            # 파일 저장
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{collection_name}_{timestamp}_{snapshot_name}"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(snapshot_data)
            
            logger.info(f"스냅샷 다운로드 완료: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"스냅샷 다운로드 실패: {e}")
            raise
    
    def backup_collection(self, collection_name: str = "code_embeddings", output_dir: str = "backups"):
        """컬렉션 전체 백업"""
        try:
            # 스냅샷 생성
            snapshot_info = self.create_snapshot(collection_name)
            snapshot_name = snapshot_info.name
            
            # 스냅샷 다운로드
            filepath = self.download_snapshot(collection_name, snapshot_name, output_dir)
            
            logger.info(f"백업 완료: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"백업 실패: {e}")
            raise


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Qdrant 백업 관리")
    parser.add_argument("--host", default="localhost", help="Qdrant 호스트")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant 포트")
    parser.add_argument("--collection", default="code_embeddings", help="컬렉션 이름")
    parser.add_argument("--output-dir", default="backups", help="백업 출력 디렉토리")
    parser.add_argument("--list", action="store_true", help="스냅샷 목록 조회")
    
    args = parser.parse_args()
    
    backup = VectorDBBackup(host=args.host, port=args.port)
    
    if args.list:
        backup.list_snapshots(args.collection)
    else:
        backup.backup_collection(args.collection, args.output_dir)


if __name__ == "__main__":
    main() 