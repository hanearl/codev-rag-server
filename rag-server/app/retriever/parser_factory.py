from typing import Dict, Type, List
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
        """
        언어별 파서 생성
        
        Args:
            language: 대상 언어
            
        Returns:
            생성된 파서 인스턴스
            
        Raises:
            ValueError: 지원하지 않는 언어인 경우
        """
        if language not in cls._parsers:
            raise ValueError(f"Unsupported language: {language}")
        
        return cls._parsers[language]()
    
    @classmethod
    def create_parser_for_file(cls, file_path: str) -> BaseASTParser:
        """
        파일 확장자에 따른 파서 생성
        
        Args:
            file_path: 파일 경로
            
        Returns:
            생성된 파서 인스턴스
            
        Raises:
            ValueError: 지원하지 않는 파일 확장자인 경우
        """
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
        """
        새로운 파서 등록
        
        Args:
            language: 언어
            parser_class: 파서 클래스
        """
        cls._parsers[language] = parser_class
    
    @classmethod
    def get_supported_languages(cls) -> List[Language]:
        """
        지원되는 언어 목록
        
        Returns:
            지원 언어 리스트
        """
        return list(cls._parsers.keys())
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """
        지원되는 파일 확장자 목록
        
        Returns:
            지원 확장자 리스트
        """
        return ['java', 'py', 'js', 'ts']
    
    @classmethod
    def is_supported_file(cls, file_path: str) -> bool:
        """
        파일이 지원되는지 확인
        
        Args:
            file_path: 파일 경로
            
        Returns:
            지원 여부
        """
        extension = file_path.lower().split('.')[-1]
        return extension in cls.get_supported_extensions() 