# Task 12: Hybrid Retriever 구현

## 📋 작업 개요
Vector Index와 BM25 Index를 결합하여 의미적 검색과 키워드 검색의 장점을 모두 활용하는 Hybrid Retriever를 구현합니다. RRF(Reciprocal Rank Fusion) 및 가중치 기반 결합 전략을 지원합니다.

## 🎯 작업 목표
- LlamaIndex BaseRetriever를 상속한 Hybrid Retriever 구현
- Vector 검색과 BM25 검색 결과의 효과적인 결합
- RRF 및 가중치 기반 스코어링 전략 구현
- 기존 하이브리드 검색 로직과의 호환성 보장

## 🔗 의존성
- **선행 Task**: Task 10 (Vector Index), Task 11 (BM25 Index)
- **활용할 기존 코드**: `app/features/search/retriever.py`, `app/features/search/scorer.py`

## 🔧 구현 사항

### 1. Hybrid Retriever 핵심 구현

```python
# app/retriever/hybrid_retriever.py
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
            # 인덱스들 초기화
            await self.vector_index.setup()
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
        rrf_k: int = None
    ) -> Dict[str, Any]:
        """상세 점수와 함께 검색"""
        await self.setup()
        
        # 임시로 설정 변경
        original_config = {}
        if vector_weight is not None:
            original_config['vector_weight'] = self.hybrid_retriever.vector_weight
            self.hybrid_retriever.vector_weight = vector_weight
        
        if bm25_weight is not None:
            original_config['bm25_weight'] = self.hybrid_retriever.bm25_weight
            self.hybrid_retriever.bm25_weight = bm25_weight
        
        if use_rrf is not None:
            original_config['use_rrf'] = self.hybrid_retriever.use_rrf
            self.hybrid_retriever.use_rrf = use_rrf
        
        if rrf_k is not None:
            original_config['rrf_k'] = self.hybrid_retriever.rrf_k
            self.hybrid_retriever.rrf_k = rrf_k
        
        try:
            start_time = time.time()
            
            # 개별 검색 결과 수집
            vector_results = await self.vector_index.search_with_scores(query, limit=50)
            bm25_results = await self.bm25_index.search_with_scores(query, limit=50)
            
            # 결합 결과 계산
            if self.hybrid_retriever.use_rrf:
                combined_results = self.hybrid_retriever.scoring_strategy.reciprocal_rank_fusion(
                    vector_results, bm25_results, self.hybrid_retriever.rrf_k
                )
            else:
                combined_results = self.hybrid_retriever.scoring_strategy.weighted_average(
                    vector_results, bm25_results,
                    self.hybrid_retriever.vector_weight, self.hybrid_retriever.bm25_weight
                )
            
            end_time = time.time()
            search_time = int((end_time - start_time) * 1000)
            
            return {
                "query": query,
                "results": combined_results[:limit],
                "search_metadata": {
                    "vector_results_count": len(vector_results),
                    "bm25_results_count": len(bm25_results),
                    "combined_results_count": len(combined_results),
                    "search_time_ms": search_time,
                    "scoring_method": "rrf" if self.hybrid_retriever.use_rrf else "weighted",
                    "vector_weight": self.hybrid_retriever.vector_weight,
                    "bm25_weight": self.hybrid_retriever.bm25_weight,
                    "rrf_k": self.hybrid_retriever.rrf_k if self.hybrid_retriever.use_rrf else None
                },
                "individual_results": {
                    "vector": vector_results[:10],
                    "bm25": bm25_results[:10]
                }
            }
            
        finally:
            # 원래 설정 복원
            for key, value in original_config.items():
                setattr(self.hybrid_retriever, key, value)
    
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
```

### 2. 하이브리드 검색 최적화

