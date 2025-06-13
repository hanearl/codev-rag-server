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
        """
        파일 파싱
        
        Args:
            file_path: 파싱할 파일 경로
            
        Returns:
            파싱 결과
        """
        pass
    
    @abstractmethod
    async def parse_content(self, content: str, file_path: str = "unknown") -> ParseResult:
        """
        문자열 콘텐츠 파싱
        
        Args:
            content: 파싱할 코드 문자열
            file_path: 파일 경로 (선택)
            
        Returns:
            파싱 결과
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, node: Any, file_path: str) -> CodeMetadata:
        """
        AST 노드에서 메타데이터 추출
        
        Args:
            node: AST 노드
            file_path: 파일 경로
            
        Returns:
            추출된 메타데이터
        """
        pass
    
    def create_document(self, content: str, metadata: CodeMetadata) -> Document:
        """
        Document 생성
        
        Args:
            content: 문서 내용
            metadata: 메타데이터
            
        Returns:
            생성된 Document
        """
        return Document(
            text=content,
            metadata=metadata.dict(),  # Pydantic V1 복원
            id_=f"{metadata.file_path}:{metadata.name}:{metadata.line_start}"
        )
    
    def create_text_node(self, content: str, metadata: CodeMetadata) -> TextNode:
        """
        TextNode 생성
        
        Args:
            content: 노드 내용
            metadata: 메타데이터
            
        Returns:
            생성된 TextNode
        """
        return TextNode(
            text=content,
            metadata=metadata.dict(),  # Pydantic V1 복원
            id_=f"{metadata.file_path}:{metadata.name}:{metadata.line_start}"
        ) 