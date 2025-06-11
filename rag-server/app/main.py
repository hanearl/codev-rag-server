from fastapi import FastAPI
from datetime import datetime
from app.core.config import settings
from app.features.users.router import router as users_router

app = FastAPI(
    title="RAG Server API",
    description="RAG 오케스트레이션 서비스",
    version="1.0.0"
)

# 라우터 등록
app.include_router(users_router, prefix="/api/v1", tags=["users"])

@app.get("/")
async def root():
    return {"service": "rag-server", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "rag-server",
        "timestamp": datetime.utcnow()
    } 