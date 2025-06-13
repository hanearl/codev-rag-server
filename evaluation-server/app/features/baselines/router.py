from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.features.baselines.service import BaselineService
from app.features.baselines.repository import BaselineRepository
from app.features.baselines.schema import (
    BaselineCreateRequest, BaselineResponse, BaselineListResponse,
    BaselineComparisonRequest, BaselineComparisonResponse,
    BaselineDeactivateRequest, BaselineDetailResponse
)
from app.features.evaluations.model import EvaluationResult
from app.features.evaluation.schema import BaselineComparison
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/baselines", tags=["baselines"])


def get_baseline_service() -> BaselineService:
    """베이스라인 서비스 의존성"""
    return BaselineService(BaselineRepository())


@router.post("/", response_model=BaselineResponse, status_code=status.HTTP_201_CREATED)
async def create_baseline(
    request: BaselineCreateRequest,
    db: Session = Depends(get_db),
    service: BaselineService = Depends(get_baseline_service)
):
    """
    베이스라인 등록
    
    평가 결과를 베이스라인으로 등록합니다.
    동일한 데이터셋에서 같은 이름의 베이스라인은 생성할 수 없습니다.
    """
    try:
        baseline = await service.register_baseline(
            db, request.name, request.description, request.evaluation_result_id
        )
        logger.info(f"베이스라인 생성 완료: {baseline.name} (ID: {baseline.id})")
        return BaselineResponse.from_orm(baseline)
    except ValueError as e:
        logger.warning(f"베이스라인 생성 실패: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"베이스라인 생성 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                           detail="베이스라인 생성 중 오류가 발생했습니다")


@router.get("/", response_model=BaselineListResponse)
async def list_baselines(
    dataset_id: Optional[str] = Query(None, description="데이터셋 ID로 필터링"),
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(100, ge=1, le=1000, description="조회할 항목 수"),
    db: Session = Depends(get_db),
    service: BaselineService = Depends(get_baseline_service)
):
    """
    베이스라인 목록 조회
    
    전체 베이스라인 목록을 조회하거나 데이터셋별로 필터링하여 조회합니다.
    """
    try:
        baselines = await service.list_baselines(db, dataset_id, skip, limit)
        baseline_responses = [BaselineResponse.from_orm(b) for b in baselines]
        
        return BaselineListResponse(
            baselines=baseline_responses,
            total=len(baseline_responses),
            dataset_id=dataset_id
        )
    except Exception as e:
        logger.error(f"베이스라인 목록 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                           detail="베이스라인 목록 조회 중 오류가 발생했습니다")


@router.get("/{baseline_id}", response_model=BaselineDetailResponse)
async def get_baseline(
    baseline_id: int,
    db: Session = Depends(get_db),
    service: BaselineService = Depends(get_baseline_service)
):
    """
    베이스라인 상세 조회
    
    특정 베이스라인의 상세 정보를 조회합니다.
    """
    baseline = await service.get_baseline_by_id(db, baseline_id)
    if not baseline:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                           detail=f"베이스라인을 찾을 수 없습니다: {baseline_id}")
    
    # 평가 결과 정보 포함
    evaluation_result_info = None
    if baseline.evaluation_result:
        evaluation_result_info = {
            "id": baseline.evaluation_result.id,
            "metrics": baseline.evaluation_result.metrics,
            "execution_time": baseline.evaluation_result.execution_time,
            "created_at": baseline.evaluation_result.created_at.isoformat()
        }
    
    response_data = BaselineResponse.from_orm(baseline).dict()
    response_data["evaluation_result"] = evaluation_result_info
    
    return BaselineDetailResponse(**response_data)


@router.post("/compare", response_model=BaselineComparison)
async def compare_baseline(
    request: BaselineComparisonRequest,
    db: Session = Depends(get_db),
    service: BaselineService = Depends(get_baseline_service)
):
    """
    베이스라인 비교
    
    현재 평가 결과를 베이스라인과 비교하여 성능 개선도를 확인합니다.
    """
    try:
        # 현재 평가 결과 조회
        current_result = db.query(EvaluationResult).filter(
            EvaluationResult.id == request.evaluation_result_id
        ).first()
        
        if not current_result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                               detail=f"평가 결과를 찾을 수 없습니다: {request.evaluation_result_id}")
        
        # 베이스라인과 비교
        comparison = await service.compare_with_baseline(
            db, request.baseline_id, current_result
        )
        
        logger.info(f"베이스라인 비교 완료: baseline_id={request.baseline_id}, "
                   f"result_id={request.evaluation_result_id}, better={comparison.is_better}")
        
        return comparison
        
    except ValueError as e:
        logger.warning(f"베이스라인 비교 실패: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"베이스라인 비교 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                           detail="베이스라인 비교 중 오류가 발생했습니다")


@router.patch("/{baseline_id}/deactivate", response_model=BaselineResponse)
async def deactivate_baseline(
    baseline_id: int,
    request: BaselineDeactivateRequest,
    db: Session = Depends(get_db),
    service: BaselineService = Depends(get_baseline_service)
):
    """
    베이스라인 비활성화
    
    베이스라인을 비활성화합니다. 비활성화된 베이스라인은 목록에서 제외됩니다.
    """
    try:
        baseline = await service.deactivate_baseline(db, baseline_id)
        if not baseline:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                               detail=f"베이스라인을 찾을 수 없습니다: {baseline_id}")
        
        logger.info(f"베이스라인 비활성화 완료: {baseline.name} (ID: {baseline_id})")
        return BaselineResponse.from_orm(baseline)
        
    except ValueError as e:
        logger.warning(f"베이스라인 비활성화 실패: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"베이스라인 비활성화 중 오류: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                           detail="베이스라인 비활성화 중 오류가 발생했습니다")


@router.get("/{baseline_id}/compare/{evaluation_result_id}", response_model=BaselineComparison)
async def compare_baseline_direct(
    baseline_id: int,
    evaluation_result_id: int,
    db: Session = Depends(get_db),
    service: BaselineService = Depends(get_baseline_service)
):
    """
    베이스라인 직접 비교 (GET 방식)
    
    URL 파라미터로 베이스라인과 평가 결과를 직접 비교합니다.
    """
    request = BaselineComparisonRequest(
        baseline_id=baseline_id,
        evaluation_result_id=evaluation_result_id
    )
    return await compare_baseline(request, db, service) 