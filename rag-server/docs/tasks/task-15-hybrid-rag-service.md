# Task 15: HybridRAG 서비스 구현

## 📋 작업 개요
모든 구성요소(Hybrid Retriever, PromptTemplate, LLMChain)를 통합하여 완전한 하이브리드 RAG 시스템을 구현합니다. 이는 기존 개별 모듈들을 대체하는 통합된 서비스입니다.

## 🎯 작업 목표
- 모든 RAG 구성요소의 완전한 통합
- 통합된 API 인터페이스 제공
- 워크플로우 최적화 및 성능 향상
- 기존 features 모듈들의 기능을 하나로 통합

## 🔗 의존성
- **선행 Task**: Task 12 (Hybrid Retriever), Task 13 (PromptTemplate), Task 14 (LLMChain)
- **대체할 기존 코드**: `app/features/generation`, `app/features/search`, `app/features/prompts`

## 🔧 구현 사항

### 1. 통합 HybridRAG 서비스

```python
# app/features/hybrid_rag/service.py
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel
import asyncio
import time
import logging

from app.retriever.hybrid_retriever import HybridRetrievalService
from app.index.vector_index import VectorIndexService, VectorIndexConfig
from app.index.bm25_index import BM25IndexService, BM25IndexConfig
from app.llm.llm_service import LLMService, LLMConfig
from app.llm.prompt_service import PromptService, PromptConfig, PromptType
from app.retriever.document_builder import DocumentService, EnhancedDocument

logger = logging.getLogger(__name__)

class RAGRequest(BaseModel):
    """RAG 요청 모델"""
    query: str
    language: str = "java"
    task_type: PromptType = PromptType.GENERAL_QA
    max_results: int = 5
    use_cache: bool = True
    include_metadata: bool = True
    
    # 검색 관련 설정
    vector_weight: Optional[float] = None
    bm25_weight: Optional[float] = None
    use_rrf: Optional[bool] = None
    
    # 컨텍스트 관련
    additional_context: Optional[Dict[str, Any]] = None
    
    # 스트리밍 설정
    streaming: bool = False

class RAGResponse(BaseModel):
    """RAG 응답 모델"""
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    processing_time_ms: int
    search_time_ms: int
    generation_time_ms: int
    cached: bool = False

class HybridRAGService:
    """통합 하이브리드 RAG 서비스"""
    
    def __init__(
        self,
        vector_config: VectorIndexConfig = None,
        bm25_config: BM25IndexConfig = None,
        llm_config: LLMConfig = None,
        prompt_config: PromptConfig = None
    ):
        # 개별 서비스 초기화
        self.vector_service = VectorIndexService(vector_config)
        self.bm25_service = BM25IndexService(bm25_config)
        self.llm_service = LLMService(llm_config, PromptService(prompt_config))
        self.document_service = DocumentService(None)  # embedding_client는 나중에 설정
        
        # 하이브리드 검색 서비스
        self.hybrid_retriever = None
        
        # 통계 및 캐싱
        self._request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_processing_time": 0,
            "cache_hits": 0
        }
        self._response_cache = {}
        self._initialized = False
    
    async def initialize(self):
        """서비스 초기화"""
        if self._initialized:
            return
        
        logger.info("HybridRAG 서비스 초기화 시작...")
        
        try:
            # 개별 서비스 초기화
            await self.vector_service.initialize()
            await self.bm25_service.initialize()
            
            # 하이브리드 검색 서비스 생성
            self.hybrid_retriever = HybridRetrievalService(
                vector_index=self.vector_service.index,
                bm25_index=self.bm25_service.index
            )
            await self.hybrid_retriever.setup()
            
            self._initialized = True
            logger.info("HybridRAG 서비스 초기화 완료")
            
        except Exception as e:
            logger.error(f"HybridRAG 서비스 초기화 실패: {e}")
            raise
    
    async def process_query(self, request: RAGRequest) -> RAGResponse:
        """쿼리 처리 - 메인 RAG 워크플로우"""
        await self.initialize()
        
        start_time = time.time()
        cache_key = self._generate_cache_key(request)
        
        # 캐시 확인
        if request.use_cache and cache_key in self._response_cache:
            cached_response = self._response_cache[cache_key]
            cached_response.cached = True
            self._request_stats["cache_hits"] += 1
            logger.info(f"캐시된 응답 반환: {cache_key[:16]}...")
            return cached_response
        
        try:
            # 1. 하이브리드 검색 실행
            search_start = time.time()
            
            if any([request.vector_weight, request.bm25_weight, request.use_rrf]):
                # 상세 검색 옵션이 있는 경우
                search_results = await self.hybrid_retriever.search_with_detailed_scores(
                    query=request.query,
                    limit=request.max_results,
                    vector_weight=request.vector_weight,
                    bm25_weight=request.bm25_weight,
                    use_rrf=request.use_rrf
                )
                retrieved_docs = search_results['results']
                search_metadata = search_results['search_metadata']
            else:
                # 기본 검색
                retrieved_docs = await self.hybrid_retriever.retrieve(
                    query=request.query,
                    limit=request.max_results
                )
                search_metadata = {}
            
            search_end = time.time()
            search_time = int((search_end - search_start) * 1000)
            
            # 2. 컨텍스트 준비
            code_contexts = self._prepare_code_contexts(retrieved_docs, request)
            
            # 3. LLM 응답 생성
            generation_start = time.time()
            
            llm_response = await self._generate_llm_response(
                request, code_contexts
            )
            
            generation_end = time.time()
            generation_time = int((generation_end - generation_start) * 1000)
            
            # 4. 응답 구성
            end_time = time.time()
            total_time = int((end_time - start_time) * 1000)
            
            response = RAGResponse(
                answer=llm_response.content,
                sources=self._format_sources(retrieved_docs),
                metadata={
                    "search_metadata": search_metadata,
                    "llm_metadata": llm_response.metadata.dict(),
                    "request_type": request.task_type.value,
                    "language": request.language,
                    "sources_count": len(retrieved_docs)
                },
                processing_time_ms=total_time,
                search_time_ms=search_time,
                generation_time_ms=generation_time
            )
            
            # 캐시 저장
            if request.use_cache:
                self._response_cache[cache_key] = response
            
            # 통계 업데이트
            self._update_stats(response, success=True)
            
            logger.info(f"RAG 쿼리 처리 완료: {total_time}ms (검색: {search_time}ms, 생성: {generation_time}ms)")
            return response
            
        except Exception as e:
            logger.error(f"RAG 쿼리 처리 실패: {e}")
            self._update_stats(None, success=False)
            raise
    
    async def process_streaming_query(
        self, 
        request: RAGRequest
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """스트리밍 쿼리 처리"""
        await self.initialize()
        
        start_time = time.time()
        
        try:
            # 1. 검색 실행
            search_start = time.time()
            retrieved_docs = await self.hybrid_retriever.retrieve(
                query=request.query,
                limit=request.max_results
            )
            search_end = time.time()
            search_time = int((search_end - search_start) * 1000)
            
            # 검색 결과 먼저 전송
            yield {
                "type": "search_results",
                "data": {
                    "sources": self._format_sources(retrieved_docs),
                    "search_time_ms": search_time
                }
            }
            
            # 2. 컨텍스트 준비
            code_contexts = self._prepare_code_contexts(retrieved_docs, request)
            
            # 3. 스트리밍 응답 생성
            generation_start = time.time()
            
            async for chunk in self.llm_service.generate_streaming_response(
                request.task_type,
                question=request.query,
                code_contexts=code_contexts,
                language=request.language,
                context_data=request.additional_context
            ):
                yield {
                    "type": "content_chunk",
                    "data": {"content": chunk}
                }
            
            generation_end = time.time()
            generation_time = int((generation_end - generation_start) * 1000)
            
            # 최종 메타데이터 전송
            end_time = time.time()
            total_time = int((end_time - start_time) * 1000)
            
            yield {
                "type": "completion",
                "data": {
                    "processing_time_ms": total_time,
                    "search_time_ms": search_time,
                    "generation_time_ms": generation_time,
                    "sources_count": len(retrieved_docs)
                }
            }
            
        except Exception as e:
            logger.error(f"스트리밍 RAG 쿼리 처리 실패: {e}")
            yield {
                "type": "error",
                "data": {"error": str(e)}
            }
    
    async def index_documents(
        self, 
        documents: List[EnhancedDocument]
    ) -> Dict[str, Any]:
        """문서 인덱싱"""
        await self.initialize()
        
        try:
            # 병렬로 Vector와 BM25 인덱스에 추가
            vector_task = self.vector_service.index_documents(documents)
            bm25_task = self.bm25_service.index_documents(documents)
            
            vector_result, bm25_result = await asyncio.gather(
                vector_task, bm25_task, return_exceptions=True
            )
            
            return {
                "success": True,
                "indexed_count": len(documents),
                "vector_result": vector_result if not isinstance(vector_result, Exception) else str(vector_result),
                "bm25_result": bm25_result if not isinstance(bm25_result, Exception) else str(bm25_result)
            }
            
        except Exception as e:
            logger.error(f"문서 인덱싱 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "indexed_count": 0
            }
    
    async def _generate_llm_response(
        self, 
        request: RAGRequest, 
        code_contexts: List[Dict[str, Any]]
    ):
        """LLM 응답 생성"""
        if request.task_type == PromptType.CODE_EXPLANATION:
            # 첫 번째 컨텍스트를 주 코드로 사용
            if code_contexts:
                main_context = code_contexts[0]
                return await self.llm_service.explain_code(
                    code_content=main_context.get('content', ''),
                    language=request.language,
                    question=request.query,
                    context_data={
                        **main_context,
                        'related_code': [ctx.get('content', '') for ctx in code_contexts[1:3]]
                    },
                    use_cache=request.use_cache
                )
        
        elif request.task_type == PromptType.CODE_GENERATION:
            return await self.llm_service.generate_code(
                requirements=request.query,
                language=request.language,
                related_code=[ctx.get('content', '') for ctx in code_contexts[:3]],
                context_data=request.additional_context,
                use_cache=request.use_cache
            )
        
        elif request.task_type == PromptType.CODE_REVIEW:
            if code_contexts:
                main_context = code_contexts[0]
                return await self.llm_service.review_code(
                    code_content=main_context.get('content', ''),
                    language=request.language,
                    context_data=main_context,
                    use_cache=request.use_cache
                )
        
        elif request.task_type == PromptType.DEBUGGING_HELP:
            if code_contexts:
                main_context = code_contexts[0]
                return await self.llm_service.help_debug(
                    code_content=main_context.get('content', ''),
                    language=request.language,
                    problem_description=request.query,
                    context_data=main_context,
                    use_cache=request.use_cache
                )
        
        # 기본적으로 일반 QA로 처리
        return await self.llm_service.answer_question(
            question=request.query,
            code_contexts=code_contexts,
            language=request.language,
            use_cache=request.use_cache
        )
    
    def _prepare_code_contexts(
        self, 
        retrieved_docs: List[Any], 
        request: RAGRequest
    ) -> List[Dict[str, Any]]:
        """코드 컨텍스트 준비"""
        code_contexts = []
        
        for doc in retrieved_docs:
            if hasattr(doc, 'content'):
                context = {
                    'content': doc.content,
                    'file_path': doc.metadata.get('file_path', ''),
                    'language': doc.metadata.get('language', request.language),
                    'function_name': doc.metadata.get('name', ''),
                    'class_name': doc.metadata.get('parent_class', ''),
                    'score': getattr(doc, 'score', 0.0)
                }
                
                if request.include_metadata:
                    context['metadata'] = doc.metadata
                
                code_contexts.append(context)
        
        return code_contexts
    
    def _format_sources(self, retrieved_docs: List[Any]) -> List[Dict[str, Any]]:
        """소스 포맷팅"""
        sources = []
        
        for i, doc in enumerate(retrieved_docs):
            source = {
                'rank': i + 1,
                'file_path': doc.metadata.get('file_path', f'문서 {i+1}'),
                'function_name': doc.metadata.get('name', ''),
                'language': doc.metadata.get('language', ''),
                'score': getattr(doc, 'score', 0.0),
                'content_preview': doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
            }
            sources.append(source)
        
        return sources
    
    def _generate_cache_key(self, request: RAGRequest) -> str:
        """캐시 키 생성"""
        import hashlib
        
        cache_data = {
            "query": request.query,
            "language": request.language,
            "task_type": request.task_type.value,
            "max_results": request.max_results,
            "vector_weight": request.vector_weight,
            "bm25_weight": request.bm25_weight,
            "use_rrf": request.use_rrf
        }
        
        cache_string = str(sorted(cache_data.items()))
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def _update_stats(self, response: Optional[RAGResponse], success: bool):
        """통계 업데이트"""
        self._request_stats["total_requests"] += 1
        
        if success:
            self._request_stats["successful_requests"] += 1
            if response:
                # 이동 평균으로 평균 처리 시간 업데이트
                current_avg = self._request_stats["average_processing_time"]
                new_time = response.processing_time_ms
                total_requests = self._request_stats["total_requests"]
                
                self._request_stats["average_processing_time"] = (
                    (current_avg * (total_requests - 1) + new_time) / total_requests
                )
        else:
            self._request_stats["failed_requests"] += 1
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """서비스 통계"""
        # 개별 서비스 통계 수집
        vector_stats = await self.vector_service.get_collection_stats()
        bm25_stats = await self.bm25_service.get_index_stats()
        llm_stats = await self.llm_service.get_service_stats()
        
        return {
            "hybrid_rag_stats": self._request_stats,
            "vector_index_stats": vector_stats,
            "bm25_index_stats": bm25_stats,
            "llm_service_stats": llm_stats,
            "cache_stats": {
                "cache_size": len(self._response_cache),
                "cache_hit_rate": (
                    self._request_stats["cache_hits"] / max(self._request_stats["total_requests"], 1)
                ) * 100
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """헬스 체크"""
        health_status = {
            "status": "healthy",
            "components": {}
        }
        
        try:
            # 개별 컴포넌트 헬스 체크
            vector_health = await self.vector_service.health_check()
            bm25_health = await self.bm25_service.health_check()
            llm_health = await self.llm_service.health_check()
            
            health_status["components"] = {
                "vector_index": vector_health,
                "bm25_index": bm25_health,
                "llm_service": llm_health,
                "hybrid_retriever": {
                    "status": "healthy" if self._initialized else "initializing"
                }
            }
            
            # 전체 상태 결정
            all_healthy = all(
                comp.get("status") == "healthy" 
                for comp in health_status["components"].values()
            )
            
            if not all_healthy:
                health_status["status"] = "degraded"
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status
    
    async def clear_cache(self):
        """캐시 클리어"""
        self._response_cache.clear()
        await self.llm_service.llm_chain.clear_cache()
        logger.info("모든 캐시가 클리어되었습니다")
```

