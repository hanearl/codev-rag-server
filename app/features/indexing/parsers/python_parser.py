"""Python 코드 파서

Python AST를 사용하여 Python 코드를 파싱하고 청크로 분할합니다.
"""

import ast
from typing import List

from ..base_parser import BaseCodeParser
from ..schemas import CodeChunk, CodeType, LanguageType, ParseResult
from ..parser_factory import register_parser


@register_parser
class PythonParser(BaseCodeParser):
    """Python 코드 파서 클래스"""
    
    @property
    def language(self) -> LanguageType:
        """Python 언어 타입 반환"""
        return LanguageType.PYTHON
    
    @property
    def supported_extensions(self) -> List[str]:
        """지원하는 파일 확장자 목록"""
        return ['.py', '.pyw']
    
    def parse_code(self, code: str, file_path: str = "") -> ParseResult:
        """Python 코드를 파싱하여 청크 목록으로 분할
        
        Args:
            code: 파싱할 Python 코드 문자열
            file_path: 파일 경로 (옵션)
            
        Returns:
            파싱 결과 (ParseResult)
            
        Raises:
            SyntaxError: Python 구문 오류
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
            # Python AST 파싱
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SyntaxError(f"Python 구문 오류: {e}")
        
        chunks = []
        lines = code.splitlines()
        
        # AST 노드 순회하여 청크 추출
        for node in ast.walk(tree):
            chunk = self._extract_chunk_from_node(node, lines, file_path)
            if chunk:
                chunks.append(chunk)
        
        return ParseResult(
            chunks=chunks,
            language=self.language,
            file_path=file_path,
            total_lines=len(lines),
            errors=[]
        )
    
    def _extract_chunk_from_node(self, node: ast.AST, lines: List[str], file_path: str) -> CodeChunk:
        """AST 노드에서 코드 청크를 추출
        
        Args:
            node: AST 노드
            lines: 코드 라인 목록
            file_path: 파일 경로
            
        Returns:
            추출된 코드 청크 또는 None
        """
        chunk = None
        
        if isinstance(node, ast.FunctionDef):
            chunk = self._create_function_chunk(node, lines, file_path, CodeType.FUNCTION)
        elif isinstance(node, ast.AsyncFunctionDef):
            chunk = self._create_function_chunk(node, lines, file_path, CodeType.FUNCTION, is_async=True)
        elif isinstance(node, ast.ClassDef):
            chunk = self._create_class_chunk(node, lines, file_path)
        
        return chunk
    
    def _create_function_chunk(self, node: ast.FunctionDef, lines: List[str], 
                             file_path: str, code_type: CodeType, is_async: bool = False) -> CodeChunk:
        """함수/메소드 청크 생성
        
        Args:
            node: 함수 AST 노드
            lines: 코드 라인 목록
            file_path: 파일 경로
            code_type: 코드 타입
            is_async: async 함수 여부
            
        Returns:
            함수 청크
        """
        line_start = node.lineno
        line_end = self._get_node_end_line(node, lines)
        
        # 함수 코드 추출
        function_lines = lines[line_start-1:line_end]
        code_content = '\n'.join(function_lines)
        
        # 키워드 추출
        keywords = self._extract_keywords(node.name, code_content)
        
        # 데코레이터 추출
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(decorator.attr)
        
        # 파라미터 추출
        parameters = []
        for arg in node.args.args:
            parameters.append(arg.arg)
        
        # 부모 클래스 찾기
        parent_class = self._find_parent_class(node, lines)
        
        return CodeChunk(
            name=node.name,
            code_content=code_content,
            code_type=CodeType.METHOD if parent_class else CodeType.FUNCTION,
            language=self.language,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            keywords=keywords,
            parent_class=parent_class,
            annotations=decorators,
            parameters=parameters,
            language_specific={
                "is_async": is_async,
                "args_count": len(node.args.args),
                "has_varargs": node.args.vararg is not None,
                "has_kwargs": node.args.kwarg is not None
            }
        )
    
    def _create_class_chunk(self, node: ast.ClassDef, lines: List[str], file_path: str) -> CodeChunk:
        """클래스 청크 생성
        
        Args:
            node: 클래스 AST 노드
            lines: 코드 라인 목록
            file_path: 파일 경로
            
        Returns:
            클래스 청크
        """
        line_start = node.lineno
        line_end = self._get_node_end_line(node, lines)
        
        # 클래스 코드 추출
        class_lines = lines[line_start-1:line_end]
        code_content = '\n'.join(class_lines)
        
        # 키워드 추출
        keywords = self._extract_keywords(node.name, code_content)
        
        # 데코레이터 추출
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(decorator.attr)
        
        # 상속 클래스 추출
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(base.attr)
        
        extends = base_classes[0] if base_classes else None
        
        return CodeChunk(
            name=node.name,
            code_content=code_content,
            code_type=CodeType.CLASS,
            language=self.language,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            keywords=keywords,
            annotations=decorators,
            extends=extends,
            implements=base_classes[1:] if len(base_classes) > 1 else [],
            language_specific={
                "base_classes": base_classes,
                "method_count": len([n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]),
                "has_docstring": ast.get_docstring(node) is not None
            }
        )
    
    def _get_node_end_line(self, node: ast.AST, lines: List[str]) -> int:
        """AST 노드의 끝 라인 번호 계산
        
        Args:
            node: AST 노드
            lines: 코드 라인 목록
            
        Returns:
            끝 라인 번호
        """
        # Python 3.8+ 에서는 end_lineno 속성 사용 가능
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno
        
        # 대안: 노드 시작부터 들여쓰기가 같거나 적은 라인까지 찾기
        start_line = node.lineno
        if start_line > len(lines):
            return len(lines)
        
        # 시작 라인의 들여쓰기 계산
        start_indent = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip())
        
        # 다음 라인들을 확인하여 끝 라인 찾기
        for i in range(start_line, len(lines)):
            line = lines[i]
            if line.strip():  # 빈 라인이 아닌 경우
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= start_indent:
                    return i
        
        return len(lines)
    
    def _find_parent_class(self, node: ast.FunctionDef, lines: List[str]) -> str:
        """함수의 부모 클래스명 찾기
        
        Args:
            node: 함수 AST 노드
            lines: 코드 라인 목록
            
        Returns:
            부모 클래스명 또는 None
        """
        start_line = node.lineno
        start_indent = len(lines[start_line - 1]) - len(lines[start_line - 1].lstrip())
        
        # 역순으로 클래스 정의 찾기
        for i in range(start_line - 2, -1, -1):
            line = lines[i].strip()
            if line.startswith('class ') and ':' in line:
                class_indent = len(lines[i]) - len(lines[i].lstrip())
                if class_indent < start_indent:
                    # 클래스명 추출
                    class_name = line.split('class ')[1].split('(')[0].split(':')[0].strip()
                    return class_name
        
        return None 