```python
# app/retriever/hybrid_optimizer.py
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sklearn.metrics import ndcg_score
import logging

logger = logging.getLogger(__name__)

class HybridSearchOptimizer:
    """하이브리드 검색 최적화"""
    
    def __init__(self, retrieval_service):
        self.retrieval_service = retrieval_service
        self.evaluation_data = []
    
    async def optimize_weights(
        self,
        evaluation_queries: List[Dict[str, Any]],
        weight_range: Tuple[float, float] = (0.1, 0.9),
        step: float = 0.1
    ) -> Dict[str, Any]:
        """가중치 최적화"""
        best_weights = None
        best_score = 0.0
        results = []
        
        vector_weights = np.arange(weight_range[0], weight_range[1] + step, step)
        
        for vector_weight in vector_weights:
            bm25_weight = 1.0 - vector_weight
            
            total_ndcg = 0.0
            valid_queries = 0
            
            for query_data in evaluation_queries:
                query = query_data['query']
                relevant_docs = query_data.get('relevant_docs', [])
                
                if not relevant_docs:
                    continue
                
                # 검색 실행
                search_result = await self.retrieval_service.search_with_detailed_scores(
                    query=query,
                    limit=20,
                    vector_weight=vector_weight,
                    bm25_weight=bm25_weight,
                    use_rrf=False
                )
                
                # NDCG 계산
                ndcg = self._calculate_ndcg(
                    search_result['results'], 
                    relevant_docs
                )
                
                if ndcg is not None:
                    total_ndcg += ndcg
                    valid_queries += 1
            
            if valid_queries > 0:
                avg_ndcg = total_ndcg / valid_queries
                results.append({
                    'vector_weight': round(vector_weight, 2),
                    'bm25_weight': round(bm25_weight, 2),
                    'avg_ndcg': round(avg_ndcg, 4),
                    'evaluated_queries': valid_queries
                })
                
                if avg_ndcg > best_score:
                    best_score = avg_ndcg
                    best_weights = (vector_weight, bm25_weight)
        
        return {
            'best_weights': {
                'vector_weight': best_weights[0] if best_weights else 0.7,
                'bm25_weight': best_weights[1] if best_weights else 0.3
            },
            'best_score': best_score,
            'all_results': results,
            'optimization_summary': {
                'total_weight_combinations': len(results),
                'best_combination': best_weights,
                'improvement_from_default': best_score - self._get_default_score(results)
            }
        }
    
    async def optimize_rrf_k(
        self,
        evaluation_queries: List[Dict[str, Any]],
        k_range: Tuple[int, int] = (10, 100),
        step: int = 10
    ) -> Dict[str, Any]:
        """RRF K 파라미터 최적화"""
        best_k = None
        best_score = 0.0
        results = []
        
        k_values = range(k_range[0], k_range[1] + step, step)
        
        for k in k_values:
            total_ndcg = 0.0
            valid_queries = 0
            
            for query_data in evaluation_queries:
                query = query_data['query']
                relevant_docs = query_data.get('relevant_docs', [])
                
                if not relevant_docs:
                    continue
                
                # RRF로 검색 실행
                search_result = await self.retrieval_service.search_with_detailed_scores(
                    query=query,
                    limit=20,
                    use_rrf=True,
                    rrf_k=k
                )
                
                # NDCG 계산
                ndcg = self._calculate_ndcg(
                    search_result['results'],
                    relevant_docs
                )
                
                if ndcg is not None:
                    total_ndcg += ndcg
                    valid_queries += 1
            
            if valid_queries > 0:
                avg_ndcg = total_ndcg / valid_queries
                results.append({
                    'rrf_k': k,
                    'avg_ndcg': round(avg_ndcg, 4),
                    'evaluated_queries': valid_queries
                })
                
                if avg_ndcg > best_score:
                    best_score = avg_ndcg
                    best_k = k
        
        return {
            'best_rrf_k': best_k or 60,
            'best_score': best_score,
            'all_results': results
        }
    
    def _calculate_ndcg(
        self, 
        search_results: List[Dict[str, Any]], 
        relevant_docs: List[str],
        k: int = 10
    ) -> Optional[float]:
        """NDCG 점수 계산"""
        if not search_results or not relevant_docs:
            return None
        
        # 검색 결과의 관련성 점수 생성
        relevance_scores = []
        for result in search_results[:k]:
            doc_id = result['id']
            if doc_id in relevant_docs:
                # 관련 문서면 1, 아니면 0
                relevance_scores.append(1)
            else:
                relevance_scores.append(0)
        
        if sum(relevance_scores) == 0:
            return 0.0
        
        # NDCG 계산
        try:
            # sklearn의 ndcg_score는 2D 배열을 요구
            y_true = np.array([relevance_scores])
            y_score = np.array([[result['combined_score'] for result in search_results[:k]]])
            
            return ndcg_score(y_true, y_score, k=k)
        except Exception as e:
            logger.warning(f"NDCG 계산 실패: {e}")
            return None
    
    def _get_default_score(self, results: List[Dict[str, Any]]) -> float:
        """기본 가중치(0.7, 0.3)의 점수 찾기"""
        for result in results:
            if (abs(result['vector_weight'] - 0.7) < 0.01 and 
                abs(result['bm25_weight'] - 0.3) < 0.01):
                return result['avg_ndcg']
        return 0.0
```

