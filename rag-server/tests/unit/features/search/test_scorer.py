import pytest
from app.features.search.scorer import SearchScorer

def test_search_scorer_should_calculate_combined_score():
    """스코어러가 결합 점수를 계산해야 함"""
    # Given
    scorer = SearchScorer()
    
    results = [
        {"id": "1", "vector_score": 0.9, "keyword_score": 0.7},
        {"id": "2", "vector_score": 0.8, "keyword_score": 0.6},
        {"id": "3", "vector_score": 0.7, "keyword_score": 0.9}
    ]
    
    # When
    scored_results = scorer.calculate_combined_scores(
        results, vector_weight=0.7, keyword_weight=0.3
    )
    
    # Then - 정렬된 순서대로 검증 (높은 점수부터)
    # ID "3": 0.7 * 0.7 + 0.9 * 0.3 = 0.76 (가장 높음)
    # ID "1": 0.9 * 0.7 + 0.7 * 0.3 = 0.84 (최고점)
    # ID "2": 0.8 * 0.7 + 0.6 * 0.3 = 0.74 (최하점)
    assert scored_results[0]["id"] == "1"  # 0.84
    assert scored_results[1]["id"] == "3"  # 0.76
    assert scored_results[2]["id"] == "2"  # 0.74

def test_search_scorer_should_sort_by_combined_score():
    """스코어러가 결합 점수 순으로 정렬해야 함"""
    # Given
    scorer = SearchScorer()
    
    results = [
        {"id": "1", "vector_score": 0.5, "keyword_score": 0.9},  # 0.62
        {"id": "2", "vector_score": 0.9, "keyword_score": 0.5},  # 0.78  
        {"id": "3", "vector_score": 0.8, "keyword_score": 0.8}   # 0.8
    ]
    
    # When
    scored_results = scorer.calculate_combined_scores(
        results, vector_weight=0.7, keyword_weight=0.3
    )
    
    # Then
    assert scored_results[0]["id"] == "3"  # 가장 높은 점수
    assert scored_results[1]["id"] == "2"
    assert scored_results[2]["id"] == "1"

def test_search_scorer_should_handle_missing_scores():
    """스코어러가 누락된 점수를 처리해야 함"""
    # Given
    scorer = SearchScorer()
    
    results = [
        {"id": "1", "vector_score": 0.9},  # keyword_score 누락
        {"id": "2", "keyword_score": 0.8}  # vector_score 누락
    ]
    
    # When
    scored_results = scorer.calculate_combined_scores(results)
    
    # Then
    assert scored_results[0]["combined_score"] == 0.9 * 0.7  # keyword_score = 0
    assert scored_results[1]["combined_score"] == 0.8 * 0.3  # vector_score = 0

def test_search_scorer_should_normalize_scores():
    """스코어러가 점수를 정규화해야 함"""
    # Given
    scorer = SearchScorer()
    
    results = [
        {"id": "1", "vector_score": 0.8, "keyword_score": 1.6},
        {"id": "2", "vector_score": 0.4, "keyword_score": 0.8}
    ]
    
    # When
    normalized_results = scorer.normalize_scores(results)
    
    # Then
    assert normalized_results[0]["vector_score"] == 1.0  # 0.8 / 0.8 (max)
    assert normalized_results[1]["vector_score"] == 0.5  # 0.4 / 0.8 (max)
    assert normalized_results[0]["keyword_score"] == 1.0  # 1.6 / 1.6 (max)
    assert normalized_results[1]["keyword_score"] == 0.5  # 0.8 / 1.6 (max) 