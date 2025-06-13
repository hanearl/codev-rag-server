# Task 9: Document Builder 구현

## 📋 작업 개요
AST 파서에서 생성된 코드 구조를 LlamaIndex Document와 TextNode로 변환하고, 임베딩과 검색에 최적화된 형태로 구조화하는 Document Builder를 구현합니다.

## 🎯 작업 목표
- LlamaIndex Document/TextNode 생성 최적화
- 코드 구조화 및 청킹 전략 구현
- 메타데이터 강화 및 검색 최적화
- 기존 indexing 모듈의 기능을 LlamaIndex 기반으로 통합

## 🔗 의존성
- **선행 Task**: Task 8 (LlamaIndex 기반 AST 파서 구현)
- **활용할 기존 코드**: `app/features/indexing/service.py`의 문서 생성 로직

## 🔧 구현 사항

### 1. Document Builder 인터페이스

```python
# app/retriever/document_builder.py
from typing import List, Dict, Any, Optional, Union
from llama_index.core import Document
from llama_index.core.schema import TextNode, MetadataMode
from llama_index.core.node_parser import SimpleNodeParser, CodeSplitter
from pydantic import BaseModel
from enum import Enum
from .ast_parser import ParseResult, CodeMetadata, Language, CodeType
import hashlib

class ChunkingStrategy(str, Enum):
    """청킹 전략"""
    METHOD_LEVEL = "method_level"      # 메서드/함수 단위
    CLASS_LEVEL = "class_level"        # 클래스 단위  
    FILE_LEVEL = "file_level"          # 파일 단위
    SEMANTIC = "semantic"              # 의미적 단위
    HYBRID = "hybrid"                  # 하이브리드

class DocumentBuildConfig(BaseModel):
    """Document 빌드 설정"""
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.METHOD_LEVEL
    max_chunk_size: int = 1024
    chunk_overlap: int = 100
    include_metadata: bool = True
    enhance_keywords: bool = True
    add_context: bool = True
    preserve_structure: bool = True

class EnhancedDocument(BaseModel):
    """강화된 문서 모델"""
    document: Document
    text_node: TextNode
    metadata: CodeMetadata
    enhanced_content: str
    search_keywords: List[str]
    semantic_tags: List[str]
    relationships: Dict[str, Any]

class DocumentBuildResult(BaseModel):
    """Document 빌드 결과"""
    documents: List[EnhancedDocument]
    total_documents: int
    build_time_ms: int
    metadata: Dict[str, Any]
    statistics: Dict[str, int]

class DocumentBuilder:
    """LlamaIndex Document Builder"""
    
    def __init__(self, config: DocumentBuildConfig = None):
        self.config = config or DocumentBuildConfig()
        self.node_parser = self._create_node_parser()
    
    async def build_from_parse_result(self, parse_result: ParseResult) -> DocumentBuildResult:
        """파싱 결과로부터 강화된 Document 생성"""
        import time
        start_time = time.time()
        
        enhanced_docs = []
        statistics = {
            "classes": 0,
            "methods": 0,
            "functions": 0,
            "interfaces": 0,
            "total_lines": 0
        }
        
        for doc in parse_result.documents:
            enhanced_doc = await self._enhance_document(doc)
            enhanced_docs.append(enhanced_doc)
            
            # 통계 업데이트
            self._update_statistics(statistics, enhanced_doc.metadata)
        
        end_time = time.time()
        
        return DocumentBuildResult(
            documents=enhanced_docs,
            total_documents=len(enhanced_docs),
            build_time_ms=int((end_time - start_time) * 1000),
            metadata=parse_result.metadata,
            statistics=statistics
        )
    
    async def build_from_legacy_chunks(self, chunks: List[Dict[str, Any]]) -> DocumentBuildResult:
        """기존 indexing 모듈의 청크로부터 Document 생성"""
        import time
        start_time = time.time()
        
        enhanced_docs = []
        statistics = {"legacy_chunks": len(chunks)}
        
        for chunk in chunks:
            # 기존 청크를 CodeMetadata로 변환
            metadata = self._convert_legacy_chunk_to_metadata(chunk)
            
            # Document 생성
            document = Document(
                text=chunk.get("code_content", ""),
                metadata=metadata.dict(),
                id_=self._generate_document_id(metadata)
            )
            
            # TextNode 생성
            text_node = TextNode(
                text=chunk.get("code_content", ""),
                metadata=metadata.dict(),
                id_=self._generate_document_id(metadata)
            )
            
            # 강화된 문서 생성
            enhanced_doc = EnhancedDocument(
                document=document,
                text_node=text_node,
                metadata=metadata,
                enhanced_content=await self._enhance_content(chunk.get("code_content", ""), metadata),
                search_keywords=await self._extract_search_keywords(chunk.get("code_content", ""), metadata),
                semantic_tags=await self._generate_semantic_tags(metadata),
                relationships=await self._analyze_relationships(metadata)
            )
            
            enhanced_docs.append(enhanced_doc)
        
        end_time = time.time()
        
        return DocumentBuildResult(
            documents=enhanced_docs,
            total_documents=len(enhanced_docs),
            build_time_ms=int((end_time - start_time) * 1000),
            metadata={"source": "legacy_chunks"},
            statistics=statistics
        )
    
    async def _enhance_document(self, document: Document) -> EnhancedDocument:
        """Document 강화"""
        # 메타데이터에서 CodeMetadata 복원
        metadata = CodeMetadata(**document.metadata)
        
        # 컨텐츠 강화
        enhanced_content = await self._enhance_content(document.text, metadata)
        
        # 검색 키워드 추출
        search_keywords = await self._extract_search_keywords(document.text, metadata)
        
        # 의미적 태그 생성
        semantic_tags = await self._generate_semantic_tags(metadata)
        
        # 관계 분석
        relationships = await self._analyze_relationships(metadata)
        
        # TextNode 생성
        text_node = TextNode(
            text=enhanced_content,
            metadata=document.metadata,
            id_=document.id_
        )
        
        return EnhancedDocument(
            document=document,
            text_node=text_node,
            metadata=metadata,
            enhanced_content=enhanced_content,
            search_keywords=search_keywords,
            semantic_tags=semantic_tags,
            relationships=relationships
        )
    
    async def _enhance_content(self, content: str, metadata: CodeMetadata) -> str:
        """컨텐츠 강화"""
        enhanced_parts = []
        
        # 기본 정보 추가
        enhanced_parts.append(f"# {metadata.code_type.value.title()}: {metadata.name}")
        
        # 파일 경로 정보
        enhanced_parts.append(f"File: {metadata.file_path}")
        
        # 언어 정보
        enhanced_parts.append(f"Language: {metadata.language.value}")
        
        # 라인 정보
        enhanced_parts.append(f"Lines: {metadata.line_start}-{metadata.line_end}")
        
        # 메타데이터 기반 컨텍스트 추가
        if metadata.parent_class:
            enhanced_parts.append(f"Parent Class: {metadata.parent_class}")
        
        if metadata.namespace:
            enhanced_parts.append(f"Namespace: {metadata.namespace}")
        
        if metadata.extends:
            enhanced_parts.append(f"Extends: {metadata.extends}")
        
        if metadata.implements:
            enhanced_parts.append(f"Implements: {', '.join(metadata.implements)}")
        
        if metadata.parameters:
            params = [f"{p['name']}: {p.get('type', 'unknown')}" for p in metadata.parameters]
            enhanced_parts.append(f"Parameters: {', '.join(params)}")
        
        if metadata.return_type:
            enhanced_parts.append(f"Returns: {metadata.return_type}")
        
        # 주석/독스트링 추가
        if metadata.comments:
            enhanced_parts.append(f"Comments: {metadata.comments}")
        
        if metadata.docstring:
            enhanced_parts.append(f"Documentation: {metadata.docstring}")
        
        # 키워드 추가
        if metadata.keywords:
            enhanced_parts.append(f"Keywords: {', '.join(metadata.keywords)}")
        
        # 원본 코드
        enhanced_parts.append("\n## Code:")
        enhanced_parts.append(content)
        
        return "\n".join(enhanced_parts)
    
    async def _extract_search_keywords(self, content: str, metadata: CodeMetadata) -> List[str]:
        """검색 키워드 추출"""
        keywords = set()
        
        # 메타데이터 기반 키워드
        keywords.add(metadata.name)
        keywords.update(metadata.keywords)
        
        if metadata.parent_class:
            keywords.add(metadata.parent_class)
        
        if metadata.namespace:
            keywords.update(metadata.namespace.split('.'))
        
        if metadata.extends:
            keywords.add(metadata.extends)
        
        keywords.update(metadata.implements)
        
        # 파라미터 타입 키워드
        for param in metadata.parameters:
            if param.get('type'):
                keywords.add(param['type'])
        
        if metadata.return_type:
            keywords.add(metadata.return_type)
        
        # 어노테이션/데코레이터
        keywords.update(metadata.annotations)
        
        # 수정자
        keywords.update(metadata.modifiers)
        
        # 코드 내용에서 추가 키워드 추출
        content_keywords = await self._extract_keywords_from_content(content, metadata.language)
        keywords.update(content_keywords)
        
        return list(keywords)
    
    async def _extract_keywords_from_content(self, content: str, language: Language) -> List[str]:
        """코드 내용에서 키워드 추출"""
        keywords = set()
        
        # 언어별 키워드 추출 전략
        if language == Language.JAVA:
            # Java 키워드 패턴
            java_patterns = [
                r'\b(String|Integer|Boolean|List|Map|Set)\b',
                r'\b(public|private|protected|static|final)\b',
                r'\b(class|interface|enum|extends|implements)\b',
                r'\b(@\w+)\b'  # 어노테이션
            ]
            for pattern in java_patterns:
                import re
                matches = re.findall(pattern, content)
                keywords.update(matches)
        
        elif language == Language.PYTHON:
            # Python 키워드 패턴
            python_patterns = [
                r'\bdef\s+(\w+)',  # 함수명
                r'\bclass\s+(\w+)',  # 클래스명
                r'\bimport\s+(\w+)',  # 임포트
                r'\bfrom\s+(\w+)',  # from 임포트
                r'@(\w+)'  # 데코레이터
            ]
            for pattern in python_patterns:
                import re
                matches = re.findall(pattern, content)
                keywords.update(matches)
        
        return list(keywords)
    
    async def _generate_semantic_tags(self, metadata: CodeMetadata) -> List[str]:
        """의미적 태그 생성"""
        tags = []
        
        # 코드 타입 기반 태그
        tags.append(f"type:{metadata.code_type.value}")
        tags.append(f"lang:{metadata.language.value}")
        
        # 접근 제한자 태그
        if 'public' in metadata.modifiers:
            tags.append("access:public")
        elif 'private' in metadata.modifiers:
            tags.append("access:private")
        elif 'protected' in metadata.modifiers:
            tags.append("access:protected")
        
        # 정적 여부
        if 'static' in metadata.modifiers:
            tags.append("scope:static")
        else:
            tags.append("scope:instance")
        
        # 상속 관계
        if metadata.extends:
            tags.append("pattern:inheritance")
        
        if metadata.implements:
            tags.append("pattern:implementation")
        
        # 복잡도 기반 태그
        if metadata.complexity_score > 0:
            if metadata.complexity_score > 10:
                tags.append("complexity:high")
            elif metadata.complexity_score > 5:
                tags.append("complexity:medium")
            else:
                tags.append("complexity:low")
        
        # 특수 패턴 인식
        if metadata.name.startswith("test"):
            tags.append("purpose:test")
        elif metadata.name.startswith("get"):
            tags.append("purpose:getter")
        elif metadata.name.startswith("set"):
            tags.append("purpose:setter")
        elif metadata.name.startswith("is") or metadata.name.startswith("has"):
            tags.append("purpose:predicate")
        
        return tags
    
    async def _analyze_relationships(self, metadata: CodeMetadata) -> Dict[str, Any]:
        """관계 분석"""
        relationships = {}
        
        # 상위-하위 관계
        if metadata.parent_class:
            relationships["parent"] = metadata.parent_class
        
        # 상속 관계
        if metadata.extends:
            relationships["extends"] = metadata.extends
        
        # 구현 관계
        if metadata.implements:
            relationships["implements"] = metadata.implements
        
        # 의존성 관계
        dependencies = []
        for param in metadata.parameters:
            if param.get('type'):
                dependencies.append(param['type'])
        
        if metadata.return_type:
            dependencies.append(metadata.return_type)
        
        if dependencies:
            relationships["dependencies"] = dependencies
        
        # 네임스페이스 관계
        if metadata.namespace:
            relationships["namespace"] = metadata.namespace
        
        return relationships
    
    def _convert_legacy_chunk_to_metadata(self, chunk: Dict[str, Any]) -> CodeMetadata:
        """기존 청크를 CodeMetadata로 변환"""
        # 언어 매핑
        language_map = {
            "java": Language.JAVA,
            "python": Language.PYTHON,
            "javascript": Language.JAVASCRIPT
        }
        
        # 코드 타입 매핑
        code_type_map = {
            "class": CodeType.CLASS,
            "method": CodeType.METHOD,
            "function": CodeType.FUNCTION,
            "interface": CodeType.INTERFACE
        }
        
        return CodeMetadata(
            file_path=chunk.get("file_path", ""),
            language=language_map.get(chunk.get("language", "").lower(), Language.JAVA),
            code_type=code_type_map.get(chunk.get("code_type", "").lower(), CodeType.METHOD),
            name=chunk.get("name", "unknown"),
            line_start=chunk.get("line_start", 1),
            line_end=chunk.get("line_end", 1),
            namespace=chunk.get("namespace"),
            parent_class=chunk.get("parent_class"),
            modifiers=chunk.get("modifiers", []),
            annotations=chunk.get("annotations", []),
            parameters=chunk.get("parameters", []),
            return_type=chunk.get("return_type"),
            extends=chunk.get("extends"),
            implements=chunk.get("implements", []),
            keywords=chunk.get("keywords", [])
        )
    
    def _generate_document_id(self, metadata: CodeMetadata) -> str:
        """Document ID 생성"""
        id_string = f"{metadata.file_path}:{metadata.name}:{metadata.line_start}:{metadata.line_end}"
        return hashlib.md5(id_string.encode()).hexdigest()
    
    def _create_node_parser(self) -> SimpleNodeParser:
        """Node Parser 생성"""
        if self.config.chunking_strategy == ChunkingStrategy.SEMANTIC:
            return CodeSplitter(
                language=self.config.chunking_strategy,
                chunk_size=self.config.max_chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )
        else:
            return SimpleNodeParser(
                chunk_size=self.config.max_chunk_size,
                chunk_overlap=self.config.chunk_overlap
            )
    
    def _update_statistics(self, statistics: Dict[str, int], metadata: CodeMetadata):
        """통계 업데이트"""
        if metadata.code_type == CodeType.CLASS:
            statistics["classes"] += 1
        elif metadata.code_type == CodeType.METHOD:
            statistics["methods"] += 1
        elif metadata.code_type == CodeType.FUNCTION:
            statistics["functions"] += 1
        elif metadata.code_type == CodeType.INTERFACE:
            statistics["interfaces"] += 1
        
        statistics["total_lines"] += (metadata.line_end - metadata.line_start + 1)
```

