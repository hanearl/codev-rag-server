"""코드 청크 스키마 정의

다중 언어 코드 파싱 결과를 저장하기 위한 데이터 구조를 정의합니다.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class LanguageType(Enum):
    """지원하는 프로그래밍 언어 타입"""
    PYTHON = "python"
    JAVA = "java" 
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"


class CodeType(Enum):
    """코드 청크 타입"""
    CLASS = "class"
    METHOD = "method"
    FUNCTION = "function"
    INTERFACE = "interface"
    ENUM = "enum"
    VARIABLE = "variable"
    CONSTANT = "constant"


@dataclass
class CodeChunk:
    """다중 언어 지원 코드 청크 데이터 클래스
    
    파싱된 코드의 각 단위를 나타내는 언어 중립적 데이터 구조입니다.
    """
    name: str                               # 클래스/메소드/함수명
    code_content: str                       # 실제 코드 내용
    code_type: CodeType                     # 코드 타입 (enum)
    language: LanguageType                  # 프로그래밍 언어
    file_path: str                          # 파일 경로
    line_start: int                         # 시작 라인 번호
    line_end: int                           # 끝 라인 번호  
    keywords: List[str]                     # 추출된 키워드 리스트
    
    # 선택적 메타데이터 (언어별로 다를 수 있음)
    namespace: Optional[str] = None         # 패키지명/모듈명/네임스페이스
    parent_class: Optional[str] = None      # 소속 클래스명 (메소드인 경우)
    annotations: List[str] = None           # 어노테이션/데코레이터
    modifiers: List[str] = None             # 접근제어자/수정자
    return_type: Optional[str] = None       # 반환 타입
    parameters: List[str] = None            # 파라미터 정보
    extends: Optional[str] = None           # 상속/확장 정보
    implements: List[str] = None            # 구현 인터페이스
    
    # 추가 언어별 메타데이터를 위한 확장 필드
    language_specific: Dict[str, Any] = None
    
    def __post_init__(self):
        """초기화 후 처리"""
        if self.annotations is None:
            self.annotations = []
        if self.modifiers is None:
            self.modifiers = []
        if self.parameters is None:
            self.parameters = []
        if self.implements is None:
            self.implements = []
        if self.language_specific is None:
            self.language_specific = {}


@dataclass 
class ParseResult:
    """파싱 결과를 담는 데이터 클래스"""
    chunks: List[CodeChunk]
    language: LanguageType
    file_path: str
    total_lines: int
    parse_time: Optional[float] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = [] 