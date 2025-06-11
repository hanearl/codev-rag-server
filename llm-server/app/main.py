from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.features.llm.router import router as llm_router
from app.core.config import settings

app = FastAPI(
    title="LLM Server",
    description="vLLM 호환 API를 제공하는 OpenAI 프록시 서비스",
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
app.include_router(llm_router)


@app.get("/health")
async def root_health_check():
    """루트 헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "llm-server",
        "model": settings.model_name
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port) 