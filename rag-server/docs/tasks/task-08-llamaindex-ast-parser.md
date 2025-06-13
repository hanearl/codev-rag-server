# Task 8: LlamaIndex 기반 AST 파서 구현

## 📋 작업 개요
기존의 분산된 코드 파싱 로직을 LlamaIndex의 Document 모델 기반으로 통합하고, 다양한 프로그래밍 언어를 지원하는 AST 파서를 구현합니다.

## 🎯 작업 목표
- LlamaIndex Document 모델을 활용한 통합된 코드 파싱 시스템 구축
- Java, Python, JavaScript AST 파서 구현
- 메서드/함수 단위의 세밀한 청킹 지원
- 주석, 메타데이터 추출 및 구조화

## 🔗 의존성
- **선행 Task**: Task 7 (하이브리드 아키텍처 기반 구조 생성)
- **활용할 기존 코드**: `app/features/indexing/parsers/` 모듈들

## 🔧 구현 사항

### 1. AST 파서 인터페이스

```python
# app/retriever/ast_parser.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from llama_index.core import Document
from llama_index.core.schema import TextNode
from pydantic import BaseModel
from enum import Enum

class CodeType(str, Enum):
    """코드 타입"""
    CLASS = "class"
    METHOD = "method"
    FUNCTION = "function"
    INTERFACE = "interface"
    CONSTRUCTOR = "constructor"
    FIELD = "field"
    VARIABLE = "variable"
    IMPORT = "import"
    MODULE = "module"

class Language(str, Enum):
    """지원 언어"""
    JAVA = "java"
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"

class CodeMetadata(BaseModel):
    """코드 메타데이터"""
    file_path: str
    language: Language
    code_type: CodeType
    name: str
    line_start: int
    line_end: int
    
    # 언어별 특성
    namespace: Optional[str] = None
    parent_class: Optional[str] = None
    modifiers: List[str] = []
    annotations: List[str] = []
    parameters: List[Dict[str, str]] = []
    return_type: Optional[str] = None
    
    # 상속/구현 관계
    extends: Optional[str] = None
    implements: List[str] = []
    
    # 추가 메타데이터
    comments: Optional[str] = None
    docstring: Optional[str] = None
    keywords: List[str] = []
    complexity_score: float = 0.0
    
    # 언어별 특화 데이터
    language_specific: Dict[str, Any] = {}

class ParseResult(BaseModel):
    """파싱 결과"""
    documents: List[Document]
    nodes: List[TextNode]
    metadata: Dict[str, Any]
    total_chunks: int
    parse_time_ms: int

class BaseASTParser(ABC):
    """기본 AST 파서 인터페이스"""
    
    def __init__(self, language: Language):
        self.language = language
    
    @abstractmethod
    async def parse_file(self, file_path: str) -> ParseResult:
        """파일 파싱"""
        pass
    
    @abstractmethod
    async def parse_content(self, content: str, file_path: str = "unknown") -> ParseResult:
        """문자열 콘텐츠 파싱"""
        pass
    
    @abstractmethod
    def extract_metadata(self, node: Any, file_path: str) -> CodeMetadata:
        """AST 노드에서 메타데이터 추출"""
        pass
    
    def create_document(self, content: str, metadata: CodeMetadata) -> Document:
        """Document 생성"""
        return Document(
            text=content,
            metadata=metadata.dict(),
            id_=f"{metadata.file_path}:{metadata.name}:{metadata.line_start}"
        )
    
    def create_text_node(self, content: str, metadata: CodeMetadata) -> TextNode:
        """TextNode 생성"""
        return TextNode(
            text=content,
            metadata=metadata.dict(),
            id_=f"{metadata.file_path}:{metadata.name}:{metadata.line_start}"
        )
```

### 2. Java AST 파서

