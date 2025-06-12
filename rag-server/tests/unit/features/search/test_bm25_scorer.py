import pytest
from app.features.search.bm25_scorer import BM25KeywordScorer

def test_bm25_scorer_should_calculate_score_for_single_document():
    """BM25 스코어러가 단일 문서에 대해 점수를 계산해야 함"""
    # Given
    scorer = BM25KeywordScorer()
    
    # 문서 컬렉션 구축
    documents = [
        ["function", "process", "data", "return"],
        ["class", "method", "function", "java"],
        ["search", "query", "database", "function"]
    ]
    scorer.fit(documents)
    
    query = ["function", "data"]
    doc_index = 0  # 첫 번째 문서
    
    # When
    score = scorer.score(query, doc_index)
    
    # Then
    assert isinstance(score, float)
    assert score > 0  # 매칭되는 키워드가 있으므로 양수


def test_bm25_scorer_should_give_higher_score_for_better_matches():
    """BM25 스코어러가 더 잘 매칭되는 문서에 더 높은 점수를 줘야 함"""
    # Given
    scorer = BM25KeywordScorer()
    
    documents = [
        ["function", "process", "data", "return"],              # 3개 매칭
        ["class", "method", "other", "java"],                   # 매칭 없음
        ["function", "data", "process", "search", "function"]   # 3개 매칭, function 2번
    ]
    scorer.fit(documents)
    
    query = ["function", "data", "process"]
    
    # When
    score_0 = scorer.score(query, 0)  # 모든 키워드 매칭
    score_1 = scorer.score(query, 1)  # 매칭 없음
    score_2 = scorer.score(query, 2)  # 모든 키워드 매칭, function 중복
    
    # Then
    assert score_0 > score_1  # 매칭 있는 것이 없는 것보다 높음
    assert score_2 > score_1  # 매칭 있는 것이 없는 것보다 높음
    assert score_1 == 0  # 매칭되는 키워드 없음


def test_bm25_scorer_should_handle_empty_query():
    """BM25 스코어러가 빈 쿼리를 처리해야 함"""
    # Given
    scorer = BM25KeywordScorer()
    documents = [["function", "data"]]
    scorer.fit(documents)
    
    # When
    score = scorer.score([], 0)
    
    # Then
    assert score == 0.0


def test_bm25_scorer_should_handle_unknown_terms():
    """BM25 스코어러가 미지의 용어를 처리해야 함"""
    # Given
    scorer = BM25KeywordScorer()
    documents = [["function", "data"]]
    scorer.fit(documents)
    
    query = ["unknown", "terms"]
    
    # When
    score = scorer.score(query, 0)
    
    # Then
    assert score == 0.0


def test_bm25_scorer_should_work_with_code_content():
    """BM25 스코어러가 실제 코드 내용으로 작동해야 함"""
    # Given
    scorer = BM25KeywordScorer()
    
    # 실제 코드 내용을 토큰화
    documents = [
        ["def", "process", "data", "return", "result"],
        ["class", "UserController", "def", "get", "user"],
        ["function", "search", "database", "query", "execute"]
    ]
    scorer.fit(documents)
    
    query = ["process", "data"]
    
    # When
    scores = [scorer.score(query, i) for i in range(len(documents))]
    
    # Then
    assert scores[0] > scores[1]  # 첫 번째 문서가 가장 관련성 높음
    assert scores[0] > scores[2]


def test_bm25_scorer_should_use_configurable_parameters():
    """BM25 스코어러가 설정 가능한 매개변수를 사용해야 함"""
    # Given
    scorer_default = BM25KeywordScorer()
    scorer_custom = BM25KeywordScorer(k1=2.0, b=0.5)
    
    # 여러 문서로 더 복잡한 컬렉션 구성
    documents = [
        ["function", "data", "process"],
        ["function", "function", "code"],  # function 빈도가 높음
        ["data", "structure", "algorithm"]
    ]
    scorer_default.fit(documents)
    scorer_custom.fit(documents)
    
    query = ["function"]
    
    # When
    score_default = scorer_default.score(query, 1)  # function이 많은 문서
    score_custom = scorer_custom.score(query, 1)
    
    # Then
    assert score_default != score_custom  # 매개변수가 다르면 점수도 달라야 함
    assert score_default > 0
    assert score_custom > 0 