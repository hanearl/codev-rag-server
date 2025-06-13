import pytest
from unittest.mock import Mock, AsyncMock
from llama_index.core import Document
from app.retriever.document_builder import (
    DocumentBuilder, 
    DocumentBuildConfig, 
    ChunkingStrategy,
    EnhancedDocument,
    DocumentBuildResult
)
from app.retriever.document_service import DocumentService
from app.retriever.ast_parser import ParseResult, CodeMetadata, Language, CodeType

class TestDocumentBuilder:
    """Document Builder 테스트"""
    
    @pytest.fixture
    def sample_metadata(self):
        """테스트용 CodeMetadata"""
        return CodeMetadata(
            file_path="test.java",
            language=Language.JAVA,
            code_type=CodeType.METHOD,
            name="testMethod",
            line_start=10,
            line_end=20,
            namespace="com.example",
            parent_class="TestClass",
            modifiers=["public", "static"],
            annotations=["Override"],
            parameters=[{"name": "param1", "type": "String"}],
            return_type="Integer",
            keywords=["test", "method"]
        )
    
    @pytest.fixture
    def sample_document(self, sample_metadata):
        """테스트용 Document"""
        return Document(
            text="public static Integer testMethod(String param1) { return 1; }",
            metadata=sample_metadata.model_dump(),
            id_="test_doc_id"
        )
    
    @pytest.fixture
    def sample_parse_result(self, sample_document):
        """테스트용 ParseResult"""
        return ParseResult(
            documents=[sample_document],
            nodes=[],
            metadata={"source": "test"},
            parse_time_ms=100
        )
    
    @pytest.fixture
    def sample_legacy_chunks(self):
        """테스트용 기존 청크"""
        return [
            {
                "file_path": "legacy.java",
                "language": "java",
                "code_type": "method",
                "name": "legacyMethod",
                "line_start": 5,
                "line_end": 15,
                "code_content": "public void legacyMethod() { }",
                "parent_class": "LegacyClass",
                "modifiers": ["public"],
                "parameters": [],
                "return_type": "void"
            }
        ]
    
    def test_document_builder_initialization(self):
        """Document Builder 초기화 테스트"""
        # Given & When
        builder = DocumentBuilder()
        
        # Then
        assert builder.config is not None
        assert builder.config.chunking_strategy == ChunkingStrategy.METHOD_LEVEL
        assert builder.node_parser is not None
    
    def test_document_builder_with_custom_config(self):
        """커스텀 설정으로 Document Builder 초기화 테스트"""
        # Given
        config = DocumentBuildConfig(
            chunking_strategy=ChunkingStrategy.CLASS_LEVEL,
            max_chunk_size=2048,
            enhance_keywords=False
        )
        
        # When
        builder = DocumentBuilder(config)
        
        # Then
        assert builder.config.chunking_strategy == ChunkingStrategy.CLASS_LEVEL
        assert builder.config.max_chunk_size == 2048
        assert builder.config.enhance_keywords is False
    
    @pytest.mark.asyncio
    async def test_build_from_parse_result(self, sample_parse_result):
        """파싱 결과로부터 Document 빌드 테스트"""
        # Given
        builder = DocumentBuilder()
        
        # When
        result = await builder.build_from_parse_result(sample_parse_result)
        
        # Then
        assert isinstance(result, DocumentBuildResult)
        assert result.total_documents == 1
        assert len(result.documents) == 1
        assert result.build_time_ms >= 0
        assert "methods" in result.statistics
        assert result.statistics["methods"] == 1
    
    @pytest.mark.asyncio
    async def test_build_from_legacy_chunks(self, sample_legacy_chunks):
        """기존 청크로부터 Document 빌드 테스트"""
        # Given
        builder = DocumentBuilder()
        
        # When
        result = await builder.build_from_legacy_chunks(sample_legacy_chunks)
        
        # Then
        assert isinstance(result, DocumentBuildResult)
        assert result.total_documents == 1
        assert len(result.documents) == 1
        assert result.metadata["source"] == "legacy_chunks"
        assert "legacy_chunks" in result.statistics
    
    @pytest.mark.asyncio
    async def test_enhance_content(self, sample_document, sample_metadata):
        """컨텐츠 강화 테스트"""
        # Given
        builder = DocumentBuilder()
        
        # When
        enhanced_content = await builder._enhance_content(sample_document.text, sample_metadata)
        
        # Then
        assert "# Method: testMethod" in enhanced_content
        assert "File: test.java" in enhanced_content
        assert "Language: java" in enhanced_content
        assert "Lines: 10-20" in enhanced_content
        assert "Parent Class: TestClass" in enhanced_content
        assert "Parameters: param1: String" in enhanced_content
        assert "Returns: Integer" in enhanced_content
        assert "## Code:" in enhanced_content
        assert sample_document.text in enhanced_content
    
    @pytest.mark.asyncio
    async def test_extract_search_keywords(self, sample_document, sample_metadata):
        """검색 키워드 추출 테스트"""
        # Given
        builder = DocumentBuilder()
        
        # When
        keywords = await builder._extract_search_keywords(sample_document.text, sample_metadata)
        
        # Then
        assert "testMethod" in keywords
        assert "TestClass" in keywords
        assert "String" in keywords
        assert "Integer" in keywords
        assert "Override" in keywords
        assert "public" in keywords
        assert "static" in keywords
        assert len(keywords) > 0
    
    @pytest.mark.asyncio
    async def test_extract_keywords_from_java_content(self):
        """Java 코드에서 키워드 추출 테스트"""
        # Given
        builder = DocumentBuilder()
        java_code = """
        @Service
        public class UserService {
            private String name;
            public List<User> getUsers() {
                return new ArrayList<>();
            }
        }
        """
        
        # When
        keywords = await builder._extract_keywords_from_content(java_code, Language.JAVA)
        
        # Then
        assert "String" in keywords
        assert "List" in keywords
        assert "public" in keywords
        assert "private" in keywords
        assert "class" in keywords
        assert "@Service" in keywords
    
    @pytest.mark.asyncio
    async def test_extract_keywords_from_python_content(self):
        """Python 코드에서 키워드 추출 테스트"""
        # Given
        builder = DocumentBuilder()
        python_code = """
        import logging
        from typing import List
        
        @dataclass
        class DataProcessor:
            def process_data(self, data: List[str]) -> bool:
                return True
        """
        
        # When
        keywords = await builder._extract_keywords_from_content(python_code, Language.PYTHON)
        
        # Then
        assert "logging" in keywords
        assert "typing" in keywords
        assert "DataProcessor" in keywords
        assert "process_data" in keywords
        assert "dataclass" in keywords
    
    @pytest.mark.asyncio
    async def test_generate_semantic_tags(self, sample_metadata):
        """의미적 태그 생성 테스트"""
        # Given
        builder = DocumentBuilder()
        
        # When
        tags = await builder._generate_semantic_tags(sample_metadata)
        
        # Then
        assert "type:method" in tags
        assert "lang:java" in tags
        assert "access:public" in tags
        assert "scope:static" in tags
        assert len(tags) > 0
    
    @pytest.mark.asyncio
    async def test_generate_semantic_tags_for_test_method(self):
        """테스트 메서드에 대한 의미적 태그 생성 테스트"""
        # Given
        builder = DocumentBuilder()
        metadata = CodeMetadata(
            file_path="test.java",
            language=Language.JAVA,
            code_type=CodeType.METHOD,
            name="testSomething",
            line_start=1,
            line_end=10,
            modifiers=["public"]
        )
        
        # When
        tags = await builder._generate_semantic_tags(metadata)
        
        # Then
        assert "purpose:test" in tags
    
    @pytest.mark.asyncio
    async def test_generate_semantic_tags_for_getter(self):
        """Getter 메서드에 대한 의미적 태그 생성 테스트"""
        # Given
        builder = DocumentBuilder()
        metadata = CodeMetadata(
            file_path="test.java",
            language=Language.JAVA,
            code_type=CodeType.METHOD,
            name="getName",
            line_start=1,
            line_end=5,
            modifiers=["public"]
        )
        
        # When
        tags = await builder._generate_semantic_tags(metadata)
        
        # Then
        assert "purpose:getter" in tags
    
    @pytest.mark.asyncio
    async def test_analyze_relationships(self, sample_metadata):
        """관계 분석 테스트"""
        # Given
        builder = DocumentBuilder()
        
        # When
        relationships = await builder._analyze_relationships(sample_metadata)
        
        # Then
        assert relationships["parent"] == "TestClass"
        assert relationships["namespace"] == "com.example"
        assert "String" in relationships["dependencies"]
        assert "Integer" in relationships["dependencies"]
    
    def test_convert_legacy_chunk_to_metadata(self, sample_legacy_chunks):
        """기존 청크를 CodeMetadata로 변환 테스트"""
        # Given
        builder = DocumentBuilder()
        chunk = sample_legacy_chunks[0]
        
        # When
        metadata = builder._convert_legacy_chunk_to_metadata(chunk)
        
        # Then
        assert metadata.file_path == "legacy.java"
        assert metadata.language == Language.JAVA
        assert metadata.code_type == CodeType.METHOD
        assert metadata.name == "legacyMethod"
        assert metadata.parent_class == "LegacyClass"
        assert "public" in metadata.modifiers
    
    def test_generate_document_id(self, sample_metadata):
        """Document ID 생성 테스트"""
        # Given
        builder = DocumentBuilder()
        
        # When
        doc_id = builder._generate_document_id(sample_metadata)
        
        # Then
        assert isinstance(doc_id, str)
        assert len(doc_id) == 32  # MD5 해시 길이
        
        # 같은 메타데이터로 다시 생성하면 같은 ID가 나와야 함
        doc_id2 = builder._generate_document_id(sample_metadata)
        assert doc_id == doc_id2
    
    def test_update_statistics(self, sample_metadata):
        """통계 업데이트 테스트"""
        # Given
        builder = DocumentBuilder()
        statistics = {
            "classes": 0,
            "methods": 0,
            "functions": 0,
            "interfaces": 0,
            "total_lines": 0
        }
        
        # When
        builder._update_statistics(statistics, sample_metadata)
        
        # Then
        assert statistics["methods"] == 1
        assert statistics["total_lines"] == 11  # line_end - line_start + 1

