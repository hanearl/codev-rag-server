import pytest
from app.features.search.bm25_scorer import BM25KeywordScorer

def test_improved_normalization_should_reflect_absolute_quality():
    """개선된 정규화가 절대적 품질을 반영해야 함"""
    # Given
    scorer = BM25KeywordScorer()
    
    # 매우 다른 품질의 문서들
    documents = [
        ["loan", "class", "finance", "loan", "loan"],  # loan 3번 - 높은 관련성
        ["user", "data", "process"],                   # 관련성 없음
        ["loan", "service"],                           # loan 1번 - 중간 관련성
        ["class", "method", "function"]                # 관련성 없음
    ]
    scorer.fit(documents)
    
    query = ["loan", "class"]
    
    # When
    scores = scorer.get_scores(query)
    normalized = scorer.normalize_scores_improved(scores)
    
    # Then
    # 상대적 순서가 유지되고 차이가 있어야 함
    assert normalized[0] > normalized[2]  # 높은 관련성 > 중간 관련성
    assert normalized[2] > normalized[1]  # 중간 관련성 > 낮은 관련성
    assert normalized[0] > normalized[3]  # 높은 관련성 > 낮은 관련성
    assert normalized[1] == 0.0 or normalized[1] < 0.6  # 관련성 없는 문서는 낮은 점수


def test_sigmoid_normalization_should_handle_score_distribution():
    """시그모이드 정규화가 점수 분포를 적절히 처리해야 함"""
    # Given
    scorer = BM25KeywordScorer()
    
    # When
    raw_scores = [0.0, 1.0, 2.0, 5.0, 10.0]
    normalized = scorer.sigmoid_normalize(raw_scores)
    
    # Then
    # 시그모이드 함수 특성 확인
    assert all(0 <= score <= 1 for score in normalized)  # 0-1 범위
    assert normalized[0] < normalized[1] < normalized[2]  # 단조증가
    assert normalized[-1] > 0.9  # 높은 점수는 1에 가까움
    assert normalized[0] < 0.6   # 낮은 점수는 중간값보다 낮음


def test_percentile_normalization_should_use_statistical_approach():
    """백분위 정규화가 통계적 접근을 사용해야 함"""
    # Given
    scorer = BM25KeywordScorer()
    
    # When
    raw_scores = [0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0]
    normalized = scorer.percentile_normalize(raw_scores)
    
    # Then
    # 백분위 기반 정규화 확인
    assert all(0 <= score <= 1 for score in normalized)
    assert max(normalized) <= 1.0  # 최대값이 항상 1은 아님
    assert min(normalized) >= 0.0  # 최소값이 항상 0은 아님


def test_adaptive_normalization_should_choose_best_method():
    """적응형 정규화가 최적 방법을 선택해야 함"""
    # Given
    scorer = BM25KeywordScorer()
    
    # 다양한 점수 분포 패턴
    uniform_scores = [1.0, 2.0, 3.0, 4.0, 5.0]  # 균등 분포
    skewed_scores = [0.1, 0.2, 0.3, 8.0, 9.0]   # 편향 분포
    sparse_scores = [0.0, 0.0, 0.1, 0.0, 5.0]   # 희소 분포
    
    # When
    norm_uniform = scorer.adaptive_normalize(uniform_scores)
    norm_skewed = scorer.adaptive_normalize(skewed_scores)
    norm_sparse = scorer.adaptive_normalize(sparse_scores)
    
    # Then
    # 각 분포에 적합한 정규화 적용 확인
    assert all(0 <= score <= 1 for score in norm_uniform)
    assert all(0 <= score <= 1 for score in norm_skewed)
    assert all(0 <= score <= 1 for score in norm_sparse)
    
    # 희소 분포에서는 높은 점수가 더 두드러져야 함
    assert max(norm_sparse) > 0.8 