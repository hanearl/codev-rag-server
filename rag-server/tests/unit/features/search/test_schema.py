import pytest
from pydantic import ValidationError
from app.features.search.schema import SearchRequest, SearchResponse

def test_search_request_should_validate_required_fields():
    """검색 요청이 필수 필드를 검증해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        SearchRequest()  # query 필드 누락
    
    # Valid request
    request = SearchRequest(query="test function")
    assert request.query == "test function"
    assert request.limit == 10  # 기본값
    assert request.vector_weight == 0.7  # 기본값
    assert request.keyword_weight == 0.3  # 기본값

def test_search_request_should_validate_weights():
    """검색 요청이 가중치를 검증해야 함"""
    # Given & When & Then
    with pytest.raises(ValidationError):
        SearchRequest(query="test", vector_weight=1.5)  # 1.0 초과
    
    with pytest.raises(ValidationError):
        SearchRequest(query="test", keyword_weight=-0.1)  # 0.0 미만

def test_search_request_should_set_default_collection():
    """검색 요청이 기본 컬렉션을 설정해야 함"""
    # Given & When
    request = SearchRequest(query="test query")
    
    # Then
    assert request.collection_name == "code_chunks"

def test_search_request_should_accept_custom_collection():
    """검색 요청이 사용자 정의 컬렉션을 받아야 함"""
    # Given & When
    request = SearchRequest(query="test query", collection_name="custom_collection")
    
    # Then
    assert request.collection_name == "custom_collection" 