# Task 10: Vector Index 구현

## 📋 작업 개요
LlamaIndex VectorStoreIndex를 활용하여 코드 문서의 임베딩 기반 검색을 지원하는 Vector Index를 구현합니다. 기존 벡터 DB 연동을 LlamaIndex 아키텍처로 통합합니다.

## 🎯 작업 목표
- LlamaIndex VectorStoreIndex 기반 벡터 검색 시스템 구축
- Qdrant Vector Store 연동 및 최적화
- 기존 벡터 DB 데이터와의 호환성 보장
- 벡터 검색 성능 최적화

## 🔗 의존성
- **선행 Task**: Task 9 (Document Builder 구현)
- **활용할 기존 코드**: `app/core/clients.py`의 VectorClient
- **외부 의존성**: Qdrant Vector Database

## 🔧 구현 사항

### 1. Vector Index 인터페이스 구현

```python
# app/index/vector_index.py
from typing import List, Dict, Any, Optional, Union
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.schema import TextNode, NodeWithScore
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
from .base_index import BaseIndex, IndexedDocument
from app.retriever.document_builder import EnhancedDocument
from app.core.config import settings

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
        self.qdrant_url = qdrant_url or settings.VECTOR_DB_URL
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
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"컬렉션 목록 조회 실패: {e}")
            return []
    
    async def _create_collection(self):
        """컬렉션 생성"""
        self.client.create_collection(
            collection_name=self.config.collection_name,
            vectors_config=VectorParams(
                size=self.config.vector_size,
                distance=self.config.distance
            )
        )
    
    async def add_documents(self, documents: List[Union[EnhancedDocument, Dict[str, Any]]]) -> List[str]:
        """문서 추가"""
        added_ids = []
        nodes = []
        
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
        
        return added_ids
    
    async def _create_text_node_from_dict(self, doc_dict: Dict[str, Any]) -> TextNode:
        """딕셔너리에서 TextNode 생성"""
        node_id = doc_dict.get('id', str(uuid.uuid4()))
        text = doc_dict.get('content', doc_dict.get('text', ''))
        metadata = doc_dict.get('metadata', {})
        
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
        # 임베딩 클라이언트를 통해 생성
        from app.core.clients import EmbeddingClient
        
        embedding_client = EmbeddingClient()
        response = await embedding_client.embed({"text": node.text})
        node.embedding = response["embedding"]
    
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
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"문서 업데이트 실패 ({doc_id}): {e}")
            return False
    
    async def delete_document(self, doc_id: str) -> bool:
        """문서 삭제"""
        try:
            self.index.delete_ref_doc(doc_id, delete_from_docstore=True)
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
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
            import logging
            logger = logging.getLogger(__name__)
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
            import logging
            logger = logging.getLogger(__name__)
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
            import logging
            logger = logging.getLogger(__name__)
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
            import logging
            logger = logging.getLogger(__name__)
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
            
            return len(point_ids)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"대량 삭제 실패: {e}")
            return 0
    
    def _convert_filters_to_qdrant(self, filters: Dict[str, Any]):
        """필터를 Qdrant 형식으로 변환"""
        # 간단한 구현 - 실제로는 더 복잡한 필터 변환 로직 필요
        if not filters:
            return None
        
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        conditions = []
        for key, value in filters.items():
            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                )
            )
        
        return Filter(must=conditions) if conditions else None
    
    async def teardown(self):
        """리소스 정리"""
        if self.client:
            self.client.close()
```

### 2. Vector Index 서비스