## ✅ 완료 조건

1. **Hybrid Retriever 구현**: LlamaIndex BaseRetriever 기반으로 완전히 구현됨
2. **스코어링 전략**: RRF와 가중평균 두 가지 방법 모두 지원됨
3. **병렬 검색**: Vector와 BM25 검색이 병렬로 실행됨
4. **결과 결합**: 두 검색 결과가 효과적으로 결합됨
5. **성능 최적화**: 대용량 검색 시 성능이 양호함
6. **파라미터 조정**: 가중치와 RRF K값 최적화 지원됨
7. **평가 시스템**: 검색 품질 평가 도구 제공됨

## 📋 다음 Task와의 연관관계

- **Task 13**: LangChain PromptTemplate에서 검색 결과 활용
- **Task 15**: HybridRAG 서비스에서 이 Retriever를 핵심 구성요소로 사용

## 🧪 테스트 계획

```python
# tests/unit/retriever/test_hybrid_retriever.py
async def test_hybrid_retriever_setup():
    """Hybrid Retriever 설정 테스트"""
    service = HybridRetrievalService(vector_index, bm25_index)
    await service.setup()
    assert service._initialized is True

async def test_parallel_search():
    """병렬 검색 테스트"""
    retriever = CodeHybridRetriever(vector_index, bm25_index)
    vector_results, bm25_results = await retriever._parallel_search("authentication")
    assert isinstance(vector_results, list)
    assert isinstance(bm25_results, list)

async def test_weighted_scoring():
    """가중평균 스코어링 테스트"""
    vector_results = [{'id': '1', 'score': 0.8, 'content': 'test', 'metadata': {}}]
    bm25_results = [{'id': '1', 'score': 0.6, 'content': 'test', 'metadata': {}}]
    
    combined = HybridScoringStrategy.weighted_average(
        vector_results, bm25_results, 0.7, 0.3
    )
    
    assert len(combined) == 1
    assert combined[0]['combined_score'] == 0.8 * 0.7 + 0.6 * 0.3

async def test_rrf_scoring():
    """RRF 스코어링 테스트"""
    vector_results = [{'id': '1', 'score': 0.8, 'content': 'test', 'metadata': {}}]
    bm25_results = [{'id': '1', 'score': 0.6, 'content': 'test', 'metadata': {}}]
    
    combined = HybridScoringStrategy.reciprocal_rank_fusion(
        vector_results, bm25_results, k=60
    )
    
    assert len(combined) == 1
    assert 'rrf_score' in combined[0]
```

이 Task는 Vector와 BM25 검색의 장점을 결합하여 최고 품질의 검색 결과를 제공하는 핵심 구성요소입니다. 정교한 스코어링 전략을 통해 의미적 검색과 키워드 검색의 시너지를 극대화합니다. 