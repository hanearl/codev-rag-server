import time
from typing import List
from .schema import SearchRequest, SearchResponse, SearchResult
from .retriever import HybridRetriever
from .scorer import SearchScorer
from .keyword_extractor import keyword_extractor
import logging

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, retriever: HybridRetriever, scorer: SearchScorer):
        self.retriever = retriever
        self.scorer = scorer
    
    async def search_code(self, request: SearchRequest) -> SearchResponse:
        """코드 하이브리드 검색"""
        start_time = time.time()
        
        try:
            # 키워드 자동 추출 (명시적 키워드가 없을 경우)
            search_keywords = request.keywords
            if search_keywords is None or len(search_keywords) == 0:
                extracted_keywords = keyword_extractor.extract_keywords(request.query)
                search_keywords = extracted_keywords[:5]  # 상위 5개만 사용
                logger.info(f"쿼리 '{request.query}'에서 자동 추출된 키워드: {search_keywords}")
            
            # 하이브리드 검색 수행
            raw_results = await self.retriever.search(
                query=request.query,
                keywords=search_keywords,
                limit=request.limit,
                collection_name=request.collection_name
            )
            
            # 점수 계산 및 정렬 (RRF 또는 가중치 기반)
            scored_results = self.scorer.calculate_combined_scores(
                raw_results,
                vector_weight=request.vector_weight,
                keyword_weight=request.keyword_weight,
                use_rrf=request.use_rrf,
                rrf_k=request.rrf_k
            )
            
            # 결과 변환
            search_results = []
            vector_count = 0
            keyword_count = 0
            
            for result in scored_results:
                search_result = SearchResult(
                    id=result["id"],
                    file_path=result.get("file_path", ""),
                    function_name=result.get("function_name"),
                    code_content=result.get("code_content", ""),
                    code_type=result.get("code_type", ""),
                    language=result.get("language", ""),
                    line_start=result.get("line_start", 0),
                    line_end=result.get("line_end", 0),
                    keywords=result.get("keywords", []),
                    vector_score=result["vector_score"],
                    keyword_score=result["keyword_score"],
                    combined_score=result["combined_score"]
                )
                search_results.append(search_result)
                
                if result["vector_score"] > 0:
                    vector_count += 1
                if result["keyword_score"] > 0:
                    keyword_count += 1
            
            end_time = time.time()
            search_time_ms = int((end_time - start_time) * 1000)
            
            return SearchResponse(
                query=request.query,
                results=search_results,
                total_results=len(search_results),
                search_time_ms=search_time_ms,
                vector_results_count=vector_count,
                keyword_results_count=keyword_count,
                search_method="rrf" if request.use_rrf else "weighted",
                rrf_k=request.rrf_k if request.use_rrf else None
            )
            
        except Exception as e:
            logger.error(f"코드 검색 실패: {e}")
            raise 