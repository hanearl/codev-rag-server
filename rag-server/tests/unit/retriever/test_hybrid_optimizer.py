import pytest
from unittest.mock import Mock, AsyncMock
import numpy as np

from app.retriever.hybrid_optimizer import HybridSearchOptimizer


@pytest.mark.asyncio
class TestHybridSearchOptimizer:
    """하이브리드 검색 최적화 테스트"""
    
    async def test_optimize_weights_with_evaluation_data(self):
        """가중치 최적화 - 평가 데이터 포함"""
        # Given
        retrieval_service = Mock()
        retrieval_service.search_with_detailed_scores = AsyncMock(return_value={
            'results': [
                {'id': 'doc1', 'combined_score': 0.8},
                {'id': 'doc2', 'combined_score': 0.6},
                {'id': 'doc3', 'combined_score': 0.4}
            ]
        })
        
        evaluation_queries = [
            {
                'query': 'test query 1',
                'relevant_docs': ['doc1', 'doc2']
            },
            {
                'query': 'test query 2', 
                'relevant_docs': ['doc2', 'doc3']
            }
        ]
        
        optimizer = HybridSearchOptimizer(retrieval_service)
        
        # When
        result = await optimizer.optimize_weights(
            evaluation_queries,
            weight_range=(0.5, 0.8),
            step=0.1
        )
        
        # Then
        assert 'best_weights' in result
        assert 'best_score' in result
        assert 'all_results' in result
        assert 'optimization_summary' in result
        assert 0.5 <= result['best_weights']['vector_weight'] <= 0.8
        assert 0.2 <= result['best_weights']['bm25_weight'] <= 0.5
    
    async def test_optimize_weights_no_relevant_docs(self):
        """가중치 최적화 - 관련 문서 없는 경우"""
        # Given
        retrieval_service = Mock()
        
        evaluation_queries = [
            {
                'query': 'test query 1',
                'relevant_docs': []  # 관련 문서 없음 
            }
        ]
        
        optimizer = HybridSearchOptimizer(retrieval_service)
        
        # When
        result = await optimizer.optimize_weights(evaluation_queries)
        
        # Then
        assert result['best_weights']['vector_weight'] == 0.7  # 기본값
        assert result['best_weights']['bm25_weight'] == 0.3   # 기본값
        assert result['best_score'] == 0.0
        assert len(result['all_results']) == 0
    
    async def test_optimize_rrf_k_parameter(self):
        """RRF K 파라미터 최적화"""
        # Given
        retrieval_service = Mock()
        retrieval_service.search_with_detailed_scores = AsyncMock(return_value={
            'results': [
                {'id': 'doc1', 'combined_score': 0.8},
                {'id': 'doc2', 'combined_score': 0.6}
            ]
        })
        
        evaluation_queries = [
            {
                'query': 'test query',
                'relevant_docs': ['doc1']
            }
        ]
        
        optimizer = HybridSearchOptimizer(retrieval_service)
        
        # When
        result = await optimizer.optimize_rrf_k(
            evaluation_queries,
            k_range=(20, 80),
            step=20
        )
        
        # Then
        assert 'best_rrf_k' in result
        assert 'best_score' in result
        assert 'all_results' in result
        assert 20 <= result['best_rrf_k'] <= 80
    
    async def test_calculate_ndcg_with_relevant_docs(self):
        """NDCG 계산 - 관련 문서 포함"""
        # Given
        retrieval_service = Mock()
        optimizer = HybridSearchOptimizer(retrieval_service)
        
        search_results = [
            {'id': 'doc1', 'combined_score': 0.9},
            {'id': 'doc2', 'combined_score': 0.8},
            {'id': 'doc3', 'combined_score': 0.7},
            {'id': 'doc4', 'combined_score': 0.6}
        ]
        relevant_docs = ['doc1', 'doc3']
        
        # When
        ndcg = optimizer._calculate_ndcg(search_results, relevant_docs, k=4)
        
        # Then
        assert ndcg is not None
        assert 0.0 <= ndcg <= 1.0
    
    async def test_calculate_ndcg_no_relevant_results(self):
        """NDCG 계산 - 관련 결과 없음"""
        # Given
        retrieval_service = Mock()
        optimizer = HybridSearchOptimizer(retrieval_service)
        
        search_results = [
            {'id': 'doc1', 'combined_score': 0.9},
            {'id': 'doc2', 'combined_score': 0.8}
        ]
        relevant_docs = ['doc3', 'doc4']  # 검색 결과에 없는 문서들
        
        # When
        ndcg = optimizer._calculate_ndcg(search_results, relevant_docs)
        
        # Then
        assert ndcg == 0.0
    
    async def test_calculate_ndcg_empty_inputs(self):
        """NDCG 계산 - 빈 입력"""
        # Given
        retrieval_service = Mock()
        optimizer = HybridSearchOptimizer(retrieval_service)
        
        # When & Then
        assert optimizer._calculate_ndcg([], ['doc1']) is None
        assert optimizer._calculate_ndcg([{'id': 'doc1', 'combined_score': 0.8}], []) is None
    
    def test_get_default_score(self):
        """기본 가중치 점수 조회"""
        # Given
        retrieval_service = Mock()
        optimizer = HybridSearchOptimizer(retrieval_service)
        
        results = [
            {'vector_weight': 0.6, 'bm25_weight': 0.4, 'avg_ndcg': 0.75},
            {'vector_weight': 0.7, 'bm25_weight': 0.3, 'avg_ndcg': 0.80},  # 기본값
            {'vector_weight': 0.8, 'bm25_weight': 0.2, 'avg_ndcg': 0.72}
        ]
        
        # When
        default_score = optimizer._get_default_score(results)
        
        # Then
        assert default_score == 0.80 