```python
# app/index/vector_service.py
from typing import List, Dict, Any, Optional
from .vector_index import CodeVectorIndex, VectorIndexConfig
from app.retriever.document_builder import EnhancedDocument
import logging

logger = logging.getLogger(__name__)

class VectorIndexService:
    """Vector Index 서비스"""
    
    def __init__(self, config: VectorIndexConfig = None):
        self.config = config or VectorIndexConfig()
        self.index = CodeVectorIndex(self.config)
        self._initialized = False
    
    async def initialize(self):
        """서비스 초기화"""
        if not self._initialized:
            await self.index.setup()
            self._initialized = True
            logger.info(f"Vector Index 서비스 초기화 완료: {self.config.collection_name}")
    
    async def index_documents(self, documents: List[EnhancedDocument]) -> Dict[str, Any]:
        """문서들 인덱싱"""
        await self.initialize()
        
        try:
            added_ids = await self.index.add_documents(documents)
            
            return {
                "success": True,
                "indexed_count": len(added_ids),
                "document_ids": added_ids,
                "collection": self.config.collection_name
            }
        except Exception as e:
            logger.error(f"문서 인덱싱 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "indexed_count": 0
            }
    
    async def search_similar_code(
        self, 
        query: str, 
        limit: int = 10,
        threshold: float = 0.0,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """유사 코드 검색"""
        await self.initialize()
        
        if threshold > 0:
            return await self.index.similarity_search_with_threshold(
                query, threshold, limit
            )
        else:
            return await self.index.search_with_scores(
                query, limit, filters
            )
    
    async def update_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """문서 업데이트"""
        await self.initialize()
        return await self.index.update_document(doc_id, document)
    
    async def delete_document(self, doc_id: str) -> bool:
        """문서 삭제"""
        await self.initialize()
        return await self.index.delete_document(doc_id)
    
    async def delete_by_file_path(self, file_path: str) -> int:
        """파일 경로로 문서 삭제"""
        await self.initialize()
        
        filters = {"file_path": file_path}
        return await self.index.bulk_delete_by_filter(filters)
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계"""
        await self.initialize()
        return await self.index.get_stats()
    
    async def health_check(self) -> Dict[str, Any]:
        """헬스 체크"""
        try:
            await self.initialize()
            stats = await self.get_collection_stats()
            
            return {
                "status": "healthy",
                "collection": self.config.collection_name,
                "document_count": stats.get("total_documents", 0),
                "vector_size": stats.get("vector_size", 0)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
```

## ✅ 완료 조건

1. **Vector Index 구현**: LlamaIndex VectorStoreIndex 기반으로 완전히 구현됨
2. **Qdrant 연동**: Qdrant Vector Store와 안정적으로 연동됨
3. **문서 관리**: 추가, 업데이트, 삭제가 정상 동작함
4. **검색 기능**: 다양한 검색 옵션(임계값, 필터 등)이 지원됨
5. **성능 최적화**: 대용량 문서 처리 시 성능이 양호함
6. **에러 처리**: 모든 예외 상황이 적절히 처리됨
7. **기존 호환성**: 기존 벡터 DB 데이터와 호환됨

## 📋 다음 Task와의 연관관계

- **Task 11**: BM25 Index와 함께 하이브리드 검색 구성
- **Task 12**: Hybrid Retriever에서 벡터 검색 결과 활용
- **Task 15**: HybridRAG 서비스에서 Vector Index 활용

## 🧪 테스트 계획

```python
# tests/unit/index/test_vector_index.py
async def test_vector_index_setup():
    """Vector Index 설정 테스트"""
    index = CodeVectorIndex()
    await index.setup()
    assert index.client is not None
    assert index.vector_store is not None

async def test_add_documents():
    """문서 추가 테스트"""
    index = CodeVectorIndex()
    await index.setup()
    
    docs = [create_sample_enhanced_document()]
    added_ids = await index.add_documents(docs)
    assert len(added_ids) == 1

async def test_vector_search():
    """벡터 검색 테스트"""
    service = VectorIndexService()
    results = await service.search_similar_code("JWT authentication", limit=5)
    assert isinstance(results, list)

async def test_search_with_threshold():
    """임계값 검색 테스트"""
    index = CodeVectorIndex()
    await index.setup()
    
    results = await index.similarity_search_with_threshold(
        "user authentication", threshold=0.7
    )
    for result in results:
        assert result['score'] >= 0.7
```

이 Task는 하이브리드 검색 시스템의 핵심 구성요소인 벡터 검색을 담당합니다. 높은 품질의 임베딩 기반 검색을 통해 의미적으로 유사한 코드를 정확하게 찾을 수 있습니다. 