from typing import List, Dict, Any

class SearchScorer:
    def calculate_combined_scores(
        self, 
        results: List[Dict[str, Any]], 
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        use_rrf: bool = False,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """결합 점수 계산 및 정렬"""
        if use_rrf:
            return self._calculate_rrf_scores(results, rrf_k)
        else:
            return self._calculate_weighted_scores(results, vector_weight, keyword_weight)
    
    def _calculate_weighted_scores(
        self, 
        results: List[Dict[str, Any]], 
        vector_weight: float,
        keyword_weight: float
    ) -> List[Dict[str, Any]]:
        """가중치 기반 점수 계산 (기존 방식)"""
        for result in results:
            vector_score = result.get("vector_score", 0.0)
            keyword_score = result.get("keyword_score", 0.0)
            
            combined_score = (
                vector_score * vector_weight + 
                keyword_score * keyword_weight
            )
            
            result["combined_score"] = combined_score
        
        # 결합 점수 기준 내림차순 정렬
        return sorted(results, key=lambda x: x["combined_score"], reverse=True)
    
    def _calculate_rrf_scores(
        self, 
        results: List[Dict[str, Any]], 
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """RRF (Reciprocal Rank Fusion) 점수 계산"""
        # 벡터 검색 결과 순위 매핑
        vector_results = [r for r in results if r.get("vector_score", 0.0) > 0]
        vector_results.sort(key=lambda x: x["vector_score"], reverse=True)
        vector_ranks = {r["id"]: idx + 1 for idx, r in enumerate(vector_results)}
        
        # 키워드 검색 결과 순위 매핑
        keyword_results = [r for r in results if r.get("keyword_score", 0.0) > 0]
        keyword_results.sort(key=lambda x: x["keyword_score"], reverse=True)
        keyword_ranks = {r["id"]: idx + 1 for idx, r in enumerate(keyword_results)}
        
        # RRF 점수 계산
        for result in results:
            doc_id = result["id"]
            rrf_score = 0.0
            
            # 벡터 검색에서의 기여도
            if doc_id in vector_ranks:
                rrf_score += 1.0 / (k + vector_ranks[doc_id])
            
            # 키워드 검색에서의 기여도
            if doc_id in keyword_ranks:
                rrf_score += 1.0 / (k + keyword_ranks[doc_id])
            
            result["combined_score"] = rrf_score
        
        # RRF 점수 기준 내림차순 정렬
        return sorted(results, key=lambda x: x["combined_score"], reverse=True)
    
    def normalize_scores(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """점수 정규화 (0-1 범위)"""
        if not results:
            return results
        
        # 각 점수 타입별 최대값 찾기
        max_vector = max(r.get("vector_score", 0.0) for r in results)
        max_keyword = max(r.get("keyword_score", 0.0) for r in results)
        
        # 정규화 적용
        for result in results:
            if max_vector > 0:
                result["vector_score"] = result.get("vector_score", 0.0) / max_vector
            if max_keyword > 0:
                result["keyword_score"] = result.get("keyword_score", 0.0) / max_keyword
        
        return results 