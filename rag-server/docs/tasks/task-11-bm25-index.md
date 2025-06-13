# Task 11: BM25 Index 구현

## 📋 작업 개요
LlamaIndex BM25Retriever를 활용하여 키워드 기반 정밀 검색을 지원하는 BM25 Index를 구현합니다. 기존 BM25 스코어링 로직을 LlamaIndex 아키텍처로 통합합니다.

## 🎯 작업 목표
- LlamaIndex BM25Retriever 기반 키워드 검색 시스템 구축
- 코드 특화 토큰화 및 전처리 최적화
- 기존 BM25 스코어링 로직과의 호환성 보장
- 다국어 코드 지원 및 성능 최적화

## 🔗 의존성
- **선행 Task**: Task 9 (Document Builder 구현)
- **활용할 기존 코드**: `app/features/search/bm25_scorer.py`
- **병렬 개발**: Task 10 (Vector Index 구현)

## 🔧 구현 사항

### 1. BM25 Index 인터페이스 구현

```python
# app/index/bm25_index.py
from typing import List, Dict, Any, Optional, Union
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.schema import TextNode, NodeWithScore
from llama_index.core import Document
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import re
import json
import pickle
from pathlib import Path
from .base_index import BaseIndex, IndexedDocument
from app.retriever.document_builder import EnhancedDocument

# NLTK 데이터 다운로드 (최초 실행 시)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

class CodeTokenizer:
    """코드 특화 토크나이저"""
    
    def __init__(self, language: str = "english"):
        self.language = language
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words(language))
        
        # 코드 특화 불용어 추가
        self.code_stop_words = {
            'public', 'private', 'protected', 'static', 'final', 'void',
            'class', 'interface', 'extends', 'implements', 'import',
            'package', 'return', 'if', 'else', 'for', 'while', 'try',
            'catch', 'throw', 'throws', 'new', 'this', 'super'
        }
        self.stop_words.update(self.code_stop_words)
    
    def tokenize(self, text: str) -> List[str]:
        """텍스트 토큰화"""
        # 코드 패턴 전처리
        text = self._preprocess_code(text)
        
        # 기본 토큰화
        tokens = word_tokenize(text.lower())
        
        # 필터링 및 스테밍
        filtered_tokens = []
        for token in tokens:
            # 불용어 및 특수문자 제거
            if (len(token) > 1 and 
                token not in self.stop_words and
                token.isalnum()):
                
                # 스테밍 적용
                stemmed = self.stemmer.stem(token)
                filtered_tokens.append(stemmed)
        
        return filtered_tokens
    
    def _preprocess_code(self, text: str) -> str:
        """코드 특화 전처리"""
        # CamelCase 분리
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # snake_case 분리
        text = re.sub(r'_', ' ', text)
        
        # 특수 문자 공백으로 치환
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # 숫자 제거 (선택적)
        # text = re.sub(r'\d+', '', text)
        
        # 연속 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

class BM25IndexConfig:
    """BM25 Index 설정"""
    def __init__(
        self,
        k1: float = 1.2,
        b: float = 0.75,
        top_k: int = 10,
        language: str = "english",
        index_path: str = "data/bm25_index",
        use_stemming: bool = True,
        include_metadata: bool = True,
        metadata_weight: float = 0.3  # 메타데이터 가중치
    ):
        self.k1 = k1
        self.b = b
        self.top_k = top_k
        self.language = language
        self.index_path = Path(index_path)
        self.use_stemming = use_stemming
        self.include_metadata = include_metadata
        self.metadata_weight = metadata_weight

class CodeBM25Index(BaseIndex):
    """코드 BM25 인덱스"""
    
    def __init__(self, config: BM25IndexConfig = None):
        self.config = config or BM25IndexConfig()
        self.tokenizer = CodeTokenizer(self.config.language)
        self.retriever = None
        self.nodes = []
        self.documents_map = {}  # ID -> EnhancedDocument 매핑
        
        # 인덱스 저장 경로 생성
        self.config.index_path.mkdir(parents=True, exist_ok=True)
    
    async def setup(self):
        """인덱스 초기화"""
        # 기존 인덱스 로드 시도
        if await self._load_existing_index():
            return
        
        # 새 인덱스 초기화
        self.nodes = []
        self.documents_map = {}
        self._build_retriever()
    
    async def add_documents(self, documents: List[Union[EnhancedDocument, Dict[str, Any]]]) -> List[str]:
        """문서 추가"""
        added_ids = []
        new_nodes = []
        
        for doc in documents:
            if isinstance(doc, EnhancedDocument):
                # EnhancedDocument 처리
                enhanced_text = self._create_enhanced_text(doc)
                text_node = TextNode(
                    text=enhanced_text,
                    metadata=doc.metadata.dict(),
                    id_=doc.text_node.id_
                )
                
                new_nodes.append(text_node)
                self.documents_map[text_node.id_] = doc
                added_ids.append(text_node.id_)
                
            else:
                # Dict 형태의 문서 처리
                node = await self._create_text_node_from_dict(doc)
                new_nodes.append(node)
                added_ids.append(node.id_)
        
        # 기존 노드에 추가
        self.nodes.extend(new_nodes)
        
        # Retriever 재구성
        self._build_retriever()
        
        # 인덱스 저장
        await self._save_index()
        
        return added_ids
    
    def _create_enhanced_text(self, doc: EnhancedDocument) -> str:
        """강화된 텍스트 생성"""
        text_parts = []
        
        # 기본 코드 내용
        text_parts.append(doc.text_node.text)
        
        # 메타데이터 기반 텍스트 추가 (가중치 적용)
        if self.config.include_metadata:
            metadata = doc.metadata
            
            # 함수/클래스명 강조 (높은 가중치)
            for _ in range(3):  # 3번 반복으로 가중치 증가
                text_parts.append(metadata.name)
            
            # 키워드 추가
            if metadata.keywords:
                text_parts.extend(metadata.keywords)
            
            # 파라미터 타입 추가
            for param in metadata.parameters:
                if param.get('type'):
                    text_parts.append(param['type'])
            
            # 반환 타입 추가
            if metadata.return_type:
                text_parts.append(metadata.return_type)
            
            # 상속/구현 관계
            if metadata.extends:
                text_parts.append(metadata.extends)
            
            text_parts.extend(metadata.implements)
            
            # 검색 키워드 추가
            text_parts.extend(doc.search_keywords)
            
            # 의미적 태그 추가
            text_parts.extend(doc.semantic_tags)
        
        return ' '.join(text_parts)
    
    async def _create_text_node_from_dict(self, doc_dict: Dict[str, Any]) -> TextNode:
        """딕셔너리에서 TextNode 생성"""
        import uuid
        
        node_id = doc_dict.get('id', str(uuid.uuid4()))
        text = doc_dict.get('content', doc_dict.get('text', ''))
        metadata = doc_dict.get('metadata', {})
        
        # 메타데이터 기반 텍스트 강화
        if self.config.include_metadata and metadata:
            enhanced_parts = [text]
            
            # 메타데이터에서 텍스트 추가
            for key in ['name', 'function_name', 'keywords']:
                if key in metadata:
                    value = metadata[key]
                    if isinstance(value, list):
                        enhanced_parts.extend(value)
                    elif isinstance(value, str):
                        enhanced_parts.append(value)
            
            text = ' '.join(enhanced_parts)
        
        return TextNode(
            text=text,
            metadata=metadata,
            id_=node_id
        )
    
    def _build_retriever(self):
        """BM25 Retriever 구성"""
        if not self.nodes:
            self.retriever = None
            return
        
        # 커스텀 토크나이저를 사용하여 BM25Retriever 생성
        self.retriever = BM25Retriever.from_defaults(
            nodes=self.nodes,
            tokenizer=self.tokenizer.tokenize,
            similarity_top_k=self.config.top_k
        )
        
        # BM25 파라미터 설정
        if hasattr(self.retriever, 'bm25'):
            self.retriever.bm25.k1 = self.config.k1
            self.retriever.bm25.b = self.config.b
    
    async def search(self, query: str, limit: int = 10, filters: Dict[str, Any] = None) -> List[IndexedDocument]:
        """BM25 검색"""
        if not self.retriever:
            return []
        
        try:
            # 검색 실행
            nodes_with_scores = self.retriever.retrieve(query)
            
            # 결과 변환
            results = []
            for node_with_score in nodes_with_scores[:limit]:
                node = node_with_score.node
                
                # 필터 적용
                if filters and not self._apply_filters(node.metadata, filters):
                    continue
                
                indexed_doc = IndexedDocument(
                    id=node.id_,
                    content=node.text,
                    metadata=node.metadata,
                    indexed_at=node.metadata.get('indexed_at', '')
                )
                results.append(indexed_doc)
            
            return results
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"BM25 검색 실패: {e}")
            return []
    
    async def search_with_scores(self, query: str, limit: int = 10, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """점수와 함께 BM25 검색"""
        if not self.retriever:
            return []
        
        try:
            nodes_with_scores = self.retriever.retrieve(query)
            
            results = []
            for node_with_score in nodes_with_scores:
                node = node_with_score.node
                
                # 필터 적용
                if filters and not self._apply_filters(node.metadata, filters):
                    continue
                
                result = {
                    'id': node.id_,
                    'content': node.text,
                    'metadata': node.metadata,
                    'score': node_with_score.score,
                    'source': 'bm25'
                }
                results.append(result)
                
                if len(results) >= limit:
                    break
            
            return results
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"점수별 BM25 검색 실패: {e}")
            return []
    
    def _apply_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """필터 적용"""
        for key, value in filters.items():
            if key not in metadata:
                return False
            
            metadata_value = metadata[key]
            
            # 리스트 타입 처리
            if isinstance(metadata_value, list):
                if value not in metadata_value:
                    return False
            else:
                if metadata_value != value:
                    return False
        
        return True
    
    async def update_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """문서 업데이트"""
        try:
            # 기존 문서 제거
            await self.delete_document(doc_id)
            
            # 새 문서 추가
            updated_doc = document.copy()
            updated_doc['id'] = doc_id
            added_ids = await self.add_documents([updated_doc])
            
            return len(added_ids) > 0
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"문서 업데이트 실패 ({doc_id}): {e}")
            return False
    
    async def delete_document(self, doc_id: str) -> bool:
        """문서 삭제"""
        try:
            # 노드 목록에서 제거
            self.nodes = [node for node in self.nodes if node.id_ != doc_id]
            
            # 문서 맵에서 제거
            if doc_id in self.documents_map:
                del self.documents_map[doc_id]
            
            # Retriever 재구성
            self._build_retriever()
            
            # 인덱스 저장
            await self._save_index()
            
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"문서 삭제 실패 ({doc_id}): {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """인덱스 통계 정보"""
        total_docs = len(self.nodes)
        total_tokens = sum(len(self.tokenizer.tokenize(node.text)) for node in self.nodes)
        avg_tokens = total_tokens / total_docs if total_docs > 0 else 0
        
        # 언어별 문서 수 계산
        language_stats = {}
        for node in self.nodes:
            lang = node.metadata.get('language', 'unknown')
            language_stats[lang] = language_stats.get(lang, 0) + 1
        
        return {
            "total_documents": total_docs,
            "total_tokens": total_tokens,
            "average_tokens_per_doc": round(avg_tokens, 2),
            "language_distribution": language_stats,
            "bm25_parameters": {
                "k1": self.config.k1,
                "b": self.config.b
            },
            "index_path": str(self.config.index_path)
        }
    
    async def _save_index(self):
        """인덱스 저장"""
        try:
            # 노드 데이터 저장
            nodes_data = []
            for node in self.nodes:
                nodes_data.append({
                    'id': node.id_,
                    'text': node.text,
                    'metadata': node.metadata
                })
            
            nodes_file = self.config.index_path / "nodes.json"
            with open(nodes_file, 'w', encoding='utf-8') as f:
                json.dump(nodes_data, f, ensure_ascii=False, indent=2)
            
            # 문서 맵 저장
            docs_map_file = self.config.index_path / "documents_map.pkl"
            with open(docs_map_file, 'wb') as f:
                pickle.dump(self.documents_map, f)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"인덱스 저장 실패: {e}")
    
    async def _load_existing_index(self) -> bool:
        """기존 인덱스 로드"""
        try:
            nodes_file = self.config.index_path / "nodes.json"
            docs_map_file = self.config.index_path / "documents_map.pkl"
            
            if not (nodes_file.exists() and docs_map_file.exists()):
                return False
            
            # 노드 데이터 로드
            with open(nodes_file, 'r', encoding='utf-8') as f:
                nodes_data = json.load(f)
            
            self.nodes = []
            for node_data in nodes_data:
                node = TextNode(
                    text=node_data['text'],
                    metadata=node_data['metadata'],
                    id_=node_data['id']
                )
                self.nodes.append(node)
            
            # 문서 맵 로드
            with open(docs_map_file, 'rb') as f:
                self.documents_map = pickle.load(f)
            
            # Retriever 구성
            self._build_retriever()
            
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"기존 인덱스 로드 실패: {e}")
            return False
```

