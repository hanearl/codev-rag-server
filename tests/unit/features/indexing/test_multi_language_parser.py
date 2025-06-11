"""다중 언어 파서 통합 테스트

팩토리 패턴과 여러 언어 파서들의 통합 테스트를 수행합니다.
"""

import pytest
from app.features.indexing import (
    CodeParserFactory, 
    LanguageType, 
    CodeType,
    KeywordExtractor
)


class TestMultiLanguageParser:
    """다중 언어 파서 통합 테스트"""
    
    def test_supported_languages(self):
        """지원하는 언어 목록 확인"""
        supported_languages = CodeParserFactory.get_supported_languages()
        
        assert LanguageType.PYTHON in supported_languages
        assert LanguageType.JAVA in supported_languages
        assert LanguageType.JAVASCRIPT in supported_languages
        assert len(supported_languages) == 3
    
    def test_supported_extensions(self):
        """지원하는 파일 확장자 확인"""
        extensions = CodeParserFactory.get_supported_extensions()
        
        expected_extensions = ['.py', '.pyw', '.java', '.js', '.mjs', '.jsx']
        for ext in expected_extensions:
            assert ext in extensions
    
    def test_language_detection(self):
        """파일 확장자로 언어 감지 테스트"""
        # Python
        assert CodeParserFactory.detect_language('test.py') == LanguageType.PYTHON
        assert CodeParserFactory.detect_language('test.pyw') == LanguageType.PYTHON
        
        # Java
        assert CodeParserFactory.detect_language('Test.java') == LanguageType.JAVA
        
        # JavaScript
        assert CodeParserFactory.detect_language('test.js') == LanguageType.JAVASCRIPT
        assert CodeParserFactory.detect_language('test.mjs') == LanguageType.JAVASCRIPT
        assert CodeParserFactory.detect_language('test.jsx') == LanguageType.JAVASCRIPT
        
        # 지원하지 않는 확장자
        assert CodeParserFactory.detect_language('test.cpp') is None
        assert CodeParserFactory.detect_language('test.rs') is None
    
    def test_parser_creation_by_language(self):
        """언어별 파서 생성 테스트"""
        keyword_extractor = KeywordExtractor()
        
        # Python 파서
        python_parser = CodeParserFactory.create_parser(LanguageType.PYTHON, keyword_extractor)
        assert python_parser is not None
        assert python_parser.language == LanguageType.PYTHON
        assert '.py' in python_parser.supported_extensions
        
        # Java 파서
        java_parser = CodeParserFactory.create_parser(LanguageType.JAVA, keyword_extractor)
        assert java_parser is not None
        assert java_parser.language == LanguageType.JAVA
        assert '.java' in java_parser.supported_extensions
        
        # JavaScript 파서
        js_parser = CodeParserFactory.create_parser(LanguageType.JAVASCRIPT, keyword_extractor)
        assert js_parser is not None
        assert js_parser.language == LanguageType.JAVASCRIPT
        assert '.js' in js_parser.supported_extensions
    
    def test_parser_creation_by_file(self):
        """파일 경로로 파서 생성 테스트"""
        keyword_extractor = KeywordExtractor()
        
        # Python 파일
        python_parser = CodeParserFactory.create_parser_for_file('test.py', keyword_extractor)
        assert python_parser is not None
        assert python_parser.language == LanguageType.PYTHON
        
        # Java 파일
        java_parser = CodeParserFactory.create_parser_for_file('Test.java', keyword_extractor)
        assert java_parser is not None
        assert java_parser.language == LanguageType.JAVA
        
        # JavaScript 파일
        js_parser = CodeParserFactory.create_parser_for_file('test.js', keyword_extractor)
        assert js_parser is not None
        assert js_parser.language == LanguageType.JAVASCRIPT
        
        # 지원하지 않는 파일
        unsupported_parser = CodeParserFactory.create_parser_for_file('test.cpp', keyword_extractor)
        assert unsupported_parser is None
    
    def test_file_support_check(self):
        """파일 지원 여부 확인 테스트"""
        assert CodeParserFactory.is_supported_file('test.py') is True
        assert CodeParserFactory.is_supported_file('Test.java') is True
        assert CodeParserFactory.is_supported_file('test.js') is True
        assert CodeParserFactory.is_supported_file('test.cpp') is False
        assert CodeParserFactory.is_supported_file('test.rs') is False


class TestPythonParser:
    """Python 파서 세부 테스트"""
    
    def test_python_function_parsing(self):
        """Python 함수 파싱 테스트"""
        code = '''
def hello_world():
    """Hello world function"""
    print("Hello, World!")
    return "success"

async def async_function():
    await some_operation()
    return "done"
'''
        
        parser = CodeParserFactory.create_parser(LanguageType.PYTHON)
        result = parser.parse_code(code)
        chunks = result.chunks
        
        assert len(chunks) == 2
        
        # 일반 함수
        func_chunk = chunks[0]
        assert func_chunk.name == "hello_world"
        assert func_chunk.code_type == CodeType.FUNCTION
        assert func_chunk.language == LanguageType.PYTHON
        assert func_chunk.line_start == 2
        assert "hello" in func_chunk.keywords
        
        # async 함수
        async_chunk = chunks[1]
        assert async_chunk.name == "async_function"
        assert async_chunk.language_specific["is_async"] is True


