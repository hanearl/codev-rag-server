from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.features.evaluation.router import router as evaluation_router

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="RAG Evaluation Server API",
    description="RAG 시스템 성능 평가를 위한 마이크로서비스. Java 클래스패스 변환과 함수명 제외 옵션을 지원합니다.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 환경에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(evaluation_router)

@app.get("/")
async def root():
    """서비스 상태 확인"""
    return {
        "service": "evaluation-server", 
        "status": "running",
        "version": "1.0.0",
        "description": "RAG 시스템 성능 평가 서비스",
        "features": {
            "java_classpath_conversion": True,
            "method_name_filtering": True,
            "inline_dataset_format": True,
            "multiple_answer_support": True,
            "difficulty_levels": ["하", "중", "상"]
        },
        "endpoints": {
            "evaluation": "/api/v1/evaluation/evaluate",
            "datasets": "/api/v1/evaluation/datasets",
            "test_conversion": "/api/v1/evaluation/test-classpath-conversion"
        }
    }

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "evaluation-server"
    }

# TODO: Phase 1에서 라우터들을 추가할 예정
# app.include_router(evaluation_router)
# app.include_router(system_router)
# app.include_router(dataset_router) 