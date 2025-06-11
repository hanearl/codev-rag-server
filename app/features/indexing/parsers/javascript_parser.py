"""JavaScript 코드 파서

esprima 라이브러리를 사용하여 JavaScript 코드를 파싱하고 청크로 분할합니다.
"""

import esprima
from typing import List, Dict, Any

from ..base_parser import BaseCodeParser
from ..schemas import CodeChunk, CodeType, LanguageType, ParseResult
from ..parser_factory import register_parser


@register_parser
class JavaScriptParser(BaseCodeParser):
    """JavaScript 코드 파서 클래스"""
    
    @property
    def language(self) -> LanguageType:
        """JavaScript 언어 타입 반환"""
        return LanguageType.JAVASCRIPT
    
    @property
    def supported_extensions(self) -> List[str]:
        """지원하는 파일 확장자 목록"""
        return ['.js', '.mjs', '.jsx']
    
    def parse_code(self, code: str, file_path: str = "") -> ParseResult:
        """JavaScript 코드를 파싱하여 청크 목록으로 분할
        
        Args:
            code: 파싱할 JavaScript 코드 문자열
            file_path: 파일 경로 (옵션)
            
        Returns:
            파싱 결과 (ParseResult)
            
        Raises:
            SyntaxError: JavaScript 구문 오류
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
            # JavaScript AST 파싱
            tree = esprima.parseScript(code, options={'loc': True, 'range': True})
        except Exception as e:
            try:
                # ES6 모듈로 다시 시도
                tree = esprima.parseModule(code, options={'loc': True, 'range': True})
            except Exception as module_e:
                raise SyntaxError(f"JavaScript 구문 오류: {e}")
        
        chunks = []
        lines = code.splitlines()
        
        # AST 순회하여 청크 추출
        if hasattr(tree, 'body'):
            for node in tree.body:
                self._extract_chunks_from_node(node, chunks, lines, file_path)
        
        return ParseResult(
            chunks=chunks,
            language=self.language,
            file_path=file_path,
            total_lines=len(lines),
            errors=[]
        )
    
    def _extract_chunks_from_node(self, node, chunks: List[CodeChunk], 
                                 lines: List[str], file_path: str, parent_class: str = None) -> None:
        """AST 노드를 순회하며 청크를 추출
        
        Args:
            node: JavaScript AST 노드
            chunks: 청크 목록 (결과가 추가됨)
            lines: 코드 라인 목록
            file_path: 파일 경로
            parent_class: 부모 클래스명 (옵션)
        """
        if not node or not hasattr(node, 'type'):
            return
        
        node_type = node.type
        
        # 함수 선언
        if node_type == 'FunctionDeclaration':
            chunk = self._create_function_chunk(node, lines, file_path, parent_class)
            chunks.append(chunk)
        
        # 클래스 선언
        elif node_type == 'ClassDeclaration':
            chunk = self._create_class_chunk(node, lines, file_path)
            chunks.append(chunk)
            
            # 클래스 메소드들 처리
            if hasattr(node, 'body') and hasattr(node.body, 'body'):
                for method in node.body.body:
                    if hasattr(method, 'type') and method.type == 'MethodDefinition':
                        method_chunk = self._create_method_chunk(method, lines, file_path, node.id.name)
                        chunks.append(method_chunk)
        
        # 변수 선언에서 함수 찾기
        elif node_type == 'VariableDeclaration':
            if hasattr(node, 'declarations'):
                for declarator in node.declarations:
                    if (hasattr(declarator, 'init') and declarator.init and 
                        hasattr(declarator.init, 'type') and 
                        declarator.init.type in ['FunctionExpression', 'ArrowFunctionExpression']):
                        chunk = self._create_variable_function_chunk(declarator, lines, file_path, parent_class)
                        if chunk:
                            chunks.append(chunk)
        
        # 자식 노드들 재귀 순회
        for attr_name in dir(node):
            if attr_name.startswith('_'):
                continue
            attr_value = getattr(node, attr_name)
            if hasattr(attr_value, 'type'):
                self._extract_chunks_from_node(attr_value, chunks, lines, file_path, parent_class)
            elif isinstance(attr_value, list):
                for item in attr_value:
                    if hasattr(item, 'type'):
                        self._extract_chunks_from_node(item, chunks, lines, file_path, parent_class)
    
    def _create_function_chunk(self, node, lines: List[str], 
                              file_path: str, parent_class: str = None) -> CodeChunk:
        """함수 선언 청크 생성
        
        Args:
            node: 함수 선언 AST 노드
            lines: 코드 라인 목록
            file_path: 파일 경로
            parent_class: 부모 클래스명
            
        Returns:
            함수 청크
        """
        # 함수명
        function_name = node.id.name if hasattr(node, 'id') and node.id else 'anonymous'
        
        # 라인 번호
        line_start = node.loc.start.line if hasattr(node, 'loc') and node.loc else 1
        line_end = node.loc.end.line if hasattr(node, 'loc') and node.loc else len(lines)
        
        # 코드 내용 추출
        function_lines = lines[line_start-1:line_end]
        code_content = '\n'.join(function_lines)
        
        # 키워드 추출
        keywords = self._extract_keywords(function_name, code_content)
        
        # 파라미터 추출
        parameters = []
        if hasattr(node, 'params'):
            for param in node.params:
                if hasattr(param, 'name'):
                    parameters.append(param.name)
                elif hasattr(param, 'left') and hasattr(param.left, 'name'):
                    parameters.append(param.left.name)
        
        return CodeChunk(
            name=function_name,
            code_content=code_content,
            code_type=CodeType.METHOD if parent_class else CodeType.FUNCTION,
            language=self.language,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            keywords=keywords,
            parent_class=parent_class,
            parameters=parameters,
            language_specific={
                "is_async": getattr(node, 'async', False),
                "is_generator": getattr(node, 'generator', False),
                "param_count": len(parameters)
            }
        )
    
    def _create_class_chunk(self, node, lines: List[str], file_path: str) -> CodeChunk:
        """클래스 청크 생성
        
        Args:
            node: 클래스 AST 노드
            lines: 코드 라인 목록
            file_path: 파일 경로
            
        Returns:
            클래스 청크
        """
        # 클래스명
        class_name = node.id.name if hasattr(node, 'id') and node.id else 'AnonymousClass'
        
        # 라인 번호
        line_start = node.loc.start.line if hasattr(node, 'loc') and node.loc else 1
        line_end = node.loc.end.line if hasattr(node, 'loc') and node.loc else len(lines)
        
        # 코드 내용 추출
        class_lines = lines[line_start-1:line_end]
        code_content = '\n'.join(class_lines)
        
        # 키워드 추출
        keywords = self._extract_keywords(class_name, code_content)
        
        # 상속 정보
        extends = None
        if hasattr(node, 'superClass') and node.superClass:
            extends = node.superClass.name if hasattr(node.superClass, 'name') else None
        
        return CodeChunk(
            name=class_name,
            code_content=code_content,
            code_type=CodeType.CLASS,
            language=self.language,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            keywords=keywords,
            extends=extends,
            language_specific={
                "has_constructor": any(
                    hasattr(m, 'key') and hasattr(m.key, 'name') and m.key.name == 'constructor' 
                    for m in node.body.body if hasattr(node, 'body') and hasattr(node.body, 'body')
                )
            }
        )
    
    def _create_method_chunk(self, node, lines: List[str], 
                           file_path: str, class_name: str) -> CodeChunk:
        """클래스 메소드 청크 생성
        
        Args:
            node: 메소드 AST 노드
            lines: 코드 라인 목록
            file_path: 파일 경로
            class_name: 클래스명
            
        Returns:
            메소드 청크
        """
        # 메소드명
        method_name = node.key.name if hasattr(node, 'key') and hasattr(node.key, 'name') else 'unknown_method'
        
        # 라인 번호
        line_start = node.loc.start.line if hasattr(node, 'loc') and node.loc else 1
        line_end = node.loc.end.line if hasattr(node, 'loc') and node.loc else len(lines)
        
        # 코드 내용 추출
        method_lines = lines[line_start-1:line_end]
        code_content = '\n'.join(method_lines)
        
        # 키워드 추출
        keywords = self._extract_keywords(method_name, code_content)
        
        # 파라미터 추출
        parameters = []
        if hasattr(node, 'value') and hasattr(node.value, 'params'):
            for param in node.value.params:
                if hasattr(param, 'name'):
                    parameters.append(param.name)
        
        return CodeChunk(
            name=method_name,
            code_content=code_content,
            code_type=CodeType.METHOD,
            language=self.language,
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            keywords=keywords,
            parent_class=class_name,
            parameters=parameters,
            language_specific={
                "is_static": getattr(node, 'static', False),
                "kind": getattr(node, 'kind', 'method'),  # method, constructor, get, set
                "is_async": getattr(node.value, 'async', False) if hasattr(node, 'value') else False
            }
        )
    
    def _create_variable_function_chunk(self, node, lines: List[str], 
                                      file_path: str, parent_class: str = None) -> CodeChunk:
        """변수에 할당된 함수 청크 생성
        
        Args:
            node: 변수 선언자 AST 노드
            lines: 코드 라인 목록
            file_path: 파일 경로
            parent_class: 부모 클래스명
            
        Returns:
            함수 청크 또는 None
        """
        # 변수명 (함수명으로 사용)
        function_name = node.id.name if hasattr(node, 'id') and hasattr(node.id, 'name') else 'anonymous'
        
        # 함수 노드
        func_node = node.init if hasattr(node, 'init') else None
        if not func_node:
            return None
        
        # 라인 번호
        line_start = func_node.loc.start.line if hasattr(func_node, 'loc') and func_node.loc else 1
        line_end = func_node.loc.end.line if hasattr(func_node, 'loc') and func_node.loc else len(lines)
        
        # 변수 선언도 포함
        var_start = node.loc.start.line if hasattr(node, 'loc') and node.loc else line_start
        
        # 코드 내용 추출 (변수 선언 포함)
        function_lines = lines[var_start-1:line_end]
        code_content = '\n'.join(function_lines)
        
        # 키워드 추출
        keywords = self._extract_keywords(function_name, code_content)
        
        # 파라미터 추출
        parameters = []
        if hasattr(func_node, 'params'):
            for param in func_node.params:
                if hasattr(param, 'name'):
                    parameters.append(param.name)
        
        return CodeChunk(
            name=function_name,
            code_content=code_content,
            code_type=CodeType.FUNCTION,
            language=self.language,
            file_path=file_path,
            line_start=var_start,
            line_end=line_end,
            keywords=keywords,
            parent_class=parent_class,
            parameters=parameters,
            language_specific={
                "is_variable_function": True,
                "function_type": func_node.type if hasattr(func_node, 'type') else 'unknown',
                "is_async": getattr(func_node, 'async', False)
            }
        ) 