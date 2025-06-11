"""코드 파서 팩토리

파일 확장자나 언어 타입에 따라 적절한 파서를 생성하고 관리합니다.
"""

import os
from typing import Dict, List, Optional, Type
from .base_parser import BaseCodeParser
from .schemas import LanguageType


class ParserRegistry:
    """파서 등록 및 관리 클래스"""
    
    def __init__(self):
        self._parsers: Dict[LanguageType, Type[BaseCodeParser]] = {}
        self._extension_mapping: Dict[str, LanguageType] = {}
    
    def register_parser(self, parser_class: Type[BaseCodeParser]) -> None:
        """파서를 등록
        
        Args:
            parser_class: 등록할 파서 클래스
        """
        # 파서 인스턴스를 생성하여 정보 획득
        temp_parser = parser_class()
        language = temp_parser.language
        extensions = temp_parser.supported_extensions
        
        # 파서 등록
        self._parsers[language] = parser_class
        
        # 확장자 매핑 등록
        for ext in extensions:
            self._extension_mapping[ext.lower()] = language
    
    def get_parser_class(self, language: LanguageType) -> Optional[Type[BaseCodeParser]]:
        """언어별 파서 클래스를 반환
        
        Args:
            language: 언어 타입
            
        Returns:
            파서 클래스 또는 None
        """
        return self._parsers.get(language)
    
    def get_language_by_extension(self, extension: str) -> Optional[LanguageType]:
        """파일 확장자로 언어 타입을 반환
        
        Args:
            extension: 파일 확장자 (.py, .java 등)
            
        Returns:
            언어 타입 또는 None
        """
        return self._extension_mapping.get(extension.lower())
    
    def get_supported_languages(self) -> List[LanguageType]:
        """지원하는 언어 목록을 반환"""
        return list(self._parsers.keys())
    
    def get_supported_extensions(self) -> List[str]:
        """지원하는 확장자 목록을 반환"""
        return list(self._extension_mapping.keys())


# 글로벌 파서 레지스트리
_parser_registry = ParserRegistry()


class CodeParserFactory:
    """코드 파서 팩토리 클래스
    
    파일이나 언어에 따라 적절한 파서를 생성합니다.
    """
    
    @staticmethod
    def register_parser(parser_class: Type[BaseCodeParser]) -> None:
        """파서를 등록
        
        Args:
            parser_class: 등록할 파서 클래스
        """
        _parser_registry.register_parser(parser_class)
    
    @staticmethod
    def create_parser(language: LanguageType, keyword_extractor=None) -> Optional[BaseCodeParser]:
        """언어별 파서를 생성
        
        Args:
            language: 언어 타입
            keyword_extractor: 키워드 추출기 (옵션)
            
        Returns:
            파서 인스턴스 또는 None
        """
        parser_class = _parser_registry.get_parser_class(language)
        if parser_class:
            try:
                # Java 파서는 keyword_extractor 매개변수를 받을 수 있음
                return parser_class(keyword_extractor=keyword_extractor)
            except TypeError:
                # Python, JavaScript 파서는 매개변수 없이 초기화
                parser = parser_class()
                if keyword_extractor and hasattr(parser, 'keyword_extractor'):
                    parser.keyword_extractor = keyword_extractor
                return parser
        return None
    
    @staticmethod
    def create_parser_for_file(file_path: str, keyword_extractor=None) -> Optional[BaseCodeParser]:
        """파일에 적합한 파서를 생성
        
        Args:
            file_path: 파일 경로
            keyword_extractor: 키워드 추출기 (옵션)
            
        Returns:
            파서 인스턴스 또는 None
        """
        # 파일 확장자 추출
        _, ext = os.path.splitext(file_path)
        
        # 언어 타입 확인
        language = _parser_registry.get_language_by_extension(ext)
        if not language:
            return None
        
        return CodeParserFactory.create_parser(language, keyword_extractor)
    
    @staticmethod
    def detect_language(file_path: str) -> Optional[LanguageType]:
        """파일의 언어를 감지
        
        Args:
            file_path: 파일 경로
            
        Returns:
            감지된 언어 타입 또는 None
        """
        _, ext = os.path.splitext(file_path)
        return _parser_registry.get_language_by_extension(ext)
    
    @staticmethod
    def get_supported_languages() -> List[LanguageType]:
        """지원하는 언어 목록을 반환"""
        return _parser_registry.get_supported_languages()
    
    @staticmethod
    def get_supported_extensions() -> List[str]:
        """지원하는 확장자 목록을 반환"""
        return _parser_registry.get_supported_extensions()
    
    @staticmethod
    def is_supported_file(file_path: str) -> bool:
        """파일이 지원되는지 확인
        
        Args:
            file_path: 파일 경로
            
        Returns:
            지원 여부
        """
        return CodeParserFactory.detect_language(file_path) is not None


def register_parser(parser_class: Type[BaseCodeParser]):
    """파서 등록 데코레이터
    
    Args:
        parser_class: 등록할 파서 클래스
    """
    def decorator(cls):
        CodeParserFactory.register_parser(cls)
        return cls
    
    # 직접 호출된 경우
    if parser_class:
        CodeParserFactory.register_parser(parser_class)
        return parser_class
    
    # 데코레이터로 사용된 경우
    return decorator 