### 2. BM25 Index 서비스

```python
# app/index/bm25_service.py
from typing import List, Dict, Any, Optional
from .bm25_index import CodeBM25Index, BM25IndexConfig
from app.retriever.document_builder import EnhancedDocument
import logging

logger = logging.getLogger(__name__)

class BM25IndexService:
    """BM25 Index 서비스"""
    
    def __init__(self, config: BM25IndexConfig = None):
        self.config = config or BM25IndexConfig()
        self.index = CodeBM25Index(self.config)
        self._initialized = False
    
    async def initialize(self):
        """서비스 초기화"""
        if not self._initialized:
            await self.index.setup()
            self._initialized = True
            logger.info(f"BM25 Index 서비스 초기화 완료")
    
    async def index_documents(self, documents: List[EnhancedDocument]) -> Dict[str, Any]:
        """문서들 인덱싱"""
        await self.initialize()
        
        try:
            added_ids = await self.index.add_documents(documents)
            
            return {
                "success": True,
                "indexed_count": len(added_ids),
                "document_ids": added_ids,
                "index_type": "bm25"
            }
        except Exception as e:
            logger.error(f"BM25 문서 인덱싱 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "indexed_count": 0
            }
    
    async def search_keywords(
        self, 
        query: str, 
        limit: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """키워드 검색"""
        await self.initialize()
        return await self.index.search_with_scores(query, limit, filters)
    
    async def update_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """문서 업데이트"""
        await self.initialize()
        return await self.index.update_document(doc_id, document)
    
    async def delete_document(self, doc_id: str) -> bool:
        """문서 삭제"""
        await self.initialize()
        return await self.index.delete_document(doc_id)
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """인덱스 통계"""
        await self.initialize()
        return await self.index.get_stats()
    
    async def rebuild_index(self, documents: List[EnhancedDocument]) -> Dict[str, Any]:
        """인덱스 재구성"""
        try:
            # 기존 인덱스 초기화
            self.index.nodes = []
            self.index.documents_map = {}
            
            # 새 문서들로 인덱스 구성
            result = await self.index_documents(documents)
            
            logger.info(f"BM25 인덱스 재구성 완료: {result['indexed_count']}개 문서")
            return result
            
        except Exception as e:
            logger.error(f"BM25 인덱스 재구성 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """헬스 체크"""
        try:
            await self.initialize()
            stats = await self.get_index_stats()
            
            return {
                "status": "healthy",
                "index_type": "bm25",
                "document_count": stats.get("total_documents", 0),
                "total_tokens": stats.get("total_tokens", 0)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
```

