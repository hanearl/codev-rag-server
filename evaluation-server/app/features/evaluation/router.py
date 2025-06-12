from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.features.evaluation.schema import (
    EvaluationRequest, EvaluationResponse, DatasetListResponse, 
    DatasetInfoResponse, MetricsInfoResponse, ClasspathTestRequest, ClasspathTestResponse
)
from app.features.evaluation.service import evaluation_service
from app.db.database import get_db

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])


@router.get("/health")
async def health_check():
    """평가 서비스 헬스체크"""
    return {
        "status": "healthy",
        "service": "evaluation-server",
        "features": {
            "metrics": list(evaluation_service.get_available_metrics().keys()),
            "datasets": await evaluation_service.get_available_datasets()
        }
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """상세 헬스체크"""
    try:
        # 데이터셋 로드 테스트
        datasets = await evaluation_service.get_available_datasets()
        
        # 메트릭 정보 조회 테스트
        metrics_info = evaluation_service.get_available_metrics()
        
        return {
            "status": "healthy",
            "service": "evaluation-server",
            "version": "1.0.0",
            "components": {
                "dataset_loader": {
                    "status": "healthy",
                    "available_datasets": len(datasets)
                },
                "metrics_manager": {
                    "status": "healthy",
                    "available_metrics": len(metrics_info)
                }
            },
            "features": {
                "datasets": datasets,
                "metrics": list(metrics_info.keys())
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


@router.get("/datasets", response_model=DatasetListResponse)
async def list_datasets():
    """사용 가능한 데이터셋 목록 조회"""
    try:
        datasets = await evaluation_service.get_available_datasets()
        return DatasetListResponse(datasets=datasets)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터셋 목록 조회 실패: {str(e)}"
        )


@router.get("/datasets/{dataset_name}", response_model=DatasetInfoResponse)
async def get_dataset_info(dataset_name: str):
    """특정 데이터셋 정보 조회"""
    try:
        dataset_info = await evaluation_service.get_dataset_info(dataset_name)
        return DatasetInfoResponse(**dataset_info)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"데이터셋 '{dataset_name}'을 찾을 수 없습니다"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"데이터셋 정보 조회 실패: {str(e)}"
        )


@router.get("/metrics", response_model=MetricsInfoResponse)
async def get_metrics_info():
    """사용 가능한 메트릭 정보 조회"""
    try:
        metrics_info = evaluation_service.get_available_metrics()
        return MetricsInfoResponse(metrics=metrics_info)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메트릭 정보 조회 실패: {str(e)}"
        )


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_rag_system(
    request: EvaluationRequest,
    db: Session = Depends(get_db)
):
    """RAG 시스템 평가 실행"""
    try:
        # 입력 검증
        if not request.k_values:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="k_values는 비어있을 수 없습니다"
            )
        
        if any(k <= 0 for k in request.k_values):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="k_values는 모두 양수여야 합니다"
            )
        
        if not request.metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="최소 하나의 메트릭을 선택해야 합니다"
            )
        
        # 메트릭 유효성 검증
        available_metrics = evaluation_service.get_available_metrics()
        invalid_metrics = [m for m in request.metrics if m not in available_metrics]
        if invalid_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"유효하지 않은 메트릭: {invalid_metrics}"
            )
        
        # 평가 실행
        result = await evaluation_service.evaluate_rag_system(request, db)
        return result
        
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"데이터셋을 찾을 수 없습니다: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"평가 실행 중 오류 발생: {str(e)}"
        )


@router.post("/test-classpath-conversion", response_model=ClasspathTestResponse)
async def test_classpath_conversion(request: ClasspathTestRequest):
    """클래스패스 변환 테스트 (디버깅용)"""
    try:
        results = await evaluation_service.test_classpath_conversion(
            request.filepaths, 
            request.options
        )
        return ClasspathTestResponse(results=results)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"클래스패스 변환 테스트 실패: {str(e)}"
        )


 