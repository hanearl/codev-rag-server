from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)

# sklearn이 설치되어 있지 않을 경우를 대비한 fallback
try:
    from sklearn.metrics import ndcg_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("sklearn을 사용할 수 없습니다. NDCG 계산이 제한될 수 있습니다.")


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
            if SKLEARN_AVAILABLE:
                # sklearn의 ndcg_score 사용
                y_true = np.array([relevance_scores])
                y_score = np.array([[result['combined_score'] for result in search_results[:k]]])
                
                return ndcg_score(y_true, y_score, k=k)
            else:
                # 간단한 DCG 기반 계산 (fallback)
                return self._calculate_dcg_fallback(relevance_scores, k)
                
        except Exception as e:
            logger.warning(f"NDCG 계산 실패: {e}")
            return None
    
    def _calculate_dcg_fallback(self, relevance_scores: List[int], k: int) -> float:
        """sklearn 없이 DCG 기반 간단한 계산"""
        dcg = 0.0
        for i, rel in enumerate(relevance_scores[:k]):
            if rel > 0:
                dcg += rel / np.log2(i + 2)
        
        # Ideal DCG 계산 (relevance_scores를 내림차순 정렬)
        ideal_relevance = sorted(relevance_scores, reverse=True)
        idcg = 0.0
        for i, rel in enumerate(ideal_relevance[:k]):
            if rel > 0:
                idcg += rel / np.log2(i + 2)
        
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    def _get_default_score(self, results: List[Dict[str, Any]]) -> float:
        """기본 가중치(0.7, 0.3)의 점수 찾기"""
        for result in results:
            if (abs(result['vector_weight'] - 0.7) < 0.01 and 
                abs(result['bm25_weight'] - 0.3) < 0.01):
                return result['avg_ndcg']
        return 0.0
    
    async def evaluate_hybrid_performance(
        self,
        evaluation_queries: List[Dict[str, Any]],
        configurations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """다양한 설정으로 하이브리드 성능 평가"""
        evaluation_results = []
        
        for config in configurations:
            config_name = config.get('name', f"config_{len(evaluation_results)}")
            total_precision = 0.0
            total_recall = 0.0
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
                    limit=config.get('limit', 10),
                    vector_weight=config.get('vector_weight'),
                    bm25_weight=config.get('bm25_weight'),
                    use_rrf=config.get('use_rrf', True),
                    rrf_k=config.get('rrf_k', 60)
                )
                
                results = search_result['results']
                
                # Precision, Recall, NDCG 계산
                precision = self._calculate_precision(results, relevant_docs)
                recall = self._calculate_recall(results, relevant_docs)
                ndcg = self._calculate_ndcg(results, relevant_docs)
                
                if precision is not None and recall is not None and ndcg is not None:
                    total_precision += precision
                    total_recall += recall
                    total_ndcg += ndcg
                    valid_queries += 1
            
            if valid_queries > 0:
                avg_metrics = {
                    'precision': round(total_precision / valid_queries, 4),
                    'recall': round(total_recall / valid_queries, 4),
                    'ndcg': round(total_ndcg / valid_queries, 4),
                    'f1_score': 0.0
                }
                
                # F1 Score 계산
                if avg_metrics['precision'] + avg_metrics['recall'] > 0:
                    avg_metrics['f1_score'] = round(
                        2 * avg_metrics['precision'] * avg_metrics['recall'] / 
                        (avg_metrics['precision'] + avg_metrics['recall']), 4
                    )
                
                evaluation_results.append({
                    'configuration': config,
                    'metrics': avg_metrics,
                    'evaluated_queries': valid_queries
                })
        
        return {
            'evaluations': evaluation_results,
            'best_configuration': max(evaluation_results, key=lambda x: x['metrics']['ndcg'])
            if evaluation_results else None
        }
    
    def _calculate_precision(
        self, 
        search_results: List[Dict[str, Any]], 
        relevant_docs: List[str]
    ) -> Optional[float]:
        """Precision 계산"""
        if not search_results:
            return None
        
        relevant_retrieved = sum(
            1 for result in search_results 
            if result['id'] in relevant_docs
        )
        
        return relevant_retrieved / len(search_results)
    
    def _calculate_recall(
        self, 
        search_results: List[Dict[str, Any]], 
        relevant_docs: List[str]
    ) -> Optional[float]:
        """Recall 계산"""
        if not relevant_docs:
            return None
        
        relevant_retrieved = sum(
            1 for result in search_results 
            if result['id'] in relevant_docs
        )
        
        return relevant_retrieved / len(relevant_docs) 