class TestJavaParser:
    """Java 파서 세부 테스트"""
    
    def test_java_class_parsing(self):
        """Java 클래스 파싱 테스트"""
        code = '''
package com.example;

public class HelloWorld {
    private String message;
    
    public HelloWorld(String message) {
        this.message = message;
    }
    
    public void sayHello() {
        System.out.println(message);
    }
}
'''
        
        parser = CodeParserFactory.create_parser(LanguageType.JAVA)
        result = parser.parse_code(code)
        chunks = result.chunks
        
        # 클래스 + 생성자 + 메소드 = 3개
        assert len(chunks) == 3
        
        # 클래스 청크
        class_chunk = next(chunk for chunk in chunks if chunk.code_type == CodeType.CLASS)
        assert class_chunk.name == "HelloWorld"
        assert class_chunk.namespace == "com.example"
        assert "public" in class_chunk.modifiers
        
        # 메소드 청크
        method_chunks = [chunk for chunk in chunks if chunk.code_type == CodeType.METHOD]
        assert len(method_chunks) == 2  # 생성자 + sayHello 메소드


class TestJavaScriptParser:
    """JavaScript 파서 세부 테스트"""
    
    def test_javascript_function_parsing(self):
        """JavaScript 함수 파싱 테스트"""
        code = '''
function greet(name) {
    console.log(`Hello, ${name}!`);
}

const arrowFunc = (x, y) => {
    return x + y;
};

class Calculator {
    constructor() {
        this.result = 0;
    }
    
    add(value) {
        this.result += value;
        return this;
    }
}
'''
        
        parser = CodeParserFactory.create_parser(LanguageType.JAVASCRIPT)
        result = parser.parse_code(code)
        chunks = result.chunks
        
        assert len(chunks) >= 4  # 함수 + 화살표함수 + 클래스 + 메소드들
        
        # 함수 선언
        func_chunks = [chunk for chunk in chunks if chunk.name == "greet"]
        assert len(func_chunks) == 1
        assert func_chunks[0].code_type == CodeType.FUNCTION
        
        # 클래스
        class_chunks = [chunk for chunk in chunks if chunk.code_type == CodeType.CLASS]
        assert len(class_chunks) == 1
        assert class_chunks[0].name == "Calculator"


class TestCrossLanguageConsistency:
    """언어간 일관성 테스트"""
    
    def test_schema_consistency(self):
        """모든 파서가 동일한 스키마를 반환하는지 확인"""
        python_code = "def test(): pass"
        java_code = "public class Test { public void test() {} }"
        js_code = "function test() {}"
        
        python_parser = CodeParserFactory.create_parser(LanguageType.PYTHON)
        java_parser = CodeParserFactory.create_parser(LanguageType.JAVA)
        js_parser = CodeParserFactory.create_parser(LanguageType.JAVASCRIPT)
        
        python_result = python_parser.parse_code(python_code)
        java_result = java_parser.parse_code(java_code)
        js_result = js_parser.parse_code(js_code)
        
        # 모든 청크가 필수 필드를 가지고 있는지 확인
        all_chunks = python_result.chunks + java_result.chunks + js_result.chunks
        for chunk in all_chunks:
            assert hasattr(chunk, 'name')
            assert hasattr(chunk, 'code_content')
            assert hasattr(chunk, 'code_type')
            assert hasattr(chunk, 'language')
            assert hasattr(chunk, 'file_path')
            assert hasattr(chunk, 'line_start')
            assert hasattr(chunk, 'line_end')
            assert hasattr(chunk, 'keywords')
            assert isinstance(chunk.keywords, list)
    
    def test_error_handling_consistency(self):
        """모든 파서가 일관된 오류 처리를 하는지 확인"""
        invalid_code = "this is not valid code in any language"
        
        python_parser = CodeParserFactory.create_parser(LanguageType.PYTHON)
        java_parser = CodeParserFactory.create_parser(LanguageType.JAVA)
        js_parser = CodeParserFactory.create_parser(LanguageType.JAVASCRIPT)
        
        # Python과 JavaScript는 SyntaxError를 발생시킴
        with pytest.raises(SyntaxError):
            python_parser.parse_code(invalid_code)
        
        with pytest.raises(SyntaxError):
            js_parser.parse_code(invalid_code)
        
        # Java는 오류를 errors 배열에 저장
        java_result = java_parser.parse_code(invalid_code)
        assert len(java_result.errors) > 0
        assert java_result.chunks == []
    
    def test_empty_code_handling(self):
        """빈 코드 처리 일관성 확인"""
        empty_codes = ["", "   ", "\n\n", "\t\t"]
        
        for lang in [LanguageType.PYTHON, LanguageType.JAVA, LanguageType.JAVASCRIPT]:
            parser = CodeParserFactory.create_parser(lang)
            for empty_code in empty_codes:
                result = parser.parse_code(empty_code)
                assert result.chunks == [] 