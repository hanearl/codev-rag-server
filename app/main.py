from fastapi import FastAPI
from app.core.config import settings
from app.features.users.router import router as users_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="FastAPI 프로젝트",
)

# 라우터 등록
app.include_router(users_router, prefix="/api/v1/users", tags=["users"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 