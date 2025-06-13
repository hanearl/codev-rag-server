"""
AST 파서 테스트
"""
import pytest
from unittest.mock import Mock, patch
from typing import List

from app.retriever.ast_parser import (
    BaseASTParser, CodeMetadata, CodeType, Language, ParseResult
)
from app.retriever.java_ast_parser import JavaASTParser
from app.retriever.python_ast_parser import PythonASTParser
from app.retriever.parser_factory import ASTParserFactory


class TestCodeMetadata:
    """CodeMetadata 모델 테스트"""
    
    def test_code_metadata_creation(self):
        """CodeMetadata 생성 테스트"""
        metadata = CodeMetadata(
            file_path="test.py",
            language=Language.PYTHON,
            code_type=CodeType.CLASS,
            name="TestClass",
            line_start=1,
            line_end=10
        )
        
        assert metadata.file_path == "test.py"
        assert metadata.language == Language.PYTHON
        assert metadata.code_type == CodeType.CLASS
        assert metadata.name == "TestClass"
        assert metadata.line_start == 1
        assert metadata.line_end == 10
    
    def test_code_metadata_with_optional_fields(self):
        """선택적 필드가 포함된 CodeMetadata 테스트"""
        metadata = CodeMetadata(
            file_path="test.java",
            language=Language.JAVA,
            code_type=CodeType.METHOD,
            name="testMethod",
            line_start=5,
            line_end=15,
            parent_class="TestClass",
            modifiers=["public", "static"],
            parameters=[{"name": "param1", "type": "String"}],
            return_type="void"
        )
        
        assert metadata.parent_class == "TestClass"
        assert metadata.modifiers == ["public", "static"]
        assert metadata.parameters == [{"name": "param1", "type": "String"}]
        assert metadata.return_type == "void"


class TestParseResult:
    """ParseResult 모델 테스트"""
    
    def test_parse_result_creation(self):
        """ParseResult 생성 테스트"""
        result = ParseResult(
            documents=[],
            nodes=[],
            metadata={"test": "value"},
            total_chunks=0,
            parse_time_ms=100
        )
        
        assert result.documents == []
        assert result.nodes == []
        assert result.metadata == {"test": "value"}
        assert result.total_chunks == 0
        assert result.parse_time_ms == 100


class TestBaseASTParser:
    """BaseASTParser 추상 클래스 테스트"""
    
    def test_base_ast_parser_is_abstract(self):
        """BaseASTParser가 추상 클래스인지 테스트"""
        with pytest.raises(TypeError):
            BaseASTParser(Language.PYTHON)
    
    def test_create_document(self):
        """Document 생성 메서드 테스트"""
        # Mock 파서 생성
        class MockParser(BaseASTParser):
            async def parse_file(self, file_path: str):
                pass
            async def parse_content(self, content: str, file_path: str = "unknown"):
                pass
            def extract_metadata(self, node, file_path: str):
                pass
        
        parser = MockParser(Language.PYTHON)
        metadata = CodeMetadata(
            file_path="test.py",
            language=Language.PYTHON,
            code_type=CodeType.FUNCTION,
            name="test_func",
            line_start=1,
            line_end=5
        )
        
        doc = parser.create_document("test content", metadata)
        
        assert doc.text == "test content"
        assert doc.metadata == metadata.dict()
        assert doc.id_ == "test.py:test_func:1"
    
    def test_create_text_node(self):
        """TextNode 생성 메서드 테스트"""
        # Mock 파서 생성
        class MockParser(BaseASTParser):
            async def parse_file(self, file_path: str):
                pass
            async def parse_content(self, content: str, file_path: str = "unknown"):
                pass
            def extract_metadata(self, node, file_path: str):
                pass
        
        parser = MockParser(Language.PYTHON)
        metadata = CodeMetadata(
            file_path="test.py",
            language=Language.PYTHON,
            code_type=CodeType.FUNCTION,
            name="test_func",
            line_start=1,
            line_end=5
        )
        
        node = parser.create_text_node("test content", metadata)
        
        assert node.text == "test content"
        assert node.metadata == metadata.dict()
        assert node.id_ == "test.py:test_func:1"


class TestPythonASTParser:
    """Python AST 파서 테스트"""
    
    def test_python_parser_initialization(self):
        """Python 파서 초기화 테스트"""
        parser = PythonASTParser()
        assert parser.language == Language.PYTHON
    
    @pytest.mark.asyncio
    async def test_parse_simple_function(self):
        """간단한 함수 파싱 테스트"""
        parser = PythonASTParser()
        
        python_code = '''
def hello_world():
    """Simple hello world function"""
    return "Hello, World!"
'''
        
        result = await parser.parse_content(python_code, "test.py")
        
        assert isinstance(result, ParseResult)
        assert len(result.documents) > 0
        assert len(result.nodes) > 0
        assert result.total_chunks > 0
        assert result.metadata["language"] == "python"
        
        # 첫 번째 문서가 함수여야 함
        first_doc = result.documents[0]
        assert "hello_world" in first_doc.metadata["name"]
        assert first_doc.metadata["code_type"] == CodeType.FUNCTION
    
    @pytest.mark.asyncio
    async def test_parse_class_with_methods(self):
        """클래스와 메서드 파싱 테스트"""
        parser = PythonASTParser()
        
        python_code = '''
class Calculator:
    """A simple calculator class"""
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers"""
        return a + b
    
    def subtract(self, a: int, b: int) -> int:
        """Subtract two numbers"""
        return a - b
'''
        
        result = await parser.parse_content(python_code, "calculator.py")
        
        assert len(result.documents) >= 3  # 클래스 + 2개 메서드
        
        # 클래스 문서 확인
        class_docs = [doc for doc in result.documents if doc.metadata["code_type"] == CodeType.CLASS]
        assert len(class_docs) == 1
        assert class_docs[0].metadata["name"] == "Calculator"
        
        # 메서드 문서 확인
        method_docs = [doc for doc in result.documents if doc.metadata["code_type"] == CodeType.METHOD]
        assert len(method_docs) == 2
        method_names = [doc.metadata["name"] for doc in method_docs]
        assert "add" in method_names
        assert "subtract" in method_names
    
    @pytest.mark.asyncio
    async def test_parse_syntax_error(self):
        """구문 오류가 있는 코드 파싱 테스트"""
        parser = PythonASTParser()
        
        # 잘못된 Python 코드
        invalid_code = '''
def incomplete_function(
    # 문법 오류 - 닫는 괄호 없음
'''
        
        result = await parser.parse_content(invalid_code, "invalid.py")
        
        # 구문 오류 시에도 결과가 반환되어야 함 (전체 파일을 하나의 문서로)
        assert len(result.documents) == 1
        assert result.documents[0].metadata["code_type"] == CodeType.MODULE
        assert "Parse error" in result.documents[0].metadata["comments"]