```python
# app/retriever/java_ast_parser.py
import javalang
from typing import List, Dict, Any, Optional
from .ast_parser import BaseASTParser, ParseResult, CodeMetadata, CodeType, Language
from llama_index.core import Document
from llama_index.core.schema import TextNode
import time

class JavaASTParser(BaseASTParser):
    """Java AST 파서"""
    
    def __init__(self):
        super().__init__(Language.JAVA)
    
    async def parse_file(self, file_path: str) -> ParseResult:
        """Java 파일 파싱"""
        start_time = time.time()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        result = await self.parse_content(content, file_path)
        
        end_time = time.time()
        result.parse_time_ms = int((end_time - start_time) * 1000)
        
        return result
    
    async def parse_content(self, content: str, file_path: str = "unknown") -> ParseResult:
        """Java 코드 문자열 파싱"""
        documents = []
        nodes = []
        
        try:
            # Java 코드 파싱
            tree = javalang.parse.parse(content)
            lines = content.split('\n')
            
            # 클래스 추출
            for path, node in tree.filter(javalang.tree.ClassDeclaration):
                class_metadata = self._extract_class_metadata(node, file_path, lines)
                class_content = self._extract_code_content(lines, class_metadata.line_start, class_metadata.line_end)
                
                documents.append(self.create_document(class_content, class_metadata))
                nodes.append(self.create_text_node(class_content, class_metadata))
                
                # 메서드 추출
                for method in node.methods:
                    method_metadata = self._extract_method_metadata(method, file_path, lines, class_metadata.name)
                    method_content = self._extract_code_content(lines, method_metadata.line_start, method_metadata.line_end)
                    
                    documents.append(self.create_document(method_content, method_metadata))
                    nodes.append(self.create_text_node(method_content, method_metadata))
            
            # 인터페이스 추출
            for path, node in tree.filter(javalang.tree.InterfaceDeclaration):
                interface_metadata = self._extract_interface_metadata(node, file_path, lines)
                interface_content = self._extract_code_content(lines, interface_metadata.line_start, interface_metadata.line_end)
                
                documents.append(self.create_document(interface_content, interface_metadata))
                nodes.append(self.create_text_node(interface_content, interface_metadata))
            
        except javalang.parser.JavaSyntaxError as e:
            # 구문 오류 시 전체 파일을 하나의 문서로 처리
            metadata = CodeMetadata(
                file_path=file_path,
                language=Language.JAVA,
                code_type=CodeType.MODULE,
                name=file_path.split('/')[-1],
                line_start=1,
                line_end=len(content.split('\n')),
                comments=f"Parse error: {str(e)}"
            )
            documents.append(self.create_document(content, metadata))
            nodes.append(self.create_text_node(content, metadata))
        
        return ParseResult(
            documents=documents,
            nodes=nodes,
            metadata={"file_path": file_path, "language": "java"},
            total_chunks=len(documents),
            parse_time_ms=0  # 상위에서 설정
        )
    
    def extract_metadata(self, node: Any, file_path: str) -> CodeMetadata:
        """AST 노드에서 메타데이터 추출 (기본 구현)"""
        # 구체적인 노드 타입에 따라 적절한 메서드 호출
        if isinstance(node, javalang.tree.ClassDeclaration):
            return self._extract_class_metadata(node, file_path, [])
        elif isinstance(node, javalang.tree.MethodDeclaration):
            return self._extract_method_metadata(node, file_path, [])
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")
    
    def _extract_class_metadata(self, node: javalang.tree.ClassDeclaration, file_path: str, lines: List[str]) -> CodeMetadata:
        """클래스 메타데이터 추출"""
        # 위치 정보 (간략화된 구현)
        line_start, line_end = self._get_node_lines(node, lines)
        
        # 상속 관계
        extends = node.extends.name if node.extends else None
        implements = [impl.name for impl in node.implements] if node.implements else []
        
        # 어노테이션
        annotations = [ann.name for ann in node.annotations] if node.annotations else []
        
        # 수정자
        modifiers = list(node.modifiers) if node.modifiers else []
        
        return CodeMetadata(
            file_path=file_path,
            language=Language.JAVA,
            code_type=CodeType.CLASS,
            name=node.name,
            line_start=line_start,
            line_end=line_end,
            modifiers=modifiers,
            annotations=annotations,
            extends=extends,
            implements=implements,
            namespace=self._extract_package_name(file_path),
            keywords=self._extract_keywords_from_class(node)
        )
    
    def _extract_method_metadata(self, node: javalang.tree.MethodDeclaration, file_path: str, lines: List[str], parent_class: str = None) -> CodeMetadata:
        """메서드 메타데이터 추출"""
        line_start, line_end = self._get_node_lines(node, lines)
        
        # 파라미터 정보
        parameters = []
        if node.parameters:
            for param in node.parameters:
                parameters.append({
                    "name": param.name,
                    "type": str(param.type.name) if param.type else "unknown"
                })
        
        # 반환 타입
        return_type = str(node.return_type.name) if node.return_type else "void"
        
        # 어노테이션
        annotations = [ann.name for ann in node.annotations] if node.annotations else []
        
        # 수정자
        modifiers = list(node.modifiers) if node.modifiers else []
        
        return CodeMetadata(
            file_path=file_path,
            language=Language.JAVA,
            code_type=CodeType.METHOD,
            name=node.name,
            line_start=line_start,
            line_end=line_end,
            parent_class=parent_class,
            modifiers=modifiers,
            annotations=annotations,
            parameters=parameters,
            return_type=return_type,
            namespace=self._extract_package_name(file_path),
            keywords=self._extract_keywords_from_method(node)
        )
    
    def _extract_interface_metadata(self, node: javalang.tree.InterfaceDeclaration, file_path: str, lines: List[str]) -> CodeMetadata:
        """인터페이스 메타데이터 추출"""
        line_start, line_end = self._get_node_lines(node, lines)
        
        # 확장 인터페이스
        extends_list = [ext.name for ext in node.extends] if node.extends else []
        
        return CodeMetadata(
            file_path=file_path,
            language=Language.JAVA,
            code_type=CodeType.INTERFACE,
            name=node.name,
            line_start=line_start,
            line_end=line_end,
            implements=extends_list,
            namespace=self._extract_package_name(file_path),
            keywords=self._extract_keywords_from_interface(node)
        )
    
    def _get_node_lines(self, node: Any, lines: List[str]) -> tuple:
        """노드의 시작/끝 라인 추출 (간략화된 구현)"""
        # 실제 구현에서는 더 정교한 라인 추출 로직 필요
        return getattr(node, 'position', (1, 1))[0], getattr(node, 'position', (1, 1))[0] + 10
    
    def _extract_code_content(self, lines: List[str], start: int, end: int) -> str:
        """지정된 라인 범위의 코드 추출"""
        return '\n'.join(lines[start-1:end])
    
    def _extract_package_name(self, file_path: str) -> str:
        """파일 경로에서 패키지명 추출"""
        # 간략화된 구현
        return file_path.replace('/', '.').replace('.java', '')
    
    def _extract_keywords_from_class(self, node: javalang.tree.ClassDeclaration) -> List[str]:
        """클래스에서 키워드 추출"""
        keywords = [node.name]
        if node.extends:
            keywords.append(node.extends.name)
        if node.implements:
            keywords.extend([impl.name for impl in node.implements])
        return keywords
    
    def _extract_keywords_from_method(self, node: javalang.tree.MethodDeclaration) -> List[str]:
        """메서드에서 키워드 추출"""
        keywords = [node.name]
        if node.return_type:
            keywords.append(str(node.return_type.name))
        return keywords
    
    def _extract_keywords_from_interface(self, node: javalang.tree.InterfaceDeclaration) -> List[str]:
        """인터페이스에서 키워드 추출"""
        keywords = [node.name]
        if node.extends:
            keywords.extend([ext.name for ext in node.extends])
        return keywords
```