class TestDocumentService:
    """Document Service 테스트"""
    
    @pytest.fixture
    def mock_embedding_client(self):
        """Mock 임베딩 클라이언트"""
        client = Mock()
        client.embed_bulk = AsyncMock(return_value={
            "embeddings": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]}
            ]
        })
        return client
    
    @pytest.fixture
    def sample_parse_result(self):
        """테스트용 ParseResult"""
        metadata = CodeMetadata(
            file_path="test.java",
            language=Language.JAVA,
            code_type=CodeType.METHOD,
            name="testMethod",
            line_start=1,
            line_end=10
        )
        
        document = Document(
            text="public void testMethod() {}",
            metadata=metadata.model_dump(),
            id_="test_id"
        )
        
        return ParseResult(
            documents=[document],
            nodes=[],
            metadata={"source": "test"},
            parse_time_ms=50
        )
    
    def test_document_service_initialization(self):
        """Document Service 초기화 테스트"""
        # Given & When
        service = DocumentService()
        
        # Then
        assert service.embedding_client is None
        assert service.builder is not None
    
    def test_document_service_with_embedding_client(self, mock_embedding_client):
        """임베딩 클라이언트와 함께 Document Service 초기화 테스트"""
        # Given & When
        service = DocumentService(mock_embedding_client)
        
        # Then
        assert service.embedding_client is not None
        assert service.builder is not None
    
    @pytest.mark.asyncio
    async def test_create_documents_from_parse_result(self, sample_parse_result):
        """파싱 결과로부터 Document 생성 테스트"""
        # Given
        service = DocumentService()
        
        # When
        result = await service.create_documents_from_parse_result(sample_parse_result)
        
        # Then
        assert isinstance(result, DocumentBuildResult)
        assert result.total_documents == 1
        assert len(result.documents) == 1
    
    @pytest.mark.asyncio
    async def test_create_documents_with_embedding_client(self, sample_parse_result, mock_embedding_client):
        """임베딩 클라이언트와 함께 Document 생성 테스트"""
        # Given
        service = DocumentService(mock_embedding_client)
        
        # When
        result = await service.create_documents_from_parse_result(sample_parse_result)
        
        # Then
        assert result.total_documents == 1
        mock_embedding_client.embed_bulk.assert_called_once()
        
        # 임베딩이 Document에 추가되었는지 확인
        enhanced_doc = result.documents[0]
        assert enhanced_doc.document.embedding is not None
        assert enhanced_doc.text_node.embedding is not None
    
    @pytest.mark.asyncio
    async def test_create_documents_from_legacy_chunks(self):
        """기존 청크로부터 Document 생성 테스트"""
        # Given
        service = DocumentService()
        chunks = [
            {
                "file_path": "legacy.java",
                "language": "java",
                "code_type": "method",
                "name": "legacyMethod",
                "line_start": 1,
                "line_end": 5,
                "code_content": "public void legacyMethod() {}"
            }
        ]
        
        # When
        result = await service.create_documents_from_legacy_chunks(chunks)
        
        # Then
        assert result.total_documents == 1
        assert result.metadata["source"] == "legacy_chunks"
    
    def test_update_config(self):
        """Document Builder 설정 업데이트 테스트"""
        # Given
        service = DocumentService()
        new_config = DocumentBuildConfig(
            chunking_strategy=ChunkingStrategy.CLASS_LEVEL,
            max_chunk_size=2048
        )
        
        # When
        service.update_config(new_config)
        
        # Then
        assert service.builder.config.chunking_strategy == ChunkingStrategy.CLASS_LEVEL
        assert service.builder.config.max_chunk_size == 2048
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, sample_parse_result):
        """통계 정보 반환 테스트"""
        # Given
        service = DocumentService()
        result = await service.create_documents_from_parse_result(sample_parse_result)
        
        # When
        stats = service.get_statistics(result)
        
        # Then
        assert "total_documents" in stats
        assert "build_time_ms" in stats
        assert "average_keywords_per_doc" in stats
        assert "average_tags_per_doc" in stats
        assert "languages" in stats
        assert "code_types" in stats
        assert stats["total_documents"] == 1
        assert "java" in stats["languages"]
        assert "method" in stats["code_types"] 