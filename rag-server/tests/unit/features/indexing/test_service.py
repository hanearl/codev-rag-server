import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from datetime import datetime
from app.features.indexing.service import IndexingService
from app.features.indexing.schema import IndexingRequest, BatchIndexingRequest
from app.features.indexing.schemas import CodeChunk, CodeType, LanguageType

@pytest.fixture
def mock_embedding_client():
    client = Mock()
    client.embed_bulk = AsyncMock()
    return client

@pytest.fixture
def mock_vector_client():
    client = Mock()
    client.insert_code_embedding = Mock()
    client.delete_by_file_path = Mock()
    return client

@pytest.fixture
def mock_parser_factory():
    factory = Mock()
    parser = Mock()
    parser.parse_file = Mock()
    factory.get_parser = Mock(return_value=parser)
    return factory, parser

@pytest.mark.asyncio
async def test_indexing_service_should_process_file(
    mock_embedding_client, mock_vector_client, mock_parser_factory
):
    """인덱싱 서비스가 파일을 처리해야 함"""
    # Given
    factory, parser = mock_parser_factory
    service = IndexingService(mock_embedding_client, mock_vector_client, factory)
    
    mock_chunks = [
        CodeChunk(
            name="test_func",
            code_content="def test_func(): pass",
            code_type=CodeType.FUNCTION,
            language=LanguageType.PYTHON,
            file_path="test.py",
            line_start=1,
            line_end=1,
            keywords=["test", "func"]
        )
    ]
    
    from app.features.indexing.schemas import ParseResult
    parser.parse_file.return_value = ParseResult(
        chunks=mock_chunks,
        language=LanguageType.PYTHON,
        file_path="test.py",
        total_lines=1,
        errors=[]
    )
    
    mock_embedding_client.embed_bulk.return_value = {
        "embeddings": [{"embedding": [0.1, 0.2, 0.3]}],
        "count": 1
    }
    
    mock_vector_client.insert_code_embedding.return_value = "test-id"
    
    request = IndexingRequest(file_path="test.py")
    
    # When
    with patch('os.path.exists', return_value=True):
        result = await service.index_file(request)
    
    # Then
    assert result.chunks_count == 1
    assert result.file_path == "test.py"
    assert "성공" in result.message
    mock_embedding_client.embed_bulk.assert_called_once()
    mock_vector_client.insert_code_embedding.assert_called_once()

@pytest.mark.asyncio
async def test_indexing_service_should_handle_file_not_found(
    mock_embedding_client, mock_vector_client, mock_parser_factory
):
    """인덱싱 서비스가 파일을 찾을 수 없을 때 예외를 발생시켜야 함"""
    # Given
    factory, parser = mock_parser_factory
    service = IndexingService(mock_embedding_client, mock_vector_client, factory)
    request = IndexingRequest(file_path="nonexistent.py")
    
    # When & Then
    with patch('os.path.exists', return_value=False):
        with pytest.raises(FileNotFoundError):
            await service.index_file(request)

@pytest.mark.asyncio
async def test_indexing_service_should_handle_empty_file(
    mock_embedding_client, mock_vector_client, mock_parser_factory
):
    """인덱싱 서비스가 빈 파일을 처리해야 함"""
    # Given
    factory, parser = mock_parser_factory
    service = IndexingService(mock_embedding_client, mock_vector_client, factory)
    
    from app.features.indexing.schemas import ParseResult
    parser.parse_file.return_value = ParseResult(
        chunks=[],
        language=LanguageType.PYTHON,
        file_path="empty.py",
        total_lines=0,
        errors=[]
    )
    
    request = IndexingRequest(file_path="empty.py")
    
    # When
    with patch('os.path.exists', return_value=True):
        result = await service.index_file(request)
    
    # Then
    assert result.chunks_count == 0
    assert "처리할 코드 청크가 없습니다" in result.message

@pytest.mark.asyncio
async def test_indexing_service_should_force_update_existing_file(
    mock_embedding_client, mock_vector_client, mock_parser_factory
):
    """인덱싱 서비스가 기존 파일을 강제 업데이트해야 함"""
    # Given
    factory, parser = mock_parser_factory
    service = IndexingService(mock_embedding_client, mock_vector_client, factory)
    
    mock_chunks = [
        CodeChunk(
            name="updated_func",
            code_content="def updated_func(): pass",
            code_type=CodeType.FUNCTION,
            language=LanguageType.PYTHON,
            file_path="test.py",
            line_start=1,
            line_end=1,
            keywords=["updated", "func"]
        )
    ]
    
    from app.features.indexing.schemas import ParseResult
    parser.parse_file.return_value = ParseResult(
        chunks=mock_chunks,
        language=LanguageType.PYTHON,
        file_path="test.py",
        total_lines=1,
        errors=[]
    )
    
    mock_embedding_client.embed_bulk.return_value = {
        "embeddings": [{"embedding": [0.4, 0.5, 0.6]}],
        "count": 1
    }
    
    mock_vector_client.delete_by_file_path.return_value = 1
    mock_vector_client.insert_code_embedding.return_value = "updated-id"
    
    request = IndexingRequest(file_path="test.py", force_update=True)
    
    # When
    with patch('os.path.exists', return_value=True):
        result = await service.index_file(request)
    
    # Then
    assert result.chunks_count == 1
    assert "업데이트" in result.message
    mock_vector_client.delete_by_file_path.assert_called_once_with("code_chunks", "test.py")

