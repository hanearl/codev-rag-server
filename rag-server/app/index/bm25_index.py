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
import uuid
import logging
from datetime import datetime

from .base_index import BaseIndex, IndexedDocument
from app.retriever.document_builder import EnhancedDocument

logger = logging.getLogger(__name__)

# NLTK 데이터 다운로드 (최초 실행 시)
def _download_nltk_data():
    """NLTK 데이터 다운로드 (멱등성 보장)"""
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        logger.info("NLTK punkt 토크나이저 다운로드 중...")
        nltk.download('punkt', quiet=True)

    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        logger.info("NLTK stopwords 데이터 다운로드 중...")
        nltk.download('stopwords', quiet=True)

# 초기 다운로드 실행
_download_nltk_data()


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
            'catch', 'throw', 'throws', 'new', 'this', 'super',
            'const', 'let', 'var', 'function', 'def', 'async', 'await',
            'true', 'false', 'null', 'undefined', 'none'
        }
        self.stop_words.update(self.code_stop_words)
    
    def tokenize(self, text: str) -> List[str]:
        """텍스트 토큰화"""
        if not text or not text.strip():
            return []
        
        try:
            # 코드 패턴 전처리
            text = self._preprocess_code(text)
            
            # 기본 토큰화
            tokens = word_tokenize(text.lower())
            
            # 필터링 및 스테밍
            filtered_tokens = []
            for token in tokens:
                # 불용어 및 특수문자 제거, 최소 길이 확인
                if (len(token) > 1 and 
                    token not in self.stop_words and
                    token.isalnum()):
                    
                    # 스테밍 적용
                    stemmed = self.stemmer.stem(token)
                    filtered_tokens.append(stemmed)
            
            return filtered_tokens
            
        except Exception as e:
            logger.warning(f"토큰화 실패: {e}, 원본 텍스트: {text[:100]}...")
            # 실패 시 간단한 fallback 토큰화
            return self._fallback_tokenize(text)
    
    def _preprocess_code(self, text: str) -> str:
        """코드 특화 전처리"""
        # CamelCase 분리 (getUserById -> get User By Id)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # snake_case 분리 (get_user_by_id -> get user by id)
        text = re.sub(r'_', ' ', text)
        
        # 특수 문자를 공백으로 치환 (중괄호, 괄호, 세미콜론 등)
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # 연속 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _fallback_tokenize(self, text: str) -> List[str]:
        """Fallback 토큰화 (NLTK 실패 시)"""
        # 간단한 정규표현식 기반 토큰화
        text = self._preprocess_code(text)
        tokens = re.findall(r'\b\w+\b', text.lower())
        
        # 기본 필터링
        filtered = [
            token for token in tokens 
            if len(token) > 1 and token not in self.code_stop_words
        ]
        
        return filtered[:50]  # 최대 50개로 제한


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
        try:
            # 기존 인덱스 로드 시도
            if await self._load_existing_index():
                logger.info(f"기존 BM25 인덱스 로드 완료: {len(self.nodes)}개 문서")
                return
            
            # 새 인덱스 초기화
            self.nodes = []
            self.documents_map = {}
            self._build_retriever()
            logger.info("새로운 BM25 인덱스 초기화 완료")
            
        except Exception as e:
            logger.error(f"BM25 인덱스 초기화 실패: {e}")
            raise
    
    async def add_documents(self, documents: List[Union[EnhancedDocument, Dict[str, Any]]]) -> List[str]:
        """문서 추가"""
        if not documents:
            return []
        
        added_ids = []
        new_nodes = []
        
        try:
            for doc in documents:
                if isinstance(doc, EnhancedDocument):
                    # EnhancedDocument 처리
                    enhanced_text = self._create_enhanced_text(doc)
                    text_node = TextNode(
                        text=enhanced_text,
                        metadata=doc.metadata.model_dump(),
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
            
            logger.info(f"BM25 인덱스에 {len(added_ids)}개 문서 추가 완료")
            return added_ids
            
        except Exception as e:
            logger.error(f"문서 추가 실패: {e}")
            raise
    
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
                if isinstance(param, dict) and param.get('type'):
                    text_parts.append(param['type'])
                elif isinstance(param, str):
                    text_parts.append(param)
            
            # 반환 타입 추가
            if metadata.return_type:
                text_parts.append(metadata.return_type)
            
            # 상속/구현 관계
            if metadata.extends:
                text_parts.append(metadata.extends)
            
            if metadata.implements:
                text_parts.extend(metadata.implements)
            
            # 검색 키워드 추가
            if hasattr(doc, 'search_keywords') and doc.search_keywords:
                text_parts.extend(doc.search_keywords)
            
            # 의미적 태그 추가
            if hasattr(doc, 'semantic_tags') and doc.semantic_tags:
                text_parts.extend(doc.semantic_tags)
        
        return ' '.join(filter(None, text_parts))
    
    async def _create_text_node_from_dict(self, doc_dict: Dict[str, Any]) -> TextNode:
        """딕셔너리에서 TextNode 생성"""
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
            
            text = ' '.join(filter(None, enhanced_parts))
        
        # 인덱싱 시간 추가
        metadata['indexed_at'] = datetime.now().isoformat()
        
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
        
        try:
            # 커스텀 토크나이저를 사용하여 BM25Retriever 생성
            self.retriever = BM25Retriever.from_defaults(
                nodes=self.nodes,
                tokenizer=self.tokenizer.tokenize,
                similarity_top_k=self.config.top_k
            )
            
            logger.debug(f"BM25 Retriever 구성 완료: {len(self.nodes)}개 노드")
            
        except Exception as e:
            logger.error(f"BM25 Retriever 구성 실패: {e}")
            self.retriever = None
    
    async def search(self, query: str, limit: int = 10, filters: Dict[str, Any] = None) -> List[IndexedDocument]:
        """BM25 검색"""
        if not self.retriever or not query.strip():
            return []
        
        try:
            # 검색 실행
            nodes_with_scores = self.retriever.retrieve(query)
            
            # 결과 변환
            results = []
            for node_with_score in nodes_with_scores:
                if len(results) >= limit:
                    break
                    
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
            
            logger.debug(f"BM25 검색 완료: 쿼리='{query}', 결과={len(results)}개")
            return results
            
        except Exception as e:
            logger.error(f"BM25 검색 실패: {e}")
            return []
    
    async def search_with_scores(self, query: str, limit: int = 10, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """점수와 함께 BM25 검색"""
        if not self.retriever or not query.strip():
            return []
        
        try:
            nodes_with_scores = self.retriever.retrieve(query)
            
            results = []
            for node_with_score in nodes_with_scores:
                if len(results) >= limit:
                    break
                    
                node = node_with_score.node
                
                # 필터 적용
                if filters and not self._apply_filters(node.metadata, filters):
                    continue
                
                result = {
                    'id': node.id_,
                    'content': node.text,
                    'metadata': node.metadata,
                    'score': float(node_with_score.score) if node_with_score.score else 0.0,
                    'source': 'bm25'
                }
                results.append(result)
            
            logger.debug(f"BM25 점수 검색 완료: 쿼리='{query}', 결과={len(results)}개")
            return results
            
        except Exception as e:
            logger.error(f"점수별 BM25 검색 실패: {e}")
            return []
    
    def _apply_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """필터 적용"""
        try:
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
            
        except Exception as e:
            logger.warning(f"필터 적용 실패: {e}")
            return False
    
    async def update_document(self, doc_id: str, document: Dict[str, Any]) -> bool:
        """문서 업데이트"""
        try:
            # 기존 문서 제거
            await self.delete_document(doc_id)
            
            # 새 문서 추가
            updated_doc = document.copy()
            updated_doc['id'] = doc_id
            added_ids = await self.add_documents([updated_doc])
            
            success = len(added_ids) > 0
            if success:
                logger.info(f"문서 업데이트 완료: {doc_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"문서 업데이트 실패 ({doc_id}): {e}")
            return False
    
    async def delete_document(self, doc_id: str) -> bool:
        """문서 삭제"""
        try:
            # 노드 목록에서 제거
            original_count = len(self.nodes)
            self.nodes = [node for node in self.nodes if node.id_ != doc_id]
            removed_count = original_count - len(self.nodes)
            
            # 문서 맵에서 제거
            if doc_id in self.documents_map:
                del self.documents_map[doc_id]
            
            # Retriever 재구성
            self._build_retriever()
            
            # 인덱스 저장
            await self._save_index()
            
            if removed_count > 0:
                logger.info(f"문서 삭제 완료: {doc_id}")
            
            return removed_count > 0
            
        except Exception as e:
            logger.error(f"문서 삭제 실패 ({doc_id}): {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """인덱스 통계 정보"""
        try:
            total_docs = len(self.nodes)
            
            if total_docs == 0:
                return {
                    "total_documents": 0,
                    "total_tokens": 0,
                    "average_tokens_per_doc": 0.0,
                    "language_distribution": {},
                    "bm25_parameters": {
                        "k1": self.config.k1,
                        "b": self.config.b
                    },
                    "index_path": str(self.config.index_path)
                }
            
            # 토큰 수 계산
            total_tokens = 0
            for node in self.nodes:
                try:
                    tokens = self.tokenizer.tokenize(node.text)
                    total_tokens += len(tokens)
                except:
                    # 토큰화 실패 시 대략적인 추정
                    total_tokens += len(node.text.split())
            
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
            
        except Exception as e:
            logger.error(f"통계 정보 조회 실패: {e}")
            return {
                "total_documents": 0,
                "total_tokens": 0,
                "error": str(e)
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
            
            # 문서 맵 저장 (pickle은 선택적)
            if self.documents_map:
                docs_map_file = self.config.index_path / "documents_map.pkl"
                with open(docs_map_file, 'wb') as f:
                    pickle.dump(self.documents_map, f)
            
            logger.debug(f"BM25 인덱스 저장 완료: {len(self.nodes)}개 노드")
            
        except Exception as e:
            logger.error(f"인덱스 저장 실패: {e}")
    
    async def _load_existing_index(self) -> bool:
        """기존 인덱스 로드"""
        try:
            nodes_file = self.config.index_path / "nodes.json"
            docs_map_file = self.config.index_path / "documents_map.pkl"
            
            if not nodes_file.exists():
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
            
            # 문서 맵 로드 (선택적)
            self.documents_map = {}
            if docs_map_file.exists():
                try:
                    with open(docs_map_file, 'rb') as f:
                        self.documents_map = pickle.load(f)
                except Exception as e:
                    logger.warning(f"문서 맵 로드 실패: {e}")
            
            # Retriever 구성
            self._build_retriever()
            
            return True
            
        except Exception as e:
            logger.warning(f"기존 인덱스 로드 실패: {e}")
            return False 