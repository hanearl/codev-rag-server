from typing import List, Dict, Any, Optional, Union
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.schema import TextNode, NodeWithScore
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import uuid
import logging
from datetime import datetime

from .base_index import BaseIndex, IndexedDocument
from app.retriever.document_builder import EnhancedDocument
from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorIndexConfig:
    """Vector Index 설정"""
    
    def __init__(
        self,
        collection_name: str = "code_vectors",
        vector_size: int = 1536,  # OpenAI embedding size
        distance: Distance = Distance.COSINE,
        qdrant_url: str = None,
        qdrant_port: int = 6333,
        qdrant_grpc_port: int = 6334,
        qdrant_prefer_grpc: bool = False,
        qdrant_https: bool = False,
        qdrant_api_key: str = None,
        similarity_top_k: int = 10,
        retrieval_mode: str = "similarity"  # similarity, mmr, etc.
    ):
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        self.qdrant_url = qdrant_url or f"http://{settings.qdrant_host}:{settings.qdrant_port}"
        self.qdrant_port = qdrant_port
        self.qdrant_grpc_port = qdrant_grpc_port
        self.qdrant_prefer_grpc = qdrant_prefer_grpc
        self.qdrant_https = qdrant_https
        self.qdrant_api_key = qdrant_api_key
        self.similarity_top_k = similarity_top_k
        self.retrieval_mode = retrieval_mode