@pytest.mark.asyncio
async def test_indexing_service_should_process_batch_files(
    mock_embedding_client, mock_vector_client, mock_parser_factory
):
    """인덱싱 서비스가 배치 파일들을 처리해야 함"""
    # Given
    factory, parser = mock_parser_factory
    service = IndexingService(mock_embedding_client, mock_vector_client, factory)
    
    mock_chunks = [
        CodeChunk(
            name="test_func",
            code_content="def test_func(): pass",
            code_type=CodeType.FUNCTION,
            language=LanguageType.PYTHON,
            file_path="test1.py",
            line_start=1,
            line_end=1,
            keywords=["test", "func"]
        )
    ]
    
    from app.features.indexing.schemas import ParseResult
    parser.parse_file.return_value = ParseResult(
        chunks=mock_chunks,
        language=LanguageType.PYTHON,
        file_path="test1.py",
        total_lines=1,
        errors=[]
    )
    
    mock_embedding_client.embed_bulk.return_value = {
        "embeddings": [{"embedding": [0.1, 0.2, 0.3]}],
        "count": 1
    }
    
    mock_vector_client.insert_code_embedding.return_value = "test-id"
    
    request = BatchIndexingRequest(file_paths=["test1.py", "test2.py"])
    
    # When
    with patch('os.path.exists', return_value=True):
        result = await service.index_batch(request)
    
    # Then
    assert result.total_files == 2
    assert result.successful_files == 2
    assert result.failed_files == 0
    assert result.total_chunks == 2

@pytest.mark.asyncio
async def test_indexing_service_should_query_chunks_with_no_filters(
    mock_embedding_client, mock_vector_client, mock_parser_factory
):
    """필터 없이 청크를 조회해야 함"""
    # Given
    factory, parser = mock_parser_factory
    service = IndexingService(mock_embedding_client, mock_vector_client, factory)
    
    from app.features.indexing.schema import ChunkQueryRequest
    request = ChunkQueryRequest(page=1, size=10)
    
    mock_chunks_data = [
        {
            "id": "chunk-1",
            "file_path": "test.py",
            "function_name": "test_func",
            "code_content": "def test_func(): pass",
            "code_type": "function",
            "language": "python",
            "line_start": 1,
            "line_end": 1,
            "keywords": ["test", "func"],
            "indexed_at": "2024-01-01T00:00:00"
        }
    ]
    
    mock_vector_client.query_chunks.return_value = (mock_chunks_data, 1)
    
    # When
    result = await service.query_chunks(request)
    
    # Then
    assert len(result.chunks) == 1
    assert result.total == 1
    assert result.page == 1
    assert result.size == 10
    assert result.total_pages == 1
    assert result.chunks[0].id == "chunk-1"
    assert result.chunks[0].file_path == "test.py"
    
    mock_vector_client.query_chunks.assert_called_once_with(
        collection_name="code_chunks",
        file_path=None,
        code_type=None,
        language=None,
        keyword=None,
        offset=0,
        limit=10
    )

@pytest.mark.asyncio
async def test_indexing_service_should_query_chunks_with_filters(
    mock_embedding_client, mock_vector_client, mock_parser_factory
):
    """필터를 적용하여 청크를 조회해야 함"""
    # Given
    factory, parser = mock_parser_factory
    service = IndexingService(mock_embedding_client, mock_vector_client, factory)
    
    from app.features.indexing.schema import ChunkQueryRequest
    request = ChunkQueryRequest(
        file_path="test.py",
        code_type="function",
        language="python",
        keyword="test",
        page=2,
        size=5
    )
    
    mock_chunks_data = [
        {
            "id": "chunk-2",
            "file_path": "test.py",
            "function_name": "test_func2",
            "code_content": "def test_func2(): pass",
            "code_type": "function",
            "language": "python",
            "line_start": 3,
            "line_end": 3,
            "keywords": ["test", "func2"],
            "indexed_at": "2024-01-01T00:00:00"
        }
    ]
    
    mock_vector_client.query_chunks.return_value = (mock_chunks_data, 15)
    
    # When
    result = await service.query_chunks(request)
    
    # Then
    assert len(result.chunks) == 1
    assert result.total == 15
    assert result.page == 2
    assert result.size == 5
    assert result.total_pages == 3  # ceil(15/5)
    assert result.chunks[0].file_path == "test.py"
    assert result.chunks[0].code_type == "function"
    
    mock_vector_client.query_chunks.assert_called_once_with(
        collection_name="code_chunks",
        file_path="test.py",
        code_type="function",
        language="python",
        keyword="test",
        offset=5,  # (page-1) * size = (2-1) * 5
        limit=5
    )

@pytest.mark.asyncio
async def test_indexing_service_should_handle_empty_chunk_query_result(
    mock_embedding_client, mock_vector_client, mock_parser_factory
):
    """빈 청크 조회 결과를 처리해야 함"""
    # Given
    factory, parser = mock_parser_factory
    service = IndexingService(mock_embedding_client, mock_vector_client, factory)
    
    from app.features.indexing.schema import ChunkQueryRequest
    request = ChunkQueryRequest(file_path="nonexistent.py")
    
    mock_vector_client.query_chunks.return_value = ([], 0)
    
    # When
    result = await service.query_chunks(request)
    
    # Then
    assert len(result.chunks) == 0
    assert result.total == 0
    assert result.page == 1
    assert result.size == 10
    assert result.total_pages == 0 