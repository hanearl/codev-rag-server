"""
외부 서비스 클라이언트 구현
"""
import httpx
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, VectorParams, Distance
import uuid
import logging

from .exceptions import EmbeddingServiceError, LLMServiceError, VectorDBError
from .config import settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """임베딩 서비스 클라이언트"""
    
    def __init__(self, base_url: str = None, timeout: float = None, max_retries: int = None):
        self.base_url = (base_url or settings.embedding_server_url).rstrip('/')
        self.timeout = timeout or settings.request_timeout
        self.max_retries = max_retries or settings.max_retries
    
    async def embed_single(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """단일 텍스트 임베딩"""
        url = f"{self.base_url}/embedding/embed"
        return await self._make_request("POST", url, json=request)
    
    async def embed_bulk(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """벌크 텍스트 임베딩"""
        url = f"{self.base_url}/embedding/embed/bulk"
        return await self._make_request("POST", url, json=request)
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """HTTP 요청 및 재시도 로직"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method, url, timeout=self.timeout, **kwargs
                    )
                    response.raise_for_status()
                    return response.json()
            
            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code < 500:
                    # 4xx 에러는 재시도하지 않음
                    break
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # 지수 백오프
            
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
        
        logger.error(f"Embedding 서비스 요청 실패: {last_exception}")
        raise EmbeddingServiceError(f"요청 실패: {last_exception}")


class LLMClient:
    """LLM 서비스 클라이언트"""
    
    def __init__(self, base_url: str = None, timeout: float = None, max_retries: int = None):
        self.base_url = (base_url or settings.llm_server_url).rstrip('/')
        self.timeout = timeout or 60.0  # LLM은 더 긴 타임아웃
        self.max_retries = max_retries or settings.max_retries
    
    async def chat_completion(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """채팅 완성 요청 (OpenAI 호환)"""
        url = f"{self.base_url}/v1/chat/completions"
        return await self._make_request("POST", url, json=request)
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """HTTP 요청 및 재시도 로직"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method, url, timeout=self.timeout, **kwargs
                    )
                    response.raise_for_status()
                    return response.json()
            
            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code < 500:
                    break
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
            
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
        
        logger.error(f"LLM 서비스 요청 실패: {last_exception}")
        raise LLMServiceError(f"요청 실패: {last_exception}")


class VectorClient:
    """벡터 DB (Qdrant) 클라이언트"""
    
    def __init__(self, host: str = None, port: int = None):
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.client = QdrantClient(host=self.host, port=self.port)
    
    def create_collection(self, collection_name: str, vector_size: int) -> bool:
        """컬렉션 생성"""
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            return True
        except Exception as e:
            logger.error(f"컬렉션 생성 실패: {e}")
            raise VectorDBError(f"컬렉션 생성 실패: {e}")
    
    def insert_code_embedding(self, collection_name: str, 
                             embedding: List[float], metadata: Dict[str, Any]) -> str:
        """코드 임베딩 삽입"""
        try:
            point_id = str(uuid.uuid4())
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=metadata
            )
            
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            return point_id
        except Exception as e:
            logger.error(f"임베딩 삽입 실패: {e}")
            raise VectorDBError(f"임베딩 삽입 실패: {e}")
    
    def delete_by_file_path(self, collection_name: str, file_path: str) -> int:
        """파일 경로로 임베딩 삭제"""
        try:
            result = self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="file_path",
                            match={"value": file_path}
                        )
                    ]
                )
            )
            return result.operation_id if result else 0
        except Exception as e:
            logger.error(f"임베딩 삭제 실패: {e}")
            raise VectorDBError(f"임베딩 삭제 실패: {e}")
    
    def hybrid_search(self, collection_name: str, query_embedding: List[float], 
                     keywords: Optional[List[str]] = None, 
                     limit: int = 10) -> List[Dict[str, Any]]:
        """하이브리드 검색 (벡터 + BM25 키워드)"""
        try:
            # 벡터 검색 (더 많은 결과 가져와서 키워드 필터링)
            search_limit = max(limit * 3, 50)  # BM25 필터링을 위해 더 많은 결과
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=search_limit,
                with_payload=True,
                with_vectors=False
            )
            
            # 결과 변환
            results = []
            documents = []  # BM25용 문서 컬렉션
            
            for scored_point in search_result:
                result = {
                    "id": str(scored_point.id),
                    "vector_score": scored_point.score,
                    **scored_point.payload
                }
                results.append(result)
                
                # BM25를 위한 문서 토큰 준비
                doc_tokens = []
                if 'keywords' in scored_point.payload:
                    doc_tokens.extend(scored_point.payload['keywords'])
                if 'code_content' in scored_point.payload:
                    # 코드 내용도 간단히 토큰화
                    code_tokens = self._tokenize_code_content(scored_point.payload['code_content'])
                    doc_tokens.extend(code_tokens)
                
                documents.append(doc_tokens)
            
            # BM25 키워드 점수 계산
            if keywords and results:
                keyword_scores = self._calculate_bm25_scores(keywords, documents)
                
                for i, result in enumerate(results):
                    if i < len(keyword_scores):
                        result["keyword_score"] = keyword_scores[i]
                        result["combined_score"] = (result["vector_score"] * 0.7 + keyword_scores[i] * 0.3)
                    else:
                        result["keyword_score"] = 0.0
                        result["combined_score"] = result["vector_score"]
            else:
                for result in results:
                    result["keyword_score"] = 0.0
                    result["combined_score"] = result["vector_score"]
            
            # 결합 점수로 재정렬 후 limit 적용
            results.sort(key=lambda x: x["combined_score"], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"하이브리드 검색 실패: {e}")
            raise VectorDBError(f"하이브리드 검색 실패: {e}")
    
    def query_chunks(self, collection_name: str, 
                    file_path: Optional[str] = None,
                    code_type: Optional[str] = None,
                    language: Optional[str] = None,
                    keyword: Optional[str] = None,
                    offset: int = 0,
                    limit: int = 10) -> Tuple[List[Dict[str, Any]], int]:
        """청크 조회 (필터링 및 페이지네이션 지원)"""
        try:
            # 필터 조건 구성
            must_conditions = []
            
            if file_path:
                must_conditions.append(
                    FieldCondition(key="file_path", match={"value": file_path})
                )
            
            if code_type:
                must_conditions.append(
                    FieldCondition(key="code_type", match={"value": code_type})
                )
            
            if language:
                must_conditions.append(
                    FieldCondition(key="language", match={"value": language})
                )
            
            if keyword:
                must_conditions.append(
                    FieldCondition(key="keywords", match={"any": [keyword]})
                )
            
            # 필터 설정
            query_filter = None
            if must_conditions:
                query_filter = Filter(must=must_conditions)
            
            # 스크롤 검색으로 데이터 조회
            scroll_result = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=query_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            # 전체 개수 조회
            count_result = self.client.count(
                collection_name=collection_name,
                count_filter=query_filter
            )
            
            # 결과 변환
            chunks = []
            for point in scroll_result[0]:  # scroll_result is (points, next_page_offset)
                chunk_data = {
                    "id": str(point.id),
                    **point.payload
                }
                chunks.append(chunk_data)
            
            total_count = count_result.count
            
            return chunks, total_count
            
        except Exception as e:
            logger.error(f"청크 조회 실패: {e}")
            raise VectorDBError(f"청크 조회 실패: {e}")

    def _calculate_bm25_scores(self, query_keywords: List[str], 
                             documents: List[List[str]]) -> List[float]:
        """BM25를 사용한 키워드 점수 계산"""
        try:
            from app.features.search.bm25_scorer import BM25KeywordScorer
            
            if not documents or not query_keywords:
                return [0.0] * len(documents)
            
            # BM25 스코어러 초기화 및 학습
            bm25 = BM25KeywordScorer()
            bm25.fit(documents)
            
            # 모든 문서에 대한 점수 계산
            scores = bm25.get_scores(query_keywords)
            
            # 0-1 범위로 정규화
            normalized_scores = bm25.normalize_scores(scores)
            
            return normalized_scores
            
        except Exception as e:
            logger.warning(f"BM25 점수 계산 실패, 기본 방식 사용: {e}")
            # BM25 실패 시 기본 Jaccard 방식 fallback
            return [self._calculate_keyword_score_fallback(doc, query_keywords) 
                   for doc in documents]
    
    def _calculate_keyword_score_fallback(self, doc_keywords: List[str], 
                                        query_keywords: List[str]) -> float:
        """키워드 매칭 점수 계산 (Jaccard 유사도 fallback)"""
        if not doc_keywords or not query_keywords:
            return 0.0
        
        doc_set = set(keyword.lower() for keyword in doc_keywords)
        query_set = set(keyword.lower() for keyword in query_keywords)
        
        intersection = len(doc_set.intersection(query_set))
        union = len(doc_set.union(query_set))
        
        return intersection / union if union > 0 else 0.0
    
    def _tokenize_code_content(self, code_content: str) -> List[str]:
        """코드 내용을 간단히 토큰화"""
        import re
        
        # 기본적인 코드 토큰화 (camelCase, snake_case 분해 포함)
        # CamelCase 분해
        camel_split = re.sub(r'([a-z])([A-Z])', r'\1 \2', code_content)
        # snake_case 분해  
        snake_split = camel_split.replace('_', ' ')
        # 특수문자 제거 및 단어 추출
        words = re.findall(r'\b[a-zA-Z]{2,}\b', snake_split.lower())
        
        # 프로그래밍 불용어 제거
        stop_words = {'def', 'class', 'if', 'else', 'for', 'while', 'try', 'catch',
                     'public', 'private', 'static', 'void', 'int', 'string', 'bool'}
        
        return [word for word in words if word not in stop_words]


class ExternalServiceClients:
    """외부 서비스 클라이언트 팩토리"""
    
    def __init__(self):
        self._embedding_client: Optional[EmbeddingClient] = None
        self._llm_client: Optional[LLMClient] = None
        self._vector_client: Optional[VectorClient] = None
    
    @property
    def embedding(self) -> EmbeddingClient:
        """임베딩 클라이언트 인스턴스 (싱글톤)"""
        if self._embedding_client is None:
            self._embedding_client = EmbeddingClient()
        return self._embedding_client
    
    @property
    def llm(self) -> LLMClient:
        """LLM 클라이언트 인스턴스 (싱글톤)"""
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client
    
    @property
    def vector(self) -> VectorClient:
        """벡터 DB 클라이언트 인스턴스 (싱글톤)"""
        if self._vector_client is None:
            self._vector_client = VectorClient()
        return self._vector_client


# 전역 클라이언트 인스턴스
external_clients = ExternalServiceClients() 