### 3. Python AST 파서

```python
# app/retriever/python_ast_parser.py
import ast
from typing import List, Dict, Any, Optional
from .ast_parser import BaseASTParser, ParseResult, CodeMetadata, CodeType, Language
from llama_index.core import Document
from llama_index.core.schema import TextNode
import time

class PythonASTParser(BaseASTParser):
    """Python AST 파서"""
    
    def __init__(self):
        super().__init__(Language.PYTHON)
    
    async def parse_file(self, file_path: str) -> ParseResult:
        """Python 파일 파싱"""
        start_time = time.time()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        result = await self.parse_content(content, file_path)
        
        end_time = time.time()
        result.parse_time_ms = int((end_time - start_time) * 1000)
        
        return result
    
    async def parse_content(self, content: str, file_path: str = "unknown") -> ParseResult:
        """Python 코드 문자열 파싱"""
        documents = []
        nodes = []
        
        try:
            tree = ast.parse(content)
            lines = content.split('\n')
            
            # 클래스 추출
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_metadata = self._extract_class_metadata(node, file_path, lines)
                    class_content = self._extract_code_content(lines, class_metadata.line_start, class_metadata.line_end)
                    
                    documents.append(self.create_document(class_content, class_metadata))
                    nodes.append(self.create_text_node(class_content, class_metadata))
                    
                    # 메서드 추출
                    for method_node in node.body:
                        if isinstance(method_node, ast.FunctionDef):
                            method_metadata = self._extract_method_metadata(method_node, file_path, lines, class_metadata.name)
                            method_content = self._extract_code_content(lines, method_metadata.line_start, method_metadata.line_end)
                            
                            documents.append(self.create_document(method_content, method_metadata))
                            nodes.append(self.create_text_node(method_content, method_metadata))
                
                # 최상위 함수 추출
                elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                    func_metadata = self._extract_function_metadata(node, file_path, lines)
                    func_content = self._extract_code_content(lines, func_metadata.line_start, func_metadata.line_end)
                    
                    documents.append(self.create_document(func_content, func_metadata))
                    nodes.append(self.create_text_node(func_content, func_metadata))
                    
        except SyntaxError as e:
            # 구문 오류 시 전체 파일을 하나의 문서로 처리
            metadata = CodeMetadata(
                file_path=file_path,
                language=Language.PYTHON,
                code_type=CodeType.MODULE,
                name=file_path.split('/')[-1],
                line_start=1,
                line_end=len(content.split('\n')),
                comments=f"Parse error: {str(e)}"
            )
            documents.append(self.create_document(content, metadata))
            nodes.append(self.create_text_node(content, metadata))
        
        return ParseResult(
            documents=documents,
            nodes=nodes,
            metadata={"file_path": file_path, "language": "python"},
            total_chunks=len(documents),
            parse_time_ms=0
        )
    
    def extract_metadata(self, node: Any, file_path: str) -> CodeMetadata:
        """AST 노드에서 메타데이터 추출"""
        if isinstance(node, ast.ClassDef):
            return self._extract_class_metadata(node, file_path, [])
        elif isinstance(node, ast.FunctionDef):
            return self._extract_function_metadata(node, file_path, [])
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")
    
    def _extract_class_metadata(self, node: ast.ClassDef, file_path: str, lines: List[str]) -> CodeMetadata:
        """클래스 메타데이터 추출"""
        # 상속 관계
        bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
        
        # 데코레이터
        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]
        
        # 독스트링
        docstring = ast.get_docstring(node)
        
        return CodeMetadata(
            file_path=file_path,
            language=Language.PYTHON,
            code_type=CodeType.CLASS,
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            implements=bases,  # Python에서는 상속을 implements로 표현
            annotations=decorators,
            docstring=docstring,
            keywords=[node.name] + bases
        )
    
    def _extract_method_metadata(self, node: ast.FunctionDef, file_path: str, lines: List[str], parent_class: str = None) -> CodeMetadata:
        """메서드 메타데이터 추출"""
        # 파라미터 정보
        parameters = []
        for arg in node.args.args:
            param_info = {"name": arg.arg}
            if arg.annotation:
                param_info["type"] = ast.unparse(arg.annotation)
            parameters.append(param_info)
        
        # 반환 타입
        return_type = ast.unparse(node.returns) if node.returns else None
        
        # 데코레이터
        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]
        
        # 독스트링
        docstring = ast.get_docstring(node)
        
        return CodeMetadata(
            file_path=file_path,
            language=Language.PYTHON,
            code_type=CodeType.METHOD,
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            parent_class=parent_class,
            parameters=parameters,
            return_type=return_type,
            annotations=decorators,
            docstring=docstring,
            keywords=[node.name]
        )
    
    def _extract_function_metadata(self, node: ast.FunctionDef, file_path: str, lines: List[str]) -> CodeMetadata:
        """함수 메타데이터 추출"""
        return self._extract_method_metadata(node, file_path, lines)
    
    def _get_decorator_name(self, decorator) -> str:
        """데코레이터 이름 추출"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return ast.unparse(decorator)
        else:
            return str(decorator)
    
    def _extract_code_content(self, lines: List[str], start: int, end: int) -> str:
        """지정된 라인 범위의 코드 추출"""
        return '\n'.join(lines[start-1:end])
```

