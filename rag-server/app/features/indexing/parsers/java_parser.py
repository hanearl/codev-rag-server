"""Java 코드 파서

javalang 라이브러리를 사용하여 Java 코드를 파싱하고 청크로 분할합니다.
"""

import javalang
from typing import List

from ..base_parser import BaseCodeParser
from ..schemas import CodeChunk, CodeType, LanguageType, ParseResult
from ..parser_factory import register_parser
from ..keyword_extractor import KeywordExtractor


@register_parser
class JavaParser(BaseCodeParser):
    """Java 코드 파서 클래스"""
    
    def __init__(self, keyword_extractor=None):
        """Java 파서 초기화"""
        if keyword_extractor is None:
            keyword_extractor = KeywordExtractor()
        super().__init__(keyword_extractor=keyword_extractor)
    
    @property
    def language(self) -> LanguageType:
        """Java 언어 타입 반환"""
        return LanguageType.JAVA
    
    @property
    def supported_extensions(self) -> List[str]:
        """지원하는 파일 확장자 목록"""
        return ['.java']
    
    def parse_code(self, code: str, file_path: str = "") -> ParseResult:
        """Java 코드를 파싱하여 청크 목록으로 분할
        
        Args:
            code: 파싱할 Java 코드 문자열
            file_path: 파일 경로 (옵션)
            
        Returns:
            파싱 결과 객체
            
        Raises:
            SyntaxError: Java 구문 오류
            ValueError: 잘못된 입력값
        """
        if not code or not code.strip():
            return ParseResult(
                chunks=[],
                language=self.language,
                file_path=file_path,
                total_lines=0,
                errors=[]
            )
        
        try:
            # Java AST 파싱
            tree = javalang.parse.parse(code)
        except (javalang.parser.JavaSyntaxError, javalang.tokenizer.LexerError) as e:
            # 구문 오류가 있어도 빈 결과 반환 (예외 발생 안함)
            return ParseResult(
                chunks=[],
                language=self.language,
                file_path=file_path,
                total_lines=len(code.splitlines()),
                errors=[f"Java 구문 오류: {e}"]
            )
        
        chunks = []
        lines = code.splitlines()
        
        # 패키지 정보 추출
        package_name = None
        if tree.package:
            package_name = tree.package.name
        
        # 타입 선언 순회 (클래스, 인터페이스, 열거형)
        for type_decl in tree.types:
            chunks.extend(self._extract_chunks_from_type(type_decl, lines, file_path, package_name))
        
        return ParseResult(
            chunks=chunks,
            language=self.language,
            file_path=file_path,
            total_lines=len(lines),
            errors=[]
        )
    
    def _extract_chunks_from_type(self, type_decl, lines: List[str], file_path: str, package_name: str) -> List[CodeChunk]:
        """타입 선언에서 청크들을 추출
        
        Args:
            type_decl: Java 타입 선언 (클래스, 인터페이스 등)
            lines: 코드 라인 목록
            file_path: 파일 경로
            package_name: 패키지명
            
        Returns:
            추출된 청크 목록
        """
        chunks = []
        
        # 클래스/인터페이스/열거형 청크 생성
        if isinstance(type_decl, javalang.tree.ClassDeclaration):
            chunk = self._create_class_chunk(type_decl, lines, file_path, package_name, CodeType.CLASS)
            chunks.append(chunk)
        elif isinstance(type_decl, javalang.tree.InterfaceDeclaration):
            chunk = self._create_class_chunk(type_decl, lines, file_path, package_name, CodeType.INTERFACE)
            chunks.append(chunk)
        elif isinstance(type_decl, javalang.tree.EnumDeclaration):
            chunk = self._create_class_chunk(type_decl, lines, file_path, package_name, CodeType.ENUM)
            chunks.append(chunk)
        
        # 메소드들 처리
        if hasattr(type_decl, 'body') and type_decl.body:
            for member in type_decl.body:
                if isinstance(member, javalang.tree.MethodDeclaration):
                    method_chunk = self._create_method_chunk(member, lines, file_path, package_name, type_decl.name)
                    chunks.append(method_chunk)
                elif isinstance(member, javalang.tree.ConstructorDeclaration):
                    constructor_chunk = self._create_constructor_chunk(member, lines, file_path, package_name, type_decl.name)
                    chunks.append(constructor_chunk)
        
        return chunks
    
    def _create_class_chunk(self, type_decl, lines: List[str], file_path: str, 
                           package_name: str, code_type: CodeType) -> CodeChunk:
        """클래스/인터페이스/열거형 청크 생성
        
        Args:
            type_decl: 타입 선언
            lines: 코드 라인 목록
            file_path: 파일 경로
            package_name: 패키지명
            code_type: 코드 타입
            
        Returns:
            클래스 청크
        """
        # 라인 번호 정보
        line_start = type_decl.position.line if type_decl.position else 1
        line_end = self._find_closing_brace(lines, line_start)
        
        # 코드 내용 추출
        class_lines = lines[line_start-1:line_end]
        code_content = '\n'.join(class_lines)
        
        # 어노테이션 추출
        annotations = []
        annotations_with_at = []
        if hasattr(type_decl, 'annotations') and type_decl.annotations:
            for annotation in type_decl.annotations:
                annotations.append(annotation.name)
                annotations_with_at.append(f"@{annotation.name}")
        
        # 어노테이션에서 키워드 추출 (우선순위 1)
        annotation_keywords = []
        if annotations_with_at:
            annotation_keywords = self.keyword_extractor.extract_from_annotations(annotations_with_at)
        
        # 클래스 이름에서 키워드 추출 (우선순위 2)
        name_keywords = self.keyword_extractor.extract_from_name(type_decl.name)
        
        # 코드 내용에서 키워드 추출 (우선순위 3)
        code_keywords = self.keyword_extractor.extract_from_code(code_content)
        
        # 우선순위별로 키워드 조합
        keywords = []
        seen = set()
        
        # 1. 어노테이션 키워드 먼저 추가
        for keyword in annotation_keywords:
            if keyword not in seen and len(keywords) < 25:
                keywords.append(keyword)
                seen.add(keyword)
        
        # 2. 이름 키워드 추가
        for keyword in name_keywords:
            if keyword not in seen and len(keywords) < 25:
                keywords.append(keyword)
                seen.add(keyword)
        
        # 3. 코드 키워드 추가
        for keyword in code_keywords:
            if keyword not in seen and len(keywords) < 25:
                keywords.append(keyword)
                seen.add(keyword)
        
        # 수정자 추출
        modifiers = []
        if hasattr(type_decl, 'modifiers') and type_decl.modifiers:
            modifiers.extend(type_decl.modifiers)
        
        # 상속/구현 정보
        extends = None
        implements = []
        
        if hasattr(type_decl, 'extends') and type_decl.extends:
            if isinstance(type_decl.extends, list):
                # Interface의 extends는 리스트일 수 있음
                extends = [ext.name for ext in type_decl.extends]
            else:
                extends = type_decl.extends.name
        
        if hasattr(type_decl, 'implements') and type_decl.implements:
            implements = [impl.name for impl in type_decl.implements]
        
        return CodeChunk(
            name=type_decl.name,
            code_content=code_content,
            code_type=code_type,
            language=self.language,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            keywords=keywords,
            namespace=package_name,
            annotations=annotations,
            modifiers=modifiers,
            extends=extends,
            implements=implements,
            language_specific={
                "package_name": package_name,
                "annotations": annotations_with_at,
                "modifiers": modifiers,
                "is_abstract": "abstract" in modifiers,
                "is_final": "final" in modifiers,
                "is_static": "static" in modifiers
            }
        )
    
    def _create_method_chunk(self, method_decl, lines: List[str], file_path: str, 
                           package_name: str, class_name: str) -> CodeChunk:
        """메소드 청크 생성
        
        Args:
            method_decl: 메소드 선언
            lines: 코드 라인 목록
            file_path: 파일 경로
            package_name: 패키지명
            class_name: 클래스명
            
        Returns:
            메소드 청크
        """
        # 라인 번호 정보
        line_start = method_decl.position.line if method_decl.position else 1
        line_end = self._find_method_end(lines, line_start)
        
        # 코드 내용 추출
        method_lines = lines[line_start-1:line_end]
        code_content = '\n'.join(method_lines)
        
        # 어노테이션 추출
        annotations = []
        annotations_with_at = []
        if hasattr(method_decl, 'annotations') and method_decl.annotations:
            for annotation in method_decl.annotations:
                annotations.append(annotation.name)
                annotations_with_at.append(f"@{annotation.name}")
        
        # 어노테이션에서 키워드 추출 (우선순위 1)
        annotation_keywords = []
        if annotations_with_at:
            annotation_keywords = self.keyword_extractor.extract_from_annotations(annotations_with_at)
        
        # 메서드 이름에서 키워드 추출 (우선순위 2)
        name_keywords = self.keyword_extractor.extract_from_name(method_decl.name)
        
        # 코드 내용에서 키워드 추출 (우선순위 3)
        code_keywords = self.keyword_extractor.extract_from_code(code_content)
        
        # 우선순위별로 키워드 조합
        keywords = []
        seen = set()
        
        # 1. 어노테이션 키워드 먼저 추가
        for keyword in annotation_keywords:
            if keyword not in seen and len(keywords) < 25:
                keywords.append(keyword)
                seen.add(keyword)
        
        # 2. 이름 키워드 추가
        for keyword in name_keywords:
            if keyword not in seen and len(keywords) < 25:
                keywords.append(keyword)
                seen.add(keyword)
        
        # 3. 코드 키워드 추가
        for keyword in code_keywords:
            if keyword not in seen and len(keywords) < 25:
                keywords.append(keyword)
                seen.add(keyword)
        
        # 수정자 추출
        modifiers = []
        if hasattr(method_decl, 'modifiers') and method_decl.modifiers:
            modifiers.extend(method_decl.modifiers)
        
        # 파라미터 추출
        parameters = []
        if hasattr(method_decl, 'parameters') and method_decl.parameters:
            for param in method_decl.parameters:
                parameters.append(f"{param.type.name} {param.name}")
        
        # 반환 타입
        return_type = None
        if hasattr(method_decl, 'return_type'):
            if method_decl.return_type is None:
                # void 메서드인 경우
                return_type = "void"
            elif hasattr(method_decl.return_type, 'name'):
                return_type = method_decl.return_type.name
            else:
                # 기타 타입의 경우 문자열로 처리
                return_type = str(method_decl.return_type)
        
        return CodeChunk(
            name=f"{class_name}.{method_decl.name}",
            code_content=code_content,
            code_type=CodeType.METHOD,
            language=self.language,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            keywords=keywords,
            namespace=package_name,
            parent_class=class_name,
            annotations=annotations,
            modifiers=modifiers,
            return_type=return_type,
            parameters=parameters,
            language_specific={
                "package_name": package_name,
                "class_name": class_name,
                "return_type": return_type,
                "annotations": annotations_with_at,
                "modifiers": modifiers,
                "is_static": "static" in modifiers,
                "is_abstract": "abstract" in modifiers,
                "is_final": "final" in modifiers,
                "is_synchronized": "synchronized" in modifiers
            }
        )
    
    def _create_constructor_chunk(self, constructor_decl, lines: List[str], file_path: str, 
                                package_name: str, class_name: str) -> CodeChunk:
        """생성자 청크 생성
        
        Args:
            constructor_decl: 생성자 선언
            lines: 코드 라인 목록
            file_path: 파일 경로
            package_name: 패키지명
            class_name: 클래스명
            
        Returns:
            생성자 청크
        """
        # 라인 번호 정보
        line_start = constructor_decl.position.line if constructor_decl.position else 1
        line_end = self._find_method_end(lines, line_start)
        
        # 코드 내용 추출
        constructor_lines = lines[line_start-1:line_end]
        code_content = '\n'.join(constructor_lines)
        
        # 어노테이션 추출
        annotations = []
        annotations_with_at = []
        if hasattr(constructor_decl, 'annotations') and constructor_decl.annotations:
            for annotation in constructor_decl.annotations:
                annotations.append(annotation.name)
                annotations_with_at.append(f"@{annotation.name}")
        
        # 어노테이션에서 키워드 추출 (우선순위 1)
        annotation_keywords = []
        if annotations_with_at:
            annotation_keywords = self.keyword_extractor.extract_from_annotations(annotations_with_at)
        
        # 생성자 이름에서 키워드 추출 (우선순위 2)
        name_keywords = self.keyword_extractor.extract_from_name(constructor_decl.name)
        
        # 코드 내용에서 키워드 추출 (우선순위 3)
        code_keywords = self.keyword_extractor.extract_from_code(code_content)
        
        # 우선순위별로 키워드 조합
        keywords = []
        seen = set()
        
        # 1. 어노테이션 키워드 먼저 추가
        for keyword in annotation_keywords:
            if keyword not in seen and len(keywords) < 25:
                keywords.append(keyword)
                seen.add(keyword)
        
        # 2. 이름 키워드 추가
        for keyword in name_keywords:
            if keyword not in seen and len(keywords) < 25:
                keywords.append(keyword)
                seen.add(keyword)
        
        # 3. 코드 키워드 추가
        for keyword in code_keywords:
            if keyword not in seen and len(keywords) < 25:
                keywords.append(keyword)
                seen.add(keyword)
        
        # 수정자 추출
        modifiers = []
        if hasattr(constructor_decl, 'modifiers') and constructor_decl.modifiers:
            modifiers.extend(constructor_decl.modifiers)
        
        # 파라미터 추출
        parameters = []
        if hasattr(constructor_decl, 'parameters') and constructor_decl.parameters:
            for param in constructor_decl.parameters:
                parameters.append(f"{param.type.name} {param.name}")
        
        return CodeChunk(
            name=f"{class_name}.{constructor_decl.name}",
            code_content=code_content,
            code_type=CodeType.METHOD,
            language=self.language,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            keywords=keywords,
            namespace=package_name,
            parent_class=class_name,
            annotations=annotations,
            modifiers=modifiers,
            parameters=parameters,
            language_specific={
                "package_name": package_name,
                "class_name": class_name,
                "annotations": annotations_with_at,
                "modifiers": modifiers,
                "is_constructor": True
            }
        )
    
    def _find_closing_brace(self, lines: List[str], start_line: int) -> int:
        """클래스의 닫힌 중괄호 라인 찾기
        
        Args:
            lines: 코드 라인 목록
            start_line: 시작 라인
            
        Returns:
            닫힌 중괄호 라인 번호
        """
        brace_count = 0
        found_opening = False
        
        for i in range(start_line - 1, len(lines)):
            line = lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_opening = True
                elif char == '}':
                    brace_count -= 1
                    
                    if found_opening and brace_count == 0:
                        return i + 1
        
        return len(lines)
    
    def _find_method_end(self, lines: List[str], start_line: int) -> int:
        """메소드의 끝 라인 찾기
        
        Args:
            lines: 코드 라인 목록
            start_line: 시작 라인
            
        Returns:
            메소드 끝 라인 번호
        """
        # 추상 메소드인 경우 (세미콜론으로 끝남)
        start_line_content = lines[start_line - 1]
        if ';' in start_line_content and '{' not in start_line_content:
            return start_line
        
        # 일반 메소드인 경우 중괄호로 끝 찾기
        return self._find_closing_brace(lines, start_line) 