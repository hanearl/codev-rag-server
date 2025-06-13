# Task 16: 통합 API 엔드포인트 구현

## 📋 작업 개요
HybridRAG 서비스를 위한 통합 API 엔드포인트를 구현합니다. 기존 개별 features의 라우터들을 하나의 통합된 API로 대체하여 일관성 있는 인터페이스를 제공합니다.

## 🎯 작업 목표
- 통합된 RAG API 엔드포인트 구현
- RESTful API 설계 원칙 준수
- WebSocket을 통한 실시간 스트리밍 지원
- API 문서 자동 생성 및 유지보수성 향상

## 🔗 의존성
- **선행 Task**: Task 15 (HybridRAG 서비스 구현)
- **대체할 기존 코드**: `app/features/*/router.py` 파일들

## 🔧 구현 사항

### 1. 통합 API 라우터

```python
# app/features/hybrid_rag/router.py
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json
import asyncio
import logging

from .service import HybridRAGService, RAGRequest, RAGResponse
from .schema import (
    QueryRequest, QueryResponse, StreamingQueryRequest,
    IndexingRequest, IndexingResponse, HealthResponse,
    StatsResponse, OptimizationRequest, OptimizationResponse
)
from app.llm.prompt_service import PromptType
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["Hybrid RAG"])

# 서비스 인스턴스 (의존성 주입으로 개선 가능)
rag_service = HybridRAGService()

@router.post("/query", response_model=QueryResponse, status_code=200)
async def process_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    # current_user = Depends(get_current_user)  # 인증이 필요한 경우
) -> QueryResponse:
    """
    코드 관련 질의응답 처리
    
    - **query**: 질문 또는 요청사항
    - **language**: 프로그래밍 언어 (java, python, javascript 등)
    - **task_type**: 작업 유형 (code_explanation, code_generation, code_review 등)
    - **max_results**: 검색할 최대 결과 수
    
    Returns:
        생성된 답변과 참조된 코드 소스들
    """
    try:
        # RAGRequest로 변환
        rag_request = RAGRequest(
            query=request.query,
            language=request.language,
            task_type=PromptType(request.task_type),
            max_results=request.max_results,
            use_cache=request.use_cache,
            include_metadata=request.include_metadata,
            vector_weight=request.vector_weight,
            bm25_weight=request.bm25_weight,
            use_rrf=request.use_rrf,
            additional_context=request.additional_context
        )
        
        # 쿼리 처리
        rag_response = await rag_service.process_query(rag_request)
        
        # 응답 변환
        response = QueryResponse(
            answer=rag_response.answer,
            sources=rag_response.sources,
            metadata=rag_response.metadata,
            processing_time_ms=rag_response.processing_time_ms,
            search_time_ms=rag_response.search_time_ms,
            generation_time_ms=rag_response.generation_time_ms,
            cached=rag_response.cached
        )
        
        # 백그라운드에서 통계 로깅
        background_tasks.add_task(
            log_query_stats, 
            request.query, 
            request.task_type, 
            rag_response.processing_time_ms
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"잘못된 요청 파라미터: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"잘못된 요청: {str(e)}"
        )
    except Exception as e:
        logger.error(f"쿼리 처리 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="내부 서버 오류가 발생했습니다"
        )

@router.post("/query/stream")
async def stream_query(
    request: StreamingQueryRequest,
    # current_user = Depends(get_current_user)
):
    """
    스트리밍 방식의 질의응답 처리
    
    실시간으로 검색 결과와 생성되는 답변을 스트리밍합니다.
    """
    try:
        # RAGRequest로 변환
        rag_request = RAGRequest(
            query=request.query,
            language=request.language,
            task_type=PromptType(request.task_type),
            max_results=request.max_results,
            use_cache=request.use_cache,
            streaming=True
        )
        
        async def generate_stream():
            try:
                async for chunk in rag_service.process_streaming_query(rag_request):
                    # Server-Sent Events 형식으로 전송
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                
                # 스트림 종료 신호
                yield f"data: {json.dumps({'type': 'end'})}\n\n"
                
            except Exception as e:
                logger.error(f"스트리밍 처리 실패: {e}")
                error_chunk = {
                    "type": "error",
                    "data": {"error": str(e)}
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"스트리밍 쿼리 설정 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="스트리밍 설정 오류"
        )

@router.post("/index", response_model=IndexingResponse, status_code=201)
async def index_documents(
    request: IndexingRequest,
    background_tasks: BackgroundTasks,
    # current_user = Depends(get_current_user)
) -> IndexingResponse:
    """
    문서 인덱싱
    
    코드 문서들을 벡터 및 BM25 인덱스에 추가합니다.
    """
    try:
        # 문서 처리 (실제로는 document_service를 통해 처리)
        enhanced_documents = await process_documents_for_indexing(request.documents)
        
        # 인덱싱 실행
        result = await rag_service.index_documents(enhanced_documents)
        
        response = IndexingResponse(
            success=result["success"],
            indexed_count=result["indexed_count"],
            vector_result=result.get("vector_result", {}),
            bm25_result=result.get("bm25_result", {}),
            error=result.get("error")
        )
        
        # 백그라운드에서 인덱스 통계 업데이트
        background_tasks.add_task(update_index_stats)
        
        return response
        
    except Exception as e:
        logger.error(f"문서 인덱싱 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인덱싱 실패: {str(e)}"
        )

@router.post("/index/files", response_model=IndexingResponse)
async def index_files(
    files: List[UploadFile] = File(...),
    language: str = "java",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    # current_user = Depends(get_current_user)
) -> IndexingResponse:
    """
    파일 업로드를 통한 인덱싱
    
    업로드된 코드 파일들을 파싱하고 인덱싱합니다.
    """
    try:
        indexed_count = 0
        errors = []
        
        for file in files:
            try:
                # 파일 내용 읽기
                content = await file.read()
                file_content = content.decode('utf-8')
                
                # 문서 생성 및 인덱싱
                documents = await process_file_content(
                    file_content, 
                    file.filename, 
                    language
                )
                
                result = await rag_service.index_documents(documents)
                if result["success"]:
                    indexed_count += result["indexed_count"]
                else:
                    errors.append(f"{file.filename}: {result.get('error', '알 수 없는 오류')}")
                    
            except Exception as e:
                errors.append(f"{file.filename}: {str(e)}")
                logger.error(f"파일 {file.filename} 처리 실패: {e}")
        
        success = len(errors) == 0
        
        response = IndexingResponse(
            success=success,
            indexed_count=indexed_count,
            error="; ".join(errors) if errors else None
        )
        
        if success:
            background_tasks.add_task(update_index_stats)
        
        return response
        
    except Exception as e:
        logger.error(f"파일 인덱싱 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 인덱싱 실패: {str(e)}"
        )

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    # current_user = Depends(get_current_user)
) -> StatsResponse:
    """
    서비스 통계 조회
    
    RAG 시스템의 전반적인 통계 정보를 반환합니다.
    """
    try:
        stats = await rag_service.get_service_stats()
        
        return StatsResponse(
            hybrid_rag_stats=stats["hybrid_rag_stats"],
            vector_index_stats=stats["vector_index_stats"],
            bm25_index_stats=stats["bm25_index_stats"],
            llm_service_stats=stats["llm_service_stats"],
            cache_stats=stats["cache_stats"]
        )
        
    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="통계 조회 실패"
        )

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    헬스 체크
    
    모든 구성요소의 상태를 확인합니다.
    """
    try:
        health_status = await rag_service.health_check()
        
        return HealthResponse(
            status=health_status["status"],
            components=health_status["components"],
            timestamp=health_status.get("timestamp"),
            error=health_status.get("error")
        )
        
    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        return HealthResponse(
            status="unhealthy",
            components={},
            error=str(e)
        )

@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_workflow(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    # current_user = Depends(get_current_user)
) -> OptimizationResponse:
    """
    워크플로우 최적화
    
    주어진 쿼리 타입에 대해 최적의 설정을 찾습니다.
    """
    try:
        from .optimizer import RAGWorkflowOptimizer
        
        optimizer = RAGWorkflowOptimizer(rag_service)
        
        # 백그라운드에서 최적화 실행
        optimization_task = asyncio.create_task(
            optimizer.optimize_for_query_type(
                PromptType(request.query_type),
                request.sample_queries,
                request.optimization_rounds
            )
        )
        
        # 즉시 응답 반환 (백그라운드에서 계속 실행)
        response = OptimizationResponse(
            status="started",
            message="최적화가 백그라운드에서 시작되었습니다",
            optimization_id=f"opt_{int(asyncio.get_event_loop().time())}"
        )
        
        # 완료 시 로깅하는 백그라운드 작업
        background_tasks.add_task(
            handle_optimization_completion, 
            optimization_task,
            response.optimization_id
        )
        
        return response
        
    except Exception as e:
        logger.error(f"최적화 시작 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="최적화 시작 실패"
        )

@router.delete("/cache")
async def clear_cache(
    # current_user = Depends(get_current_user)
) -> Dict[str, str]:
    """
    캐시 클리어
    
    모든 캐시를 삭제합니다.
    """
    try:
        await rag_service.clear_cache()
        return {"message": "모든 캐시가 클리어되었습니다"}
        
    except Exception as e:
        logger.error(f"캐시 클리어 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="캐시 클리어 실패"
        )

# 헬퍼 함수들
async def process_documents_for_indexing(documents: List[Dict[str, Any]]):
    """문서를 인덱싱용으로 처리"""
    # 실제 구현에서는 document_service를 사용
    enhanced_documents = []
    for doc in documents:
        # EnhancedDocument 생성 로직
        pass
    return enhanced_documents

async def process_file_content(content: str, filename: str, language: str):
    """파일 내용을 문서로 처리"""
    # 실제 구현에서는 AST 파서를 사용
    documents = []
    # 파싱 및 문서 생성 로직
    return documents

async def log_query_stats(query: str, task_type: str, processing_time: int):
    """쿼리 통계 로깅"""
    logger.info(f"Query processed: type={task_type}, time={processing_time}ms")

async def update_index_stats():
    """인덱스 통계 업데이트"""
    logger.info("Index statistics updated")

async def handle_optimization_completion(task: asyncio.Task, optimization_id: str):
    """최적화 완료 처리"""
    try:
        result = await task
        logger.info(f"Optimization {optimization_id} completed: {result}")
    except Exception as e:
        logger.error(f"Optimization {optimization_id} failed: {e}")

# 서비스 시작 시 초기화
@router.on_event("startup")
async def startup_event():
    """라우터 시작 시 초기화"""
    await rag_service.initialize()
    logger.info("HybridRAG 서비스 초기화 완료")
```