### 2. RAG 워크플로우 최적화

```python
# app/features/hybrid_rag/optimizer.py
from typing import Dict, Any, List, Optional
import asyncio
import time
from .service import HybridRAGService, RAGRequest, PromptType

class RAGWorkflowOptimizer:
    """RAG 워크플로우 최적화"""
    
    def __init__(self, rag_service: HybridRAGService):
        self.rag_service = rag_service
        self.optimization_history = []
    
    async def optimize_for_query_type(
        self, 
        query_type: PromptType,
        sample_queries: List[str],
        optimization_rounds: int = 5
    ) -> Dict[str, Any]:
        """쿼리 타입별 최적화"""
        best_config = None
        best_avg_time = float('inf')
        
        # 테스트할 설정들
        test_configs = [
            {"vector_weight": 0.7, "bm25_weight": 0.3, "use_rrf": False},
            {"vector_weight": 0.6, "bm25_weight": 0.4, "use_rrf": False},
            {"vector_weight": 0.8, "bm25_weight": 0.2, "use_rrf": False},
            {"use_rrf": True, "rrf_k": 60},
            {"use_rrf": True, "rrf_k": 30},
            {"use_rrf": True, "rrf_k": 90},
        ]
        
        results = []
        
        for config in test_configs:
            times = []
            errors = 0
            
            for query in sample_queries[:min(len(sample_queries), 10)]:  # 최대 10개 쿼리만
                try:
                    request = RAGRequest(
                        query=query,
                        task_type=query_type,
                        use_cache=False,  # 캐시 비활성화로 정확한 측정
                        **config
                    )
                    
                    start_time = time.time()
                    response = await self.rag_service.process_query(request)
                    end_time = time.time()
                    
                    times.append((end_time - start_time) * 1000)
                    
                except Exception as e:
                    errors += 1
                    print(f"최적화 중 오류: {e}")
            
            if times:
                avg_time = sum(times) / len(times)
                config_result = {
                    "config": config,
                    "avg_time_ms": avg_time,
                    "min_time_ms": min(times),
                    "max_time_ms": max(times),
                    "error_count": errors,
                    "success_rate": (len(times) / (len(times) + errors)) * 100
                }
                results.append(config_result)
                
                if avg_time < best_avg_time and errors == 0:
                    best_avg_time = avg_time
                    best_config = config
        
        return {
            "query_type": query_type.value,
            "best_config": best_config,
            "best_avg_time_ms": best_avg_time,
            "all_results": results,
            "optimization_summary": {
                "total_configs_tested": len(test_configs),
                "successful_configs": len([r for r in results if r["error_count"] == 0]),
                "improvement_percentage": self._calculate_improvement(results)
            }
        }
    
    def _calculate_improvement(self, results: List[Dict[str, Any]]) -> float:
        """개선율 계산"""
        if len(results) < 2:
            return 0.0
        
        times = [r["avg_time_ms"] for r in results if r["error_count"] == 0]
        if len(times) < 2:
            return 0.0
        
        worst_time = max(times)
        best_time = min(times)
        
        return ((worst_time - best_time) / worst_time) * 100
```