### 2. Document Builder 서비스

```python
# app/retriever/document_service.py
from typing import List, Dict, Any, Optional
from .document_builder import DocumentBuilder, DocumentBuildConfig, DocumentBuildResult, EnhancedDocument
from .ast_parser import ParseResult
from app.core.clients import EmbeddingClient

class DocumentService:
    """Document 생성 서비스"""
    
    def __init__(self, embedding_client: EmbeddingClient):
        self.embedding_client = embedding_client
        self.builder = DocumentBuilder()
    
    async def create_documents_from_parse_result(
        self, 
        parse_result: ParseResult,
        config: Optional[DocumentBuildConfig] = None
    ) -> DocumentBuildResult:
        """파싱 결과로부터 Document 생성"""
        if config:
            self.builder.config = config
        
        result = await self.builder.build_from_parse_result(parse_result)
        
        # 임베딩 생성 (옵션)
        if self.embedding_client:
            await self._generate_embeddings(result.documents)
        
        return result
    
    async def create_documents_from_legacy_chunks(
        self,
        chunks: List[Dict[str, Any]],
        config: Optional[DocumentBuildConfig] = None
    ) -> DocumentBuildResult:
        """기존 청크로부터 Document 생성"""
        if config:
            self.builder.config = config
        
        result = await self.builder.build_from_legacy_chunks(chunks)
        
        # 임베딩 생성 (옵션)
        if self.embedding_client:
            await self._generate_embeddings(result.documents)
        
        return result
    
    async def _generate_embeddings(self, documents: List[EnhancedDocument]):
        """Document들에 대한 임베딩 생성"""
        texts = [doc.enhanced_content for doc in documents]
        
        try:
            embedding_response = await self.embedding_client.embed_bulk({"texts": texts})
            embeddings = [emb["embedding"] for emb in embedding_response["embeddings"]]
            
            # Document에 임베딩 추가
            for doc, embedding in zip(documents, embeddings):
                doc.document.embedding = embedding
                doc.text_node.embedding = embedding
                
        except Exception as e:
            # 임베딩 생성 실패 시 로그만 남기고 계속 진행
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"임베딩 생성 실패: {e}")
```