### 4. AST 파서 팩토리

```python
# app/retriever/parser_factory.py
from typing import Dict, Type
from .ast_parser import BaseASTParser, Language
from .java_ast_parser import JavaASTParser
from .python_ast_parser import PythonASTParser

class ASTParserFactory:
    """AST 파서 팩토리"""
    
    _parsers: Dict[Language, Type[BaseASTParser]] = {
        Language.JAVA: JavaASTParser,
        Language.PYTHON: PythonASTParser,
    }
    
    @classmethod
    def create_parser(cls, language: Language) -> BaseASTParser:
        """언어별 파서 생성"""
        if language not in cls._parsers:
            raise ValueError(f"Unsupported language: {language}")
        
        return cls._parsers[language]()
    
    @classmethod
    def create_parser_for_file(cls, file_path: str) -> BaseASTParser:
        """파일 확장자에 따른 파서 생성"""
        extension = file_path.lower().split('.')[-1]
        
        extension_mapping = {
            'java': Language.JAVA,
            'py': Language.PYTHON,
            'js': Language.JAVASCRIPT,
            'ts': Language.TYPESCRIPT,
        }
        
        if extension not in extension_mapping:
            raise ValueError(f"Unsupported file extension: {extension}")
        
        language = extension_mapping[extension]
        return cls.create_parser(language)
    
    @classmethod
    def register_parser(cls, language: Language, parser_class: Type[BaseASTParser]):
        """새로운 파서 등록"""
        cls._parsers[language] = parser_class
    
    @classmethod
    def get_supported_languages(cls) -> List[Language]:
        """지원되는 언어 목록"""
        return list(cls._parsers.keys())
```