## ✅ 완료 조건

1. **BM25 Index 구현**: LlamaIndex BM25Retriever 기반으로 완전히 구현됨
2. **코드 특화 토큰화**: 코드 특성을 고려한 토큰화가 정상 동작함
3. **문서 관리**: 추가, 업데이트, 삭제가 정상 동작함
4. **키워드 검색**: 정밀한 키워드 기반 검색이 지원됨
5. **필터링**: 메타데이터 기반 필터링이 정상 동작함
6. **성능 최적화**: 대용량 문서 처리 시 성능이 양호함
7. **인덱스 지속성**: 인덱스 저장/로드가 정상 동작함

## 📋 다음 Task와의 연관관계

- **Task 12**: Vector Index와 함께 Hybrid Retriever 구성
- **Task 15**: HybridRAG 서비스에서 BM25 검색 결과 활용

## 🧪 테스트 계획

```python
# tests/unit/index/test_bm25_index.py
async def test_bm25_index_setup():
    """BM25 Index 설정 테스트"""
    index = CodeBM25Index()
    await index.setup()
    assert index.tokenizer is not None

async def test_code_tokenizer():
    """코드 토크나이저 테스트"""
    tokenizer = CodeTokenizer()
    tokens = tokenizer.tokenize("getUserById")
    assert "get" in tokens
    assert "user" in tokens
    assert "id" in tokens

async def test_bm25_search():
    """BM25 검색 테스트"""
    service = BM25IndexService()
    results = await service.search_keywords("authentication method", limit=5)
    assert isinstance(results, list)

async def test_enhanced_text_creation():
    """강화된 텍스트 생성 테스트"""
    index = CodeBM25Index()
    enhanced_text = index._create_enhanced_text(sample_enhanced_document)
    assert sample_enhanced_document.metadata.name in enhanced_text
```

이 Task는 하이브리드 검색 시스템에서 정밀한 키워드 매칭을 담당하는 핵심 구성요소입니다. 코드 특화 토큰화를 통해 프로그래밍 언어의 특성을 고려한 정확한 검색을 제공합니다. 