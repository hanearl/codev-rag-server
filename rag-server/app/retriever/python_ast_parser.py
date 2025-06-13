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
        bases = [self._get_name_from_node(base) for base in node.bases]
        
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
            line_end=getattr(node, 'end_lineno', node.lineno + 10),
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
                param_info["type"] = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else "annotated"
            parameters.append(param_info)
        
        # 반환 타입
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else "annotated"
        
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
            line_end=getattr(node, 'end_lineno', node.lineno + 10),
            parent_class=parent_class,
            parameters=parameters,
            return_type=return_type,
            annotations=decorators,
            docstring=docstring,
            keywords=[node.name]
        )
    
    def _extract_function_metadata(self, node: ast.FunctionDef, file_path: str, lines: List[str]) -> CodeMetadata:
        """함수 메타데이터 추출"""
        # 메서드와 동일한 로직이지만 code_type을 FUNCTION으로 설정
        metadata = self._extract_method_metadata(node, file_path, lines)
        metadata.code_type = CodeType.FUNCTION
        return metadata
    
    def _get_decorator_name(self, decorator) -> str:
        """데코레이터 이름 추출"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            if hasattr(ast, 'unparse'):
                return ast.unparse(decorator)
            else:
                return f"{decorator.value.id}.{decorator.attr}" if hasattr(decorator.value, 'id') else decorator.attr
        else:
            return str(decorator)
    
    def _get_name_from_node(self, node) -> str:
        """AST 노드에서 이름 추출"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            if hasattr(ast, 'unparse'):
                return ast.unparse(node)
            else:
                return f"{node.value.id}.{node.attr}" if hasattr(node.value, 'id') else node.attr
        else:
            return str(node)
    
    def _extract_code_content(self, lines: List[str], start: int, end: int) -> str:
        """지정된 라인 범위의 코드 추출"""
        if start <= 0:
            start = 1
        if end > len(lines):
            end = len(lines)
        return '\n'.join(lines[start-1:end]) 