## ✅ 완료 조건

1. **통합 서비스 구현**: 모든 RAG 구성요소가 완전히 통합됨
2. **워크플로우 최적화**: 검색-생성 파이프라인이 효율적으로 동작함
3. **스트리밍 지원**: 실시간 스트리밍 응답 제공
4. **캐싱 시스템**: 효과적인 응답 캐싱으로 성능 향상
5. **모니터링**: 상세한 성능 및 품질 모니터링
6. **헬스 체크**: 모든 구성요소의 상태 확인 가능
7. **최적화 도구**: 워크플로우 성능 최적화 지원

## 📋 다음 Task와의 연관관계

- **Task 16**: 이 통합 서비스를 위한 통합 API 엔드포인트 구현

## 🧪 테스트 계획

```python
# tests/unit/features/hybrid_rag/test_service.py
async def test_hybrid_rag_initialization():
    """HybridRAG 서비스 초기화 테스트"""
    service = HybridRAGService()
    await service.initialize()
    assert service._initialized is True

async def test_process_query():
    """쿼리 처리 테스트"""
    service = HybridRAGService()
    request = RAGRequest(
        query="JWT 인증 구현 방법",
        task_type=PromptType.GENERAL_QA
    )
    response = await service.process_query(request)
    assert response.answer != ""
    assert len(response.sources) > 0

async def test_streaming_query():
    """스트리밍 쿼리 테스트"""
    service = HybridRAGService()
    request = RAGRequest(
        query="코드 리뷰 요청",
        task_type=PromptType.CODE_REVIEW,
        streaming=True
    )
    
    chunks = []
    async for chunk in service.process_streaming_query(request):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    assert any(chunk["type"] == "search_results" for chunk in chunks)

async def test_document_indexing():
    """문서 인덱싱 테스트"""
    service = HybridRAGService()
    documents = [create_sample_enhanced_document()]
    result = await service.index_documents(documents)
    assert result["success"] is True
```

이 Task는 전체 RAG 시스템의 핵심으로, 모든 구성요소를 통합하여 완전한 코드 검색 및 생성 서비스를 제공합니다. 기존의 분산된 features 모듈들을 하나의 통합된 서비스로 대체합니다. 