class CodeVectorIndex(BaseIndex):
    """코드 벡터 인덱스"""
    
    def __init__(self, config: VectorIndexConfig = None):
        self.config = config or VectorIndexConfig()
        self.client = None
        self.vector_store = None
        self.index = None
        self.retriever = None
        self.query_engine = None
    
    async def setup(self):
        """인덱스 초기화"""
        try:
            # Qdrant 클라이언트 생성
            self.client = QdrantClient(
                url=self.config.qdrant_url,
                port=self.config.qdrant_port,
                grpc_port=self.config.qdrant_grpc_port,
                prefer_grpc=self.config.qdrant_prefer_grpc,
                https=self.config.qdrant_https,
                api_key=self.config.qdrant_api_key
            )
            
            # 컬렉션 존재 확인 및 생성
            await self._ensure_collection_exists()
            
            # Vector Store 생성
            self.vector_store = QdrantVectorStore(
                client=self.client,
                collection_name=self.config.collection_name
            )
            
            # Storage Context 설정
            storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store
            )
            
            # Vector Index 생성 또는 로드
            try:
                self.index = VectorStoreIndex.from_vector_store(
                    vector_store=self.vector_store
                )
            except Exception:
                # 빈 인덱스 생성
                self.index = VectorStoreIndex(
                    nodes=[],
                    storage_context=storage_context
                )
            
            # Retriever 생성
            self.retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=self.config.similarity_top_k
            )
            
            # Query Engine 생성 (선택적)
            self.query_engine = RetrieverQueryEngine(
                retriever=self.retriever
            )
            
            logger.info(f"Vector Index 초기화 완료: {self.config.collection_name}")
            
        except Exception as e:
            logger.error(f"Vector Index 초기화 실패: {e}")
            raise
    
    async def _ensure_collection_exists(self):
        """컬렉션 존재 확인 및 생성"""
        collections = await self._get_collections()
        
        if self.config.collection_name not in collections:
            await self._create_collection()
    
    async def _get_collections(self) -> List[str]:
        """컬렉션 목록 조회"""
        try:
            response = self.client.get_collections()
            return [collection.name for collection in response.collections]
        except Exception as e:
            logger.error(f"컬렉션 목록 조회 실패: {e}")
            return []
    
    async def _create_collection(self):
        """컬렉션 생성"""
        try:
            self.client.create_collection(
                collection_name=self.config.collection_name,
                vectors_config=VectorParams(
                    size=self.config.vector_size,
                    distance=self.config.distance
                )
            )
            logger.info(f"컬렉션 생성 완료: {self.config.collection_name}")
        except Exception as e:
            logger.error(f"컬렉션 생성 실패: {e}")
            raise
    
    async def add_documents(self, documents: List[Union[EnhancedDocument, Dict[str, Any]]]) -> List[str]:
        """문서 추가"""
        added_ids = []
        nodes = []
        
        try:
            for doc in documents:
                if isinstance(doc, EnhancedDocument):
                    text_node = doc.text_node
                    # 임베딩이 없으면 생성
                    if not hasattr(text_node, 'embedding') or text_node.embedding is None:
                        await self._generate_embedding(text_node)
                    nodes.append(text_node)
                    added_ids.append(text_node.id_)
                else:
                    # Dict 형태의 문서 처리
                    node = await self._create_text_node_from_dict(doc)
                    nodes.append(node)
                    added_ids.append(node.id_)
            
            # 노드들을 인덱스에 추가
            if nodes:
                self.index.insert_nodes(nodes)
                logger.info(f"문서 {len(nodes)}개 추가 완료")
            
            return added_ids
            
        except Exception as e:
            logger.error(f"문서 추가 실패: {e}")
            raise
    
    async def _create_text_node_from_dict(self, doc_dict: Dict[str, Any]) -> TextNode:
        """딕셔너리에서 TextNode 생성"""
        node_id = doc_dict.get('id', str(uuid.uuid4()))
        text = doc_dict.get('content', doc_dict.get('text', ''))
        metadata = doc_dict.get('metadata', {})
        
        # 타임스탬프 추가
        metadata['indexed_at'] = datetime.now().isoformat()
        
        node = TextNode(
            text=text,
            metadata=metadata,
            id_=node_id
        )
        
        # 임베딩 생성
        await self._generate_embedding(node)
        
        return node
    
    async def _generate_embedding(self, node: TextNode):
        """노드에 대한 임베딩 생성"""
        try:
            # 임베딩 클라이언트를 통해 생성
            from app.core.clients import EmbeddingClient
            
            embedding_client = EmbeddingClient()
            response = await embedding_client.embed_single({"text": node.text})
            
            if 'embedding' in response:
                node.embedding = response["embedding"]
            else:
                logger.warning(f"임베딩 생성 실패 - 노드 ID: {node.id_}")
                
        except Exception as e:
            logger.error(f"임베딩 생성 중 오류: {e}")
            # 기본 임베딩 설정 (테스트용)
            node.embedding = [0.0] * self.config.vector_size
    
    async def update_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """문서 업데이트"""
        try:
            # 기존 문서 삭제
            await self.delete_document(doc_id)
            
            # 새 문서 추가
            updated_doc = document.copy()
            updated_doc['id'] = doc_id
            added_ids = await self.add_documents([updated_doc])
            
            return len(added_ids) > 0
        except Exception as e:
            logger.error(f"문서 업데이트 실패 ({doc_id}): {e}")
            return False
    
    async def delete_document(self, doc_id: str) -> bool:
        """문서 삭제"""
        try:
            self.index.delete_ref_doc(doc_id, delete_from_docstore=True)
            logger.info(f"문서 삭제 완료: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"문서 삭제 실패 ({doc_id}): {e}")
            return False
    
    async def search(self, query: str, limit: int = 10, filters: Dict[str, Any] = None) -> List[IndexedDocument]:
        """벡터 검색"""
        try:
            # 검색 실행
            nodes_with_scores = self.retriever.retrieve(query)
            
            # 결과 변환
            results = []
            for node_with_score in nodes_with_scores[:limit]:
                node = node_with_score.node
                indexed_doc = IndexedDocument(
                    id=node.id_,
                    content=node.text,
                    metadata=node.metadata,
                    indexed_at=node.metadata.get('indexed_at', '')
                )
                results.append(indexed_doc)
            
            return results
        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}")
            return []
    
    async def search_with_scores(self, query: str, limit: int = 10, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """점수와 함께 벡터 검색"""
        try:
            nodes_with_scores = self.retriever.retrieve(query)
            
            results = []
            for node_with_score in nodes_with_scores[:limit]:
                node = node_with_score.node
                result = {
                    'id': node.id_,
                    'content': node.text,
                    'metadata': node.metadata,
                    'score': node_with_score.score,
                    'source': 'vector'
                }
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"점수별 벡터 검색 실패: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """인덱스 통계 정보"""
        try:
            collection_info = self.client.get_collection(self.config.collection_name)
            
            return {
                "collection_name": self.config.collection_name,
                "total_documents": collection_info.points_count,
                "vector_size": collection_info.config.params.vectors.size,
                "distance_metric": collection_info.config.params.vectors.distance.name,
                "indexed_documents": collection_info.points_count,
                "status": collection_info.status.name
            }
        except Exception as e:
            logger.error(f"통계 정보 조회 실패: {e}")
            return {
                "collection_name": self.config.collection_name,
                "total_documents": 0,
                "error": str(e)
            }
    
    async def similarity_search_with_threshold(
        self, 
        query: str, 
        threshold: float = 0.7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """임계값 기반 유사도 검색"""
        results = await self.search_with_scores(query, limit * 2)  # 여유있게 검색
        
        # 임계값 필터링
        filtered_results = [
            result for result in results 
            if result['score'] >= threshold
        ]
        
        return filtered_results[:limit]
    
    async def get_document_by_id(self, doc_id: str) -> Optional[IndexedDocument]:
        """ID로 문서 조회"""
        try:
            # Qdrant에서 직접 조회
            points = self.client.retrieve(
                collection_name=self.config.collection_name,
                ids=[doc_id]
            )
            
            if not points:
                return None
            
            point = points[0]
            return IndexedDocument(
                id=str(point.id),
                content=point.payload.get('text', ''),
                metadata=point.payload.get('metadata', {}),
                indexed_at=point.payload.get('indexed_at', '')
            )
        except Exception as e:
            logger.error(f"문서 ID 조회 실패 ({doc_id}): {e}")
            return None
    
    async def bulk_delete_by_filter(self, filters: Dict[str, Any]) -> int:
        """필터 조건으로 대량 삭제"""
        try:
            # 필터 조건에 맞는 포인트들 검색
            search_result = self.client.scroll(
                collection_name=self.config.collection_name,
                scroll_filter=self._convert_filters_to_qdrant(filters),
                limit=10000  # 대량 삭제를 위한 높은 limit
            )
            
            if not search_result[0]:
                return 0
            
            # 포인트 ID들 추출
            point_ids = [point.id for point in search_result[0]]
            
            # 대량 삭제 실행
            self.client.delete(
                collection_name=self.config.collection_name,
                points_selector=point_ids
            )
            
            logger.info(f"대량 삭제 완료: {len(point_ids)}개 문서")
            return len(point_ids)
        except Exception as e:
            logger.error(f"대량 삭제 실패: {e}")
            return 0
    
    def _convert_filters_to_qdrant(self, filters: Dict[str, Any]):
        """필터를 Qdrant 형식으로 변환"""
        if not filters:
            return None
        
        try:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            
            return Filter(must=conditions) if conditions else None
        except Exception as e:
            logger.error(f"필터 변환 실패: {e}")
            return None
    
    async def teardown(self):
        """리소스 정리"""
        try:
            if self.client:
                self.client.close()
                logger.info("Vector Index 리소스 정리 완료")
        except Exception as e:
            logger.error(f"리소스 정리 중 오류: {e}") 