from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.features.embedding.router import router as embedding_router
from app.core.config import settings

app = FastAPI(
    title="Embedding Server",
    description="HuggingFace 임베딩 모델을 사용한 텍스트 임베딩 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(embedding_router)


@app.get("/health")
async def root_health_check():
    """루트 헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "embedding-server",
        "model": settings.model_name
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port) 