class TestJavaASTParser:
    """Java AST 파서 테스트"""
    
    def test_java_parser_initialization(self):
        """Java 파서 초기화 테스트"""
        parser = JavaASTParser()
        assert parser.language == Language.JAVA
    
    @pytest.mark.asyncio
    async def test_parse_simple_class(self):
        """간단한 Java 클래스 파싱 테스트"""
        parser = JavaASTParser()
        
        java_code = '''
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
'''
        
        result = await parser.parse_content(java_code, "HelloWorld.java")
        
        assert isinstance(result, ParseResult)
        assert len(result.documents) > 0
        assert result.metadata["language"] == "java"
        
        # 클래스 문서 확인
        class_docs = [doc for doc in result.documents if doc.metadata["code_type"] == CodeType.CLASS]
        assert len(class_docs) >= 1
        assert class_docs[0].metadata["name"] == "HelloWorld"
    
    @pytest.mark.asyncio
    async def test_parse_syntax_error(self):
        """Java 구문 오류 파싱 테스트"""
        parser = JavaASTParser()
        
        # 잘못된 Java 코드
        invalid_code = '''
public class InvalidClass {
    // 닫는 중괄호 없음
'''
        
        result = await parser.parse_content(invalid_code, "Invalid.java")
        
        # 구문 오류 시에도 결과가 반환되어야 함
        assert len(result.documents) == 1
        assert result.documents[0].metadata["code_type"] == CodeType.MODULE
        assert "Parse error" in result.documents[0].metadata["comments"]


class TestASTParserFactory:
    """AST 파서 팩토리 테스트"""
    
    def test_create_java_parser(self):
        """Java 파서 생성 테스트"""
        parser = ASTParserFactory.create_parser(Language.JAVA)
        assert isinstance(parser, JavaASTParser)
        assert parser.language == Language.JAVA
    
    def test_create_python_parser(self):
        """Python 파서 생성 테스트"""
        parser = ASTParserFactory.create_parser(Language.PYTHON)
        assert isinstance(parser, PythonASTParser)
        assert parser.language == Language.PYTHON
    
    def test_create_unsupported_parser(self):
        """지원하지 않는 언어 파서 생성 테스트"""
        with pytest.raises(ValueError, match="Unsupported language"):
            ASTParserFactory.create_parser(Language.JAVASCRIPT)
    
    def test_create_parser_for_java_file(self):
        """Java 파일용 파서 생성 테스트"""
        parser = ASTParserFactory.create_parser_for_file("Test.java")
        assert isinstance(parser, JavaASTParser)
    
    def test_create_parser_for_python_file(self):
        """Python 파일용 파서 생성 테스트"""
        parser = ASTParserFactory.create_parser_for_file("test.py")
        assert isinstance(parser, PythonASTParser)
    
    def test_create_parser_for_unsupported_file(self):
        """지원하지 않는 파일 확장자 테스트"""
        with pytest.raises(ValueError, match="Unsupported file extension"):
            ASTParserFactory.create_parser_for_file("test.cpp")
    
    def test_get_supported_languages(self):
        """지원 언어 목록 테스트"""
        languages = ASTParserFactory.get_supported_languages()
        assert Language.JAVA in languages
        assert Language.PYTHON in languages
        assert len(languages) >= 2
    
    def test_get_supported_extensions(self):
        """지원 확장자 목록 테스트"""
        extensions = ASTParserFactory.get_supported_extensions()
        assert 'java' in extensions
        assert 'py' in extensions
        assert len(extensions) >= 2
    
    def test_is_supported_file(self):
        """파일 지원 여부 테스트"""
        assert ASTParserFactory.is_supported_file("Test.java") is True
        assert ASTParserFactory.is_supported_file("test.py") is True
        assert ASTParserFactory.is_supported_file("test.cpp") is False
        assert ASTParserFactory.is_supported_file("readme.txt") is False
    
    def test_register_new_parser(self):
        """새 파서 등록 테스트"""
        # Mock 파서 클래스
        class MockJSParser(BaseASTParser):
            def __init__(self):
                super().__init__(Language.JAVASCRIPT)
            async def parse_file(self, file_path: str):
                pass
            async def parse_content(self, content: str, file_path: str = "unknown"):
                pass
            def extract_metadata(self, node, file_path: str):
                pass
        
        # 파서 등록
        ASTParserFactory.register_parser(Language.JAVASCRIPT, MockJSParser)
        
        # 등록된 파서 사용
        parser = ASTParserFactory.create_parser(Language.JAVASCRIPT)
        assert isinstance(parser, MockJSParser)
        assert parser.language == Language.JAVASCRIPT 