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
        start_line = getattr(node, 'position', None)
        if start_line and hasattr(start_line, 'line'):
            return start_line.line, start_line.line + 10
        return 1, 10
    
    def _extract_code_content(self, lines: List[str], start: int, end: int) -> str:
        """지정된 라인 범위의 코드 추출"""
        if start <= 0:
            start = 1
        if end > len(lines):
            end = len(lines)
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