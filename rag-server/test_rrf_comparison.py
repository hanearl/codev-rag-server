#!/usr/bin/env python3
"""
RRF vs 가중치 방식 비교 테스트
OpenSearch와 동일한 RRF 구현 검증
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.features.search.scorer import SearchScorer

def test_rrf_vs_weighted():
    """RRF와 가중치 방식 비교"""
    scorer = SearchScorer()
    
    # 테스트 데이터: 벡터와 키워드 점수가 다른 패턴
    results = [
        {"id": "doc1", "vector_score": 0.9, "keyword_score": 0.2},  # 벡터 강함
        {"id": "doc2", "vector_score": 0.3, "keyword_score": 0.9},  # 키워드 강함
        {"id": "doc3", "vector_score": 0.7, "keyword_score": 0.7},  # 균형잡힌
        {"id": "doc4", "vector_score": 0.8, "keyword_score": 0.1},  # 벡터만
        {"id": "doc5", "vector_score": 0.1, "keyword_score": 0.8}   # 키워드만
    ]
    
    print("=== 원본 데이터 ===")
    for r in results:
        print(f"{r['id']}: vector={r['vector_score']:.1f}, keyword={r['keyword_score']:.1f}")
    
    # 가중치 방식 (벡터 중심)
    weighted_results = scorer._calculate_weighted_scores(
        [r.copy() for r in results], 
        vector_weight=0.8, 
        keyword_weight=0.2
    )
    
    print("\n=== 가중치 방식 (벡터 80%, 키워드 20%) ===")
    for i, r in enumerate(weighted_results, 1):
        print(f"{i}위: {r['id']} - combined_score={r['combined_score']:.3f}")
    
    # RRF 방식
    rrf_results = scorer._calculate_rrf_scores([r.copy() for r in results], k=10)
    
    print("\n=== RRF 방식 (k=10) ===")
    for i, r in enumerate(rrf_results, 1):
        print(f"{i}위: {r['id']} - combined_score={r['combined_score']:.3f}")
    
    # OpenSearch 공식 검증
    print("\n=== OpenSearch RRF 공식 검증 ===")
    test_opensearch_formula(scorer)

def test_opensearch_formula(scorer):
    """OpenSearch 문서의 RRF 공식과 일치하는지 검증"""
    results = [
        {"id": "A", "vector_score": 0.9, "keyword_score": 0.1},  # vector 1위, keyword 3위
        {"id": "B", "vector_score": 0.7, "keyword_score": 0.8},  # vector 2위, keyword 1위  
        {"id": "C", "vector_score": 0.5, "keyword_score": 0.6}   # vector 3위, keyword 2위
    ]
    
    rrf_results = scorer._calculate_rrf_scores(results, k=10)
    
    # 수동 계산
    expected_A = 1/11 + 1/13  # vector 1위 + keyword 3위
    expected_B = 1/12 + 1/11  # vector 2위 + keyword 1위
    expected_C = 1/13 + 1/12  # vector 3위 + keyword 2위
    
    print(f"A: 계산값={expected_A:.4f}, 실제값={rrf_results[1]['combined_score']:.4f}")
    print(f"B: 계산값={expected_B:.4f}, 실제값={rrf_results[0]['combined_score']:.4f}")
    print(f"C: 계산값={expected_C:.4f}, 실제값={rrf_results[2]['combined_score']:.4f}")
    
    # 순위 확인
    print(f"\n순위: {[r['id'] for r in rrf_results]}")
    print("예상 순위: ['B', 'A', 'C'] (B가 가장 높아야 함)")
    
    # 검증
    assert abs(rrf_results[1]['combined_score'] - expected_A) < 0.001, "A 점수 불일치"
    assert abs(rrf_results[0]['combined_score'] - expected_B) < 0.001, "B 점수 불일치"
    assert abs(rrf_results[2]['combined_score'] - expected_C) < 0.001, "C 점수 불일치"
    assert rrf_results[0]['id'] == 'B', "B가 1위가 아님"
    
    print("✅ OpenSearch RRF 공식 검증 성공!")

if __name__ == "__main__":
    test_rrf_vs_weighted() 