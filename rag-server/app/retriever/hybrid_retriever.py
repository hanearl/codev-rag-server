from typing import List, Dict, Any, Optional, Union
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.core import Document
import asyncio
import time
import logging
from .base_retriever import BaseRetriever as BaseRetrieverInterface, RetrievalResult
from app.index.vector_index import CodeVectorIndex
from app.index.bm25_index import CodeBM25Index

logger = logging.getLogger(__name__)


class HybridScoringStrategy:
    """하이브리드 스코어링 전략"""
    
    @staticmethod
    def weighted_average(
        vector_results: List[Dict[str, Any]], 
        bm25_results: List[Dict[str, Any]],
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """가중평균 기반 스코어링"""
        # 결과를 ID별로 그룹화
        results_map = {}
        
        # Vector 결과 처리
        for result in vector_results:
            doc_id = result['id']
            results_map[doc_id] = {
                **result,
                'vector_score': result['score'],
                'bm25_score': 0.0,
                'combined_score': result['score'] * vector_weight,
                'sources': ['vector']
            }
        
        # BM25 결과 처리
        for result in bm25_results:
            doc_id = result['id']
            if doc_id in results_map:
                # 기존 결과에 BM25 점수 추가
                results_map[doc_id]['bm25_score'] = result['score']
                results_map[doc_id]['combined_score'] += result['score'] * bm25_weight
                results_map[doc_id]['sources'].append('bm25')
            else:
                # 새로운 BM25 결과
                results_map[doc_id] = {
                    **result,
                    'vector_score': 0.0,
                    'bm25_score': result['score'],
                    'combined_score': result['score'] * bm25_weight,
                    'sources': ['bm25']
                }
        
        # 점수별 정렬
        combined_results = list(results_map.values())
        combined_results.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return combined_results
    
    @staticmethod
    def reciprocal_rank_fusion(
        vector_results: List[Dict[str, Any]], 
        bm25_results: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """RRF (Reciprocal Rank Fusion) 기반 스코어링"""
        results_map = {}
        
        # Vector 결과의 순위 기반 점수
        for rank, result in enumerate(vector_results):
            doc_id = result['id']
            rrf_score = 1.0 / (k + rank + 1)
            
            results_map[doc_id] = {
                **result,
                'vector_score': result['score'],
                'vector_rank': rank + 1,
                'bm25_score': 0.0,
                'bm25_rank': None,
                'rrf_score': rrf_score,
                'sources': ['vector']
            }
        
        # BM25 결과의 순위 기반 점수 추가
        for rank, result in enumerate(bm25_results):
            doc_id = result['id']
            rrf_score = 1.0 / (k + rank + 1)
            
            if doc_id in results_map:
                # 기존 결과에 BM25 RRF 점수 추가
                results_map[doc_id]['bm25_score'] = result['score']
                results_map[doc_id]['bm25_rank'] = rank + 1
                results_map[doc_id]['rrf_score'] += rrf_score
                results_map[doc_id]['sources'].append('bm25')
            else:
                # 새로운 BM25 결과
                results_map[doc_id] = {
                    **result,
                    'vector_score': 0.0,
                    'vector_rank': None,
                    'bm25_score': result['score'],
                    'bm25_rank': rank + 1,
                    'rrf_score': rrf_score,
                    'sources': ['bm25']
                }
        
        # RRF 점수로 정렬
        combined_results = list(results_map.values())
        combined_results.sort(key=lambda x: x['rrf_score'], reverse=True)
        
        # combined_score를 rrf_score로 설정
        for result in combined_results:
            result['combined_score'] = result['rrf_score']
        
        return combined_results


class CodeHybridRetriever(BaseRetriever):
    """코드 하이브리드 리트리버"""
    
    def __init__(
        self,
        vector_index: CodeVectorIndex,
        bm25_index: CodeBM25Index,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        use_rrf: bool = True,
        rrf_k: int = 60,
        max_results: int = 50,
        enable_filtering: bool = True
    ):
        super().__init__()
        self.vector_index = vector_index
        self.bm25_index = bm25_index
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.use_rrf = use_rrf
        self.rrf_k = rrf_k
        self.max_results = max_results
        self.enable_filtering = enable_filtering
        self.scoring_strategy = HybridScoringStrategy()
    
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """하이브리드 검색 실행"""
        query = query_bundle.query_str
        
        # 병렬로 Vector와 BM25 검색 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            vector_results, bm25_results = loop.run_until_complete(
                self._parallel_search(query)
            )
        finally:
            loop.close()
        
        # 결과 결합
        if self.use_rrf:
            combined_results = self.scoring_strategy.reciprocal_rank_fusion(
                vector_results, bm25_results, self.rrf_k
            )
        else:
            combined_results = self.scoring_strategy.weighted_average(
                vector_results, bm25_results, 
                self.vector_weight, self.bm25_weight
            )
        
        # NodeWithScore 객체로 변환
        nodes_with_scores = []
        for result in combined_results[:self.max_results]:
            node = TextNode(
                text=result['content'],
                metadata=result['metadata'],
                id_=result['id']
            )
            
            node_with_score = NodeWithScore(
                node=node,
                score=result['combined_score']
            )
            nodes_with_scores.append(node_with_score)
        
        return nodes_with_scores
    
    async def _parallel_search(self, query: str) -> tuple:
        """병렬 검색 실행"""
        # Vector와 BM25 검색을 병렬로 실행
        vector_task = self.vector_index.search_with_scores(
            query, limit=self.max_results
        )
        bm25_task = self.bm25_index.search_with_scores(
            query, limit=self.max_results
        )
        
        vector_results, bm25_results = await asyncio.gather(
            vector_task, bm25_task, return_exceptions=True
        )
        
        # 예외 처리
        if isinstance(vector_results, Exception):
            logger.error(f"Vector 검색 실패: {vector_results}")
            vector_results = []
        
        if isinstance(bm25_results, Exception):
            logger.error(f"BM25 검색 실패: {bm25_results}")
            bm25_results = []
        
        return vector_results, bm25_results


class HybridRetrievalService(BaseRetrieverInterface):
    """하이브리드 검색 서비스"""
    
    def __init__(
        self,
        vector_index: CodeVectorIndex,
        bm25_index: CodeBM25Index,
        config: Optional[Dict[str, Any]] = None
    ):
        self.vector_index = vector_index
        self.bm25_index = bm25_index
        self.config = config or {}
        self.hybrid_retriever = None
        self._initialized = False
    
    async def setup(self) -> None:
        """리트리버 초기화"""
        if not self._initialized:
            # 인덱스들 초기화 (setup 메서드가 있는 경우에만)
            if hasattr(self.vector_index, 'setup'):
                await self.vector_index.setup()
            if hasattr(self.bm25_index, 'setup'):
                await self.bm25_index.setup()
            
            # 하이브리드 리트리버 생성
            self.hybrid_retriever = CodeHybridRetriever(
                vector_index=self.vector_index,
                bm25_index=self.bm25_index,
                vector_weight=self.config.get('vector_weight', 0.7),
                bm25_weight=self.config.get('bm25_weight', 0.3),
                use_rrf=self.config.get('use_rrf', True),
                rrf_k=self.config.get('rrf_k', 60),
                max_results=self.config.get('max_results', 50)
            )
            
            self._initialized = True
            logger.info("하이브리드 검색 서비스 초기화 완료")
    
    async def retrieve(
        self, 
        query: str, 
        limit: int = 10,
        **kwargs
    ) -> List[RetrievalResult]:
        """하이브리드 검색 실행"""
        await self.setup()
        
        start_time = time.time()
        
        try:
            # QueryBundle 생성
            query_bundle = QueryBundle(query_str=query)
            
            # 검색 실행
            nodes_with_scores = self.hybrid_retriever._retrieve(query_bundle)
            
            # RetrievalResult로 변환
            results = []
            for node_with_score in nodes_with_scores[:limit]:
                node = node_with_score.node
                result = RetrievalResult(
                    id=node.id_,
                    content=node.text,
                    metadata=node.metadata,
                    score=node_with_score.score,
                    source="hybrid"
                )
                results.append(result)
            
            end_time = time.time()
            search_time = int((end_time - start_time) * 1000)
            
            logger.info(f"하이브리드 검색 완료: {len(results)}개 결과, {search_time}ms")
            
            return results
            
        except Exception as e:
            logger.error(f"하이브리드 검색 실패: {e}")
            return []
    
    async def search_with_detailed_scores(
        self,
        query: str,
        limit: int = 10,
        vector_weight: float = None,
        bm25_weight: float = None,
        use_rrf: bool = None,
        rrf_k: int = None,
        collection_name: str = None,
        index_name: str = None
    ) -> Dict[str, Any]:
        """상세 점수와 함께 검색"""
        await self.setup()
        
        try:
            start_time = time.time()
            
            # 개별 검색 결과 수집 - 실제 서비스 메서드 사용
            vector_results = await self.vector_index.search_similar_code(
                query=query,
                limit=50,
                threshold=0.0,
                collection_name=collection_name
            )
            
            bm25_results = await self.bm25_index.search_keywords(
                query=query,
                collection_name=index_name or collection_name,
                limit=50
            )
            
            # 결과를 표준 형식으로 변환
            vector_formatted = [
                {
                    "id": result.get("id", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0.0),
                    "metadata": result.get("metadata", {})
                }
                for result in vector_results
            ]
            
            bm25_formatted = [
                {
                    "id": result.get("id", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0.0),
                    "metadata": result.get("metadata", {})
                }
                for result in bm25_results
            ]
            
            # 결합 결과 계산
            scoring_strategy = HybridScoringStrategy()
            
            if use_rrf if use_rrf is not None else True:
                combined_results = scoring_strategy.reciprocal_rank_fusion(
                    vector_formatted, bm25_formatted, rrf_k or 60
                )
            else:
                combined_results = scoring_strategy.weighted_average(
                    vector_formatted, bm25_formatted,
                    vector_weight or 0.7, bm25_weight or 0.3
                )
            
            end_time = time.time()
            search_time = int((end_time - start_time) * 1000)
            
            return {
                "query": query,
                "results": combined_results[:limit],
                "vector_results_count": len(vector_formatted),
                "bm25_results_count": len(bm25_formatted),
                "search_time_ms": search_time,
                "fusion_method": "rrf" if (use_rrf if use_rrf is not None else True) else "weighted",
                "weights_used": {
                    "vector_weight": vector_weight or 0.7,
                    "bm25_weight": bm25_weight or 0.3
                }
            }
            
        except Exception as e:
            logger.error(f"하이브리드 검색 실패: {e}")
            return {
                "query": query,
                "results": [],
                "vector_results_count": 0,
                "bm25_results_count": 0,
                "search_time_ms": 0,
                "fusion_method": "error",
                "weights_used": {},
                "error": str(e)
            }
    
    async def compare_scoring_methods(
        self,
        query: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """스코어링 방법 비교"""
        await self.setup()
        
        # Vector와 BM25 개별 결과
        vector_results = await self.vector_index.search_with_scores(query, limit=50)
        bm25_results = await self.bm25_index.search_with_scores(query, limit=50)
        
        # 가중평균 결과
        weighted_results = self.hybrid_retriever.scoring_strategy.weighted_average(
            vector_results, bm25_results, 0.7, 0.3
        )
        
        # RRF 결과
        rrf_results = self.hybrid_retriever.scoring_strategy.reciprocal_rank_fusion(
            vector_results, bm25_results, 60
        )
        
        return {
            "query": query,
            "comparison": {
                "vector_only": vector_results[:limit],
                "bm25_only": bm25_results[:limit],
                "weighted_fusion": weighted_results[:limit],
                "rrf_fusion": rrf_results[:limit]
            },
            "statistics": {
                "vector_unique": len(set(r['id'] for r in vector_results)),
                "bm25_unique": len(set(r['id'] for r in bm25_results)),
                "overlap": len(set(r['id'] for r in vector_results) & 
                             set(r['id'] for r in bm25_results))
            }
        }
    
    async def teardown(self) -> None:
        """리소스 정리"""
        if self.vector_index:
            await self.vector_index.teardown()
        if self.bm25_index:
            # BM25 index는 특별한 정리가 필요 없을 수 있음
            pass 