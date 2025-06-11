"""다중 언어 지원을 위한 기본 파서 추상 클래스

모든 언어별 파서가 구현해야 하는 공통 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import time
import os

from .schemas import CodeChunk, ParseResult, LanguageType


class BaseCodeParser(ABC):
    """코드 파서의 추상 기본 클래스
    
    모든 언어별 파서는 이 클래스를 상속받아 구현해야 합니다.
    """
    
    def __init__(self, keyword_extractor=None):
        """파서 초기화
        
        Args:
            keyword_extractor: 키워드 추출기 (언어별로 다를 수 있음)
        """
        self.keyword_extractor = keyword_extractor
    
    @property
    @abstractmethod
    def language(self) -> LanguageType:
        """지원하는 언어 타입을 반환"""
        pass
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """지원하는 파일 확장자 목록을 반환"""
        pass
    
    @abstractmethod
    def parse_code(self, code: str, file_path: str = "") -> List[CodeChunk]:
        """코드를 파싱하여 청크 목록으로 분할
        
        Args:
            code: 파싱할 코드 문자열
            file_path: 파일 경로 (옵션)
            
        Returns:
            파싱된 코드 청크 목록
            
        Raises:
            SyntaxError: 코드 구문 오류
            ValueError: 잘못된 입력값
        """
        pass
    
    def parse_file(self, file_path: str) -> ParseResult:
        """파일을 파싱하여 결과를 반환
        
        Args:
            file_path: 파싱할 파일 경로
            
        Returns:
            파싱 결과 객체
            
        Raises:
            FileNotFoundError: 파일을 찾을 수 없음
            PermissionError: 파일 읽기 권한 없음
        """
        start_time = time.time()
        errors = []
        
        try:
            # 파일 존재 확인
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
            
            # 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 코드 파싱
            chunks = self.parse_code(code, file_path)
            total_lines = len(code.splitlines())
            
        except Exception as e:
            errors.append(str(e))
            chunks = []
            total_lines = 0
        
        parse_time = time.time() - start_time
        
        return ParseResult(
            chunks=chunks,
            language=self.language,
            file_path=file_path,
            total_lines=total_lines,
            parse_time=parse_time,
            errors=errors
        )
    
    def can_parse_file(self, file_path: str) -> bool:
        """파일이 이 파서로 파싱 가능한지 확인
        
        Args:
            file_path: 확인할 파일 경로
            
        Returns:
            파싱 가능 여부
        """
        if not os.path.exists(file_path):
            return False
            
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.supported_extensions
    
    def _extract_keywords(self, text: str, additional_context: Optional[str] = None) -> List[str]:
        """텍스트에서 키워드를 추출
        
        Args:
            text: 키워드를 추출할 텍스트
            additional_context: 추가 컨텍스트 (옵션)
            
        Returns:
            추출된 키워드 목록
        """
        if self.keyword_extractor:
            # 이름에서 키워드 추출 (우선순위)
            name_keywords = self.keyword_extractor.extract_from_name(text)
            
            # 추가 컨텍스트가 있으면 코드에서도 키워드 추출
            if additional_context:
                code_keywords = self.keyword_extractor.extract_from_code(additional_context)
                
                # 이름 키워드를 우선순위로 두고 코드 키워드 추가
                # 중복 제거하되 이름 키워드는 유지
                seen = set(name_keywords)
                result_keywords = name_keywords.copy()
                
                for keyword in code_keywords:
                    if keyword not in seen and len(result_keywords) < 15:  # 최대 15개로 증가
                        result_keywords.append(keyword)
                        seen.add(keyword)
                
                return result_keywords
            
            return name_keywords[:10]
        else:
            # 기본 키워드 추출 (단순 분할)
            return [word.strip() for word in text.replace('_', ' ').split() if len(word.strip()) > 2][:10]
    
    def get_parser_info(self) -> dict:
        """파서 정보를 반환
        
        Returns:
            파서 정보 딕셔너리
        """
        return {
            "language": self.language.value,
            "supported_extensions": self.supported_extensions,
            "parser_class": self.__class__.__name__,
            "has_keyword_extractor": self.keyword_extractor is not None
        } 