### 2. WebSocket 스트리밍 엔드포인트

```python
# app/features/hybrid_rag/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging
from typing import Dict, Any

from .service import HybridRAGService, RAGRequest
from app.llm.prompt_service import PromptType

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket 연결됨: {client_id}")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket 연결 해제됨: {client_id}")
    
    async def send_message(self, client_id: str, message: Dict[str, Any]):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(json.dumps(message, ensure_ascii=False))

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket 엔드포인트"""
    rag_service = HybridRAGService()
    await rag_service.initialize()
    
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "query":
                await handle_query_message(message, client_id, rag_service)
            elif message.get("type") == "ping":
                await manager.send_message(client_id, {"type": "pong"})
            else:
                await manager.send_message(client_id, {
                    "type": "error",
                    "message": "지원하지 않는 메시지 타입입니다"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket 처리 오류 ({client_id}): {e}")
        await manager.send_message(client_id, {
            "type": "error",
            "message": str(e)
        })
        manager.disconnect(client_id)

async def handle_query_message(
    message: Dict[str, Any], 
    client_id: str, 
    rag_service: HybridRAGService
):
    """쿼리 메시지 처리"""
    try:
        query_data = message.get("data", {})
        
        # RAGRequest 생성
        rag_request = RAGRequest(
            query=query_data.get("query", ""),
            language=query_data.get("language", "java"),
            task_type=PromptType(query_data.get("task_type", "general_qa")),
            max_results=query_data.get("max_results", 5),
            streaming=True
        )
        
        # 처리 시작 알림
        await manager.send_message(client_id, {
            "type": "processing_started",
            "query": rag_request.query
        })
        
        # 스트리밍 응답 처리
        async for chunk in rag_service.process_streaming_query(rag_request):
            await manager.send_message(client_id, chunk)
        
        # 완료 알림
        await manager.send_message(client_id, {
            "type": "processing_completed"
        })
        
    except Exception as e:
        logger.error(f"쿼리 처리 실패 ({client_id}): {e}")
        await manager.send_message(client_id, {
            "type": "error",
            "message": f"쿼리 처리 실패: {str(e)}"
        })
```

