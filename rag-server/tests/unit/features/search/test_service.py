import pytest
from unittest.mock import Mock, AsyncMock
from app.features.search.service import SearchService
from app.features.search.schema import SearchRequest

@pytest.fixture
def mock_retriever():
    retriever = Mock()
    retriever.search = AsyncMock()
    return retriever

@pytest.fixture
def mock_scorer():
    scorer = Mock()
    scorer.calculate_combined_scores = Mock()
    return scorer

@pytest.mark.asyncio
async def test_search_service_should_perform_hybrid_search(
    mock_retriever, mock_scorer
):
    """검색 서비스가 하이브리드 검색을 수행해야 함"""
    # Given
    service = SearchService(mock_retriever, mock_scorer)
    
    mock_retriever.search.return_value = [
        {
            "id": "test-id-1",
            "vector_score": 0.9,
            "keyword_score": 0.8,
            "file_path": "test.py",
            "function_name": "test_func",
            "code_content": "def test_func(): pass",
            "code_type": "function",
            "language": "python",
            "line_start": 1,
            "line_end": 1,
            "keywords": ["test", "func"]
        }
    ]
    
    mock_scorer.calculate_combined_scores.return_value = [
        {
            "id": "test-id-1",
            "vector_score": 0.9,
            "keyword_score": 0.8,
            "combined_score": 0.86,
            "file_path": "test.py",
            "function_name": "test_func",
            "code_content": "def test_func(): pass",
            "code_type": "function", 
            "language": "python",
            "line_start": 1,
            "line_end": 1,
            "keywords": ["test", "func"]
        }
    ]
    
    request = SearchRequest(query="test function", keywords=["test"])
    
    # When
    result = await service.search_code(request)
    
    # Then
    assert result.total_results == 1
    assert result.results[0].function_name == "test_func"
    assert result.results[0].combined_score == 0.86
    mock_retriever.search.assert_called_once()
    mock_scorer.calculate_combined_scores.assert_called_once()

@pytest.mark.asyncio
async def test_search_service_should_count_result_types(
    mock_retriever, mock_scorer
):
    """검색 서비스가 결과 타입별 개수를 계산해야 함"""
    # Given
    service = SearchService(mock_retriever, mock_scorer)
    
    mock_retriever.search.return_value = [
        {"id": "1", "vector_score": 0.9, "keyword_score": 0.0},  # 벡터만
        {"id": "2", "vector_score": 0.0, "keyword_score": 0.8},  # 키워드만
        {"id": "3", "vector_score": 0.7, "keyword_score": 0.6},  # 둘 다
    ]
    
    mock_scorer.calculate_combined_scores.return_value = [
        {"id": "1", "vector_score": 0.9, "keyword_score": 0.0, "combined_score": 0.63, "file_path": "test1.py", "code_content": "test1", "code_type": "function", "language": "python", "line_start": 1, "line_end": 1, "keywords": []},
        {"id": "2", "vector_score": 0.0, "keyword_score": 0.8, "combined_score": 0.24, "file_path": "test2.py", "code_content": "test2", "code_type": "function", "language": "python", "line_start": 1, "line_end": 1, "keywords": []},
        {"id": "3", "vector_score": 0.7, "keyword_score": 0.6, "combined_score": 0.67, "file_path": "test3.py", "code_content": "test3", "code_type": "function", "language": "python", "line_start": 1, "line_end": 1, "keywords": []},
    ]
    
    request = SearchRequest(query="test")
    
    # When
    result = await service.search_code(request)
    
    # Then
    assert result.vector_results_count == 2  # ID 1, 3
    assert result.keyword_results_count == 2  # ID 2, 3

@pytest.mark.asyncio
async def test_search_service_should_measure_search_time(
    mock_retriever, mock_scorer
):
    """검색 서비스가 검색 시간을 측정해야 함"""
    # Given
    service = SearchService(mock_retriever, mock_scorer)
    
    mock_retriever.search.return_value = []
    mock_scorer.calculate_combined_scores.return_value = []
    
    request = SearchRequest(query="test")
    
    # When
    result = await service.search_code(request)
    
    # Then
    assert result.search_time_ms >= 0
    assert isinstance(result.search_time_ms, int) 