## ✅ 완료 조건

1. **Document Builder 구현**: 모든 핵심 기능이 구현되고 테스트 통과
2. **컨텐츠 강화**: 메타데이터 기반 컨텐츠 강화가 정상 동작
3. **키워드 추출**: 검색 최적화를 위한 키워드 추출이 정확함
4. **의미적 태그 생성**: 의미적 분류를 위한 태그가 생성됨
5. **관계 분석**: 코드 간 관계가 정확히 분석됨
6. **기존 코드 호환**: 기존 indexing 모듈의 청크와 호환됨
7. **성능 최적화**: 대용량 파일 처리 시 성능이 양호함

## 📋 다음 Task와의 연관관계

- **Task 10**: 이 Task에서 생성한 EnhancedDocument들을 Vector Index에 저장
- **Task 11**: BM25 Index에 키워드 기반 검색을 위한 데이터 저장
- **Task 12**: Hybrid Retriever에서 강화된 메타데이터 활용

## 🧪 테스트 계획

```python
# tests/unit/retriever/test_document_builder.py
async def test_build_from_parse_result():
    """파싱 결과로부터 Document 빌드 테스트"""
    builder = DocumentBuilder()
    result = await builder.build_from_parse_result(sample_parse_result)
    assert len(result.documents) > 0
    assert result.total_documents > 0

async def test_enhance_content():
    """컨텐츠 강화 테스트"""
    builder = DocumentBuilder()
    enhanced = await builder._enhance_content(sample_code, sample_metadata)
    assert "File:" in enhanced
    assert "Language:" in enhanced

async def test_extract_search_keywords():
    """검색 키워드 추출 테스트"""
    builder = DocumentBuilder()
    keywords = await builder._extract_search_keywords(sample_code, sample_metadata)
    assert len(keywords) > 0
    assert sample_metadata.name in keywords

async def test_legacy_chunk_conversion():
    """기존 청크 변환 테스트"""
    builder = DocumentBuilder()
    result = await builder.build_from_legacy_chunks(sample_legacy_chunks)
    assert len(result.documents) == len(sample_legacy_chunks)
```

이 Task는 검색 품질 향상을 위한 핵심 구성요소입니다. 풍부한 메타데이터와 강화된 컨텐츠를 통해 더 정확한 검색 결과를 제공할 수 있습니다. 