## ✅ 완료 조건

1. **통합 API 구현**: 모든 RAG 기능을 위한 통합 API 완전 구현
2. **스트리밍 지원**: HTTP SSE 및 WebSocket 스트리밍 지원
3. **파일 업로드**: 코드 파일 업로드 및 인덱싱 지원
4. **에러 처리**: 모든 예외 상황 적절히 처리
5. **API 문서**: FastAPI 자동 문서 생성
6. **성능 최적화**: 백그라운드 작업 및 비동기 처리
7. **보안**: 인증/인가 준비 (주석 처리된 상태)

## 📋 다음 Task와의 연관관계

- **Task 17**: 기존 개별 features 모듈들을 이 통합 API로 대체

## 🧪 테스트 계획

```python
# tests/unit/features/hybrid_rag/test_router.py
from fastapi.testclient import TestClient

def test_process_query(client: TestClient):
    """쿼리 처리 API 테스트"""
    response = client.post("/api/v1/rag/query", json={
        "query": "JWT 인증 구현 방법",
        "language": "java",
        "task_type": "general_qa"
    })
    assert response.status_code == 200
    assert "answer" in response.json()

def test_health_check(client: TestClient):
    """헬스 체크 API 테스트"""
    response = client.get("/api/v1/rag/health")
    assert response.status_code == 200
    assert response.json()["status"] in ["healthy", "degraded", "unhealthy"]

async def test_websocket_connection():
    """WebSocket 연결 테스트"""
    with client.websocket_connect("/ws/rag/test-client") as websocket:
        # Ping 테스트
        websocket.send_json({"type": "ping"})
        data = websocket.receive_json()
        assert data["type"] == "pong"
```

이 Task는 모든 RAG 기능을 하나의 일관성 있는 API로 통합하여 클라이언트가 쉽게 사용할 수 있도록 합니다. RESTful API와 WebSocket을 통한 실시간 스트리밍을 모두 지원합니다. 