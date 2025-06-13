import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import List, Dict, Any

from app.retriever.hybrid_retriever import (
    HybridScoringStrategy, 
    CodeHybridRetriever, 
    HybridRetrievalService
)
from app.index.vector_index import CodeVectorIndex
from app.index.bm25_index import CodeBM25Index
from app.retriever.base_retriever import RetrievalResult


class TestHybridScoringStrategy:
    """하이브리드 스코어링 전략 테스트"""
    
    def test_weighted_average_scoring_with_overlap(self):
        """가중평균 스코어링 - 중복 문서 테스트"""
        # Given
        vector_results = [
            {'id': 'doc1', 'score': 0.8, 'content': 'test content 1', 'metadata': {}},
            {'id': 'doc2', 'score': 0.6, 'content': 'test content 2', 'metadata': {}}
        ]
        bm25_results = [
            {'id': 'doc1', 'score': 0.7, 'content': 'test content 1', 'metadata': {}},
            {'id': 'doc3', 'score': 0.9, 'content': 'test content 3', 'metadata': {}}
        ]
        
        # When
        combined = HybridScoringStrategy.weighted_average(
            vector_results, bm25_results, 0.7, 0.3
        )
        
        # Then
        assert len(combined) == 3
        assert combined[0]['id'] == 'doc1'  # 가장 높은 점수
        assert combined[0]['combined_score'] == 0.8 * 0.7 + 0.7 * 0.3
        assert combined[0]['sources'] == ['vector', 'bm25']
        assert combined[1]['id'] == 'doc2'  # Vector만 있는 문서 (두 번째 높은 점수)
        assert combined[1]['sources'] == ['vector']
        assert combined[2]['id'] == 'doc3'  # BM25만 있는 문서 (가장 낮은 점수)
        assert combined[2]['sources'] == ['bm25']
    
    def test_weighted_average_scoring_no_overlap(self):
        """가중평균 스코어링 - 중복 없는 경우"""
        # Given
        vector_results = [
            {'id': 'doc1', 'score': 0.8, 'content': 'test1', 'metadata': {}}
        ]
        bm25_results = [
            {'id': 'doc2', 'score': 0.9, 'content': 'test2', 'metadata': {}}
        ]
        
        # When
        combined = HybridScoringStrategy.weighted_average(
            vector_results, bm25_results, 0.7, 0.3
        )
        
        # Then
        assert len(combined) == 2
        assert combined[0]['id'] == 'doc1'  # 0.8 * 0.7 = 0.56
        assert combined[1]['id'] == 'doc2'  # 0.9 * 0.3 = 0.27
    
    def test_rrf_scoring_with_overlap(self):
        """RRF 스코어링 - 중복 문서 테스트"""
        # Given
        vector_results = [
            {'id': 'doc1', 'score': 0.8, 'content': 'test1', 'metadata': {}},
            {'id': 'doc2', 'score': 0.6, 'content': 'test2', 'metadata': {}}
        ]
        bm25_results = [
            {'id': 'doc1', 'score': 0.7, 'content': 'test1', 'metadata': {}},
            {'id': 'doc3', 'score': 0.9, 'content': 'test3', 'metadata': {}}
        ]
        
        # When
        combined = HybridScoringStrategy.reciprocal_rank_fusion(
            vector_results, bm25_results, k=60
        )
        
        # Then
        assert len(combined) == 3
        assert combined[0]['id'] == 'doc1'  # 두 소스 모두에서 높은 순위
        assert combined[0]['vector_rank'] == 1
        assert combined[0]['bm25_rank'] == 1
        assert 'rrf_score' in combined[0]
        assert combined[0]['combined_score'] == combined[0]['rrf_score']
    
    def test_rrf_scoring_k_parameter(self):
        """RRF 스코어링 - K 파라미터 테스트"""
        # Given
        vector_results = [
            {'id': 'doc1', 'score': 0.8, 'content': 'test1', 'metadata': {}}
        ]
        bm25_results = [
            {'id': 'doc1', 'score': 0.7, 'content': 'test1', 'metadata': {}}
        ]
        
        # When
        combined_k60 = HybridScoringStrategy.reciprocal_rank_fusion(
            vector_results, bm25_results, k=60
        )
        combined_k10 = HybridScoringStrategy.reciprocal_rank_fusion(
            vector_results, bm25_results, k=10
        )
        
        # Then
        assert combined_k10[0]['rrf_score'] > combined_k60[0]['rrf_score']


