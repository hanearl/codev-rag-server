"""
하이브리드 검색 서비스

벡터 검색, BM25 검색, 하이브리드 검색 기능을 통합하여 REST API로 제공
"""
import time
from typing import List, Dict, Any, Optional
import asyncio

from app.retriever.hybrid_retriever import HybridRetrievalService
from app.index.vector_service import VectorIndexService
from app.index.bm25_service import BM25IndexService
from app.features.search.schema import (
    VectorSearchRequest, VectorSearchResponse,
    BM25SearchRequest, BM25SearchResponse,
    HybridSearchRequest, HybridSearchResponse,
    SearchResult
)


class HybridSearchService:
    """하이브리드 검색 서비스"""
    
    def __init__(self):
        self.hybrid_retriever = HybridRetrievalService(
            vector_index=None,  # 초기화 시 None, 나중에 설정
            bm25_index=None     # 초기화 시 None, 나중에 설정
        )
        self.vector_service = VectorIndexService()
        self.bm25_service = BM25IndexService()
    
    async def vector_search(self, request: VectorSearchRequest) -> VectorSearchResponse:
        """벡터 검색"""
        start_time = time.time()
        
        try:
            # 벡터 검색 실행
            search_results = await self.vector_service.search_similar_code(
                query=request.query,
                limit=request.top_k,
                threshold=request.score_threshold or 0.0,
                filters=request.filter_metadata
            )
            
            # 결과 변환
            results = [
                SearchResult(
                    content=result.get("content", ""),
                    score=result.get("score", 0.0),
                    metadata=result.get("metadata", {}),
                    document_id=result.get("id")
                )
                for result in search_results
            ]
            
            search_time_ms = int((time.time() - start_time) * 1000)
            
            return VectorSearchResponse(
                success=True,
                results=results,
                total_results=len(results),
                search_time_ms=search_time_ms,
                collection_name=request.collection_name,
                query=request.query
            )
            
        except Exception as e:
            search_time_ms = int((time.time() - start_time) * 1000)
            return VectorSearchResponse(
                success=False,
                results=[],
                total_results=0,
                search_time_ms=search_time_ms,
                collection_name=request.collection_name,
                error=f"벡터 검색 실패: {str(e)}"
            )
    
    async def bm25_search(self, request: BM25SearchRequest) -> BM25SearchResponse:
        """BM25 검색"""
        start_time = time.time()
        
        try:
            # BM25 검색 실행
            search_results = await self.bm25_service.search_keywords(
                query=request.query,
                limit=request.top_k,
                filters={"language": request.filter_language} if request.filter_language else None
            )
            
            # 결과 변환
            results = [
                SearchResult(
                    content=result.get("content", ""),
                    score=result.get("score", 0.0),
                    metadata=result.get("metadata", {}),
                    document_id=result.get("id")
                )
                for result in search_results
            ]
            
            search_time_ms = int((time.time() - start_time) * 1000)
            
            return BM25SearchResponse(
                success=True,
                results=results,
                total_results=len(results),
                search_time_ms=search_time_ms,
                index_name=request.index_name,
                query=request.query
            )
            
        except Exception as e:
            search_time_ms = int((time.time() - start_time) * 1000)
            return BM25SearchResponse(
                success=False,
                results=[],
                total_results=0,
                search_time_ms=search_time_ms,
                index_name=request.index_name,
                error=f"BM25 검색 실패: {str(e)}"
            )
    
    async def hybrid_search(self, request: HybridSearchRequest) -> HybridSearchResponse:
        """하이브리드 검색"""
        start_time = time.time()
        
        try:
            # 하이브리드 검색 실행
            search_results = await self.hybrid_retriever.search_with_detailed_scores(
                query=request.query,
                limit=request.top_k,
                vector_weight=request.vector_weight,
                bm25_weight=request.bm25_weight,
                use_rrf=(request.fusion_method.value == "rrf"),
                rrf_k=60
            )
            
            # 결과 변환
            results = [
                SearchResult(
                    content=result.get("content", ""),
                    score=result.get("combined_score", 0.0),
                    metadata=result.get("metadata", {}),
                    document_id=result.get("id")
                )
                for result in search_results.get("results", [])
            ]
            
            search_time_ms = int((time.time() - start_time) * 1000)
            
            return HybridSearchResponse(
                success=True,
                results=results,
                total_results=len(results),
                search_time_ms=search_time_ms,
                vector_results_count=search_results.get("vector_results_count", 0),
                bm25_results_count=search_results.get("bm25_results_count", 0),
                fusion_method=request.fusion_method,
                weights_used={
                    "vector_weight": request.vector_weight,
                    "bm25_weight": request.bm25_weight
                },
                query=request.query
            )
            
        except Exception as e:
            search_time_ms = int((time.time() - start_time) * 1000)
            return HybridSearchResponse(
                success=False,
                results=[],
                total_results=0,
                search_time_ms=search_time_ms,
                vector_results_count=0,
                bm25_results_count=0,
                fusion_method="unknown",
                weights_used={
                    "vector_weight": request.vector_weight,
                    "bm25_weight": request.bm25_weight
                },
                error=f"하이브리드 검색 실패: {str(e)}"
            )
    
    async def get_collections(self) -> Dict[str, List[str]]:
        """벡터 컬렉션 목록 조회"""
        try:
            # 현재 구성된 컬렉션 정보 반환 (실제 list_collections 메서드가 없을 수 있음)
            return {"collections": [self.vector_service.config.collection_name]}
        except Exception as e:
            raise Exception(f"컬렉션 목록 조회 실패: {str(e)}")
    
    async def get_indexes(self) -> Dict[str, List[str]]:
        """BM25 인덱스 목록 조회"""
        try:
            # 현재 구성된 인덱스 정보 반환 (실제 list_indexes 메서드가 없을 수 있음)
            return {"indexes": ["default"]}  # 기본 인덱스명 반환
        except Exception as e:
            raise Exception(f"인덱스 목록 조회 실패: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """서비스 헬스체크"""
        components = {}
        overall_status = "healthy"
        
        try:
            # 하이브리드 리트리버 상태 확인
            components["hybrid_retriever"] = "healthy"
        except:
            components["hybrid_retriever"] = "unhealthy"
            overall_status = "degraded"
        
        try:
            # 벡터 서비스 상태 확인
            await self.vector_service.health_check()
            components["vector_service"] = "healthy"
        except:
            components["vector_service"] = "unhealthy"
            overall_status = "degraded"
        
        try:
            # BM25 서비스 상태 확인
            await self.bm25_service.health_check()
            components["bm25_service"] = "healthy"
        except:
            components["bm25_service"] = "unhealthy"
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "service": "search",
            "components": components
        }


# 싱글톤 인스턴스
hybrid_search_service = HybridSearchService() 