## ✅ 완료 조건

1. **기본 인터페이스 구현**: `BaseASTParser` 및 관련 모델들이 완전히 구현됨
2. **Java 파서 구현**: Java 클래스, 메서드, 인터페이스 파싱이 정상 동작
3. **Python 파서 구현**: Python 클래스, 함수 파싱이 정상 동작
4. **팩토리 패턴 구현**: 언어별 파서 생성이 자동화됨
5. **LlamaIndex 통합**: Document와 TextNode 생성이 정상 동작
6. **메타데이터 추출**: 모든 필요한 메타데이터가 정확히 추출됨
7. **테스트 통과**: 단위 테스트 및 통합 테스트 모두 통과

## 📋 다음 Task와의 연관관계

- **Task 9**: 이 Task에서 생성한 Document들을 활용하여 Document Builder 구현
- **Task 10-12**: 생성된 Document들을 각각의 인덱스에 저장

## 🧪 테스트 계획

```python
# tests/unit/retriever/test_ast_parser.py
async def test_java_parser_parse_class():
    """Java 클래스 파싱 테스트"""
    parser = JavaASTParser()
    result = await parser.parse_content(sample_java_code)
    assert len(result.documents) > 0
    assert result.total_chunks > 0

async def test_python_parser_parse_function():
    """Python 함수 파싱 테스트"""
    parser = PythonASTParser()
    result = await parser.parse_content(sample_python_code)
    assert len(result.documents) > 0

def test_parser_factory_create_by_extension():
    """파일 확장자별 파서 생성 테스트"""
    java_parser = ASTParserFactory.create_parser_for_file("Test.java")
    assert isinstance(java_parser, JavaASTParser)
    
    python_parser = ASTParserFactory.create_parser_for_file("test.py")
    assert isinstance(python_parser, PythonASTParser)
```

이 Task는 전체 하이브리드 아키텍처에서 문서 생성의 핵심이 되는 중요한 작업입니다. 정확하고 풍부한 메타데이터를 포함한 Document 생성이 후속 검색 품질에 직접적인 영향을 미칩니다. 