@pytest.mark.asyncio
class TestCodeHybridRetriever:
    """코드 하이브리드 리트리버 테스트"""
    
    async def test_parallel_search_success(self):
        """병렬 검색 성공 테스트"""
        # Given
        vector_index = Mock()
        vector_index.search_with_scores = AsyncMock(return_value=[
            {'id': 'doc1', 'score': 0.8, 'content': 'test1', 'metadata': {}}
        ])
        
        bm25_index = Mock()
        bm25_index.search_with_scores = AsyncMock(return_value=[
            {'id': 'doc2', 'score': 0.9, 'content': 'test2', 'metadata': {}}
        ])
        
        retriever = CodeHybridRetriever(vector_index, bm25_index)
        
        # When
        vector_results, bm25_results = await retriever._parallel_search("test query")
        
        # Then
        assert len(vector_results) == 1
        assert len(bm25_results) == 1
        assert vector_results[0]['id'] == 'doc1'
        assert bm25_results[0]['id'] == 'doc2'
    
    async def test_parallel_search_with_exception(self):
        """병렬 검색 중 예외 발생 테스트"""
        # Given
        vector_index = Mock()
        vector_index.search_with_scores = AsyncMock(side_effect=Exception("Vector search failed"))
        
        bm25_index = Mock()
        bm25_index.search_with_scores = AsyncMock(return_value=[
            {'id': 'doc1', 'score': 0.8, 'content': 'test1', 'metadata': {}}
        ])
        
        retriever = CodeHybridRetriever(vector_index, bm25_index)
        
        # When
        vector_results, bm25_results = await retriever._parallel_search("test query")
        
        # Then
        assert vector_results == []  # 예외 발생 시 빈 리스트
        assert len(bm25_results) == 1


@pytest.mark.asyncio 
class TestHybridRetrievalService:
    """하이브리드 검색 서비스 테스트"""
    
    async def test_service_setup(self):
        """서비스 초기화 테스트"""
        # Given
        vector_index = Mock()
        vector_index.setup = AsyncMock()
        
        bm25_index = Mock()
        bm25_index.setup = AsyncMock()
        
        service = HybridRetrievalService(vector_index, bm25_index)
        
        # When
        await service.setup()
        
        # Then
        assert service._initialized is True
        assert service.hybrid_retriever is not None
        vector_index.setup.assert_called_once()
        bm25_index.setup.assert_called_once()
    
    async def test_retrieve_with_results(self):
        """검색 결과 반환 테스트"""
        # Given
        vector_index = Mock()
        vector_index.setup = AsyncMock()
        vector_index.search_with_scores = AsyncMock(return_value=[
            {'id': 'doc1', 'score': 0.8, 'content': 'test content 1', 'metadata': {'type': 'code'}}
        ])
        
        bm25_index = Mock()
        bm25_index.setup = AsyncMock()
        bm25_index.search_with_scores = AsyncMock(return_value=[
            {'id': 'doc2', 'score': 0.9, 'content': 'test content 2', 'metadata': {'type': 'doc'}}
        ])
        
        service = HybridRetrievalService(vector_index, bm25_index)
        
        # When
        results = await service.retrieve("test query", limit=5)
        
        # Then
        assert isinstance(results, list)
        assert len(results) <= 5
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert all(r.source == "hybrid" for r in results)
    
    async def test_search_with_detailed_scores(self):
        """상세 점수 검색 테스트"""
        # Given
        vector_index = Mock()
        vector_index.setup = AsyncMock()
        vector_index.search_with_scores = AsyncMock(return_value=[
            {'id': 'doc1', 'score': 0.8, 'content': 'test1', 'metadata': {}}
        ])
        
        bm25_index = Mock()
        bm25_index.setup = AsyncMock()
        bm25_index.search_with_scores = AsyncMock(return_value=[
            {'id': 'doc1', 'score': 0.7, 'content': 'test1', 'metadata': {}}
        ])
        
        service = HybridRetrievalService(vector_index, bm25_index)
        
        # When
        result = await service.search_with_detailed_scores(
            "test query", 
            limit=10,
            vector_weight=0.6,
            bm25_weight=0.4
        )
        
        # Then
        assert 'query' in result
        assert 'results' in result
        assert 'search_metadata' in result
        assert 'individual_results' in result
        assert result['search_metadata']['vector_weight'] == 0.6
        assert result['search_metadata']['bm25_weight'] == 0.4
    
    async def test_compare_scoring_methods(self):
        """스코어링 방법 비교 테스트"""
        # Given
        vector_index = Mock()
        vector_index.setup = AsyncMock()
        vector_index.search_with_scores = AsyncMock(return_value=[
            {'id': 'doc1', 'score': 0.8, 'content': 'test1', 'metadata': {}}
        ])
        
        bm25_index = Mock()
        bm25_index.setup = AsyncMock()
        bm25_index.search_with_scores = AsyncMock(return_value=[
            {'id': 'doc2', 'score': 0.9, 'content': 'test2', 'metadata': {}}
        ])
        
        service = HybridRetrievalService(vector_index, bm25_index)
        
        # When
        result = await service.compare_scoring_methods("test query", limit=5)
        
        # Then
        assert 'query' in result
        assert 'comparison' in result
        assert 'statistics' in result
        assert 'vector_only' in result['comparison']
        assert 'bm25_only' in result['comparison']
        assert 'weighted_fusion' in result['comparison']
        assert 'rrf_fusion' in result['comparison']
    
    async def test_teardown(self):
        """서비스 정리 테스트"""
        # Given
        vector_index = Mock()
        vector_index.teardown = AsyncMock()
        
        bm25_index = Mock()
        
        service = HybridRetrievalService(vector_index, bm25_index)
        
        # When
        await service.teardown()
        
        # Then
        # 정리가 예외 없이 완료되어야 함
        vector_index.teardown.assert_called_once() 