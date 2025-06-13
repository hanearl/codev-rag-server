from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.features.evaluations.service import evaluation_history_service
from app.features.evaluations.schema import (
    EvaluationResultResponse,
    EvaluationHistoryResponse,
    EvaluationSummaryResponse,
    EvaluationHistoryRequest
)

router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])


@router.get("/history", response_model=EvaluationHistoryResponse)
async def get_evaluation_history(
    dataset_id: Optional[str] = Query(None, description="데이터셋 ID로 필터링"),
    system_name: Optional[str] = Query(None, description="시스템 이름으로 필터링"),
    status: Optional[str] = Query(None, description="상태로 필터링 (completed, failed, running)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db: Session = Depends(get_db)
):
    """
    평가 결과 히스토리 조회
    
    - **dataset_id**: 특정 데이터셋의 평가 결과만 조회
    - **system_name**: 특정 시스템의 평가 결과만 조회  
    - **status**: 특정 상태의 평가 결과만 조회
    - **page**: 페이지 번호 (1부터 시작)
    - **page_size**: 페이지당 결과 수 (최대 100)
    
    Returns:
        평가 결과 목록과 페이지네이션 정보
    """
    try:
        # 오프셋 계산
        offset = (page - 1) * page_size
        
        # 평가 결과 조회
        results = evaluation_history_service.get_evaluation_history(
            db=db,
            dataset_id=dataset_id,
            system_name=system_name,
            status=status,
            limit=page_size,
            offset=offset
        )
        
        # 전체 개수 조회
        total_count = evaluation_history_service.get_evaluation_count(
            db=db,
            dataset_id=dataset_id,
            system_name=system_name,
            status=status
        )
        
        # 응답 데이터 변환
        result_responses = []
        for result in results:
            result_responses.append(EvaluationResultResponse(
                id=result.id,
                system_id=result.system_id,
                system_name=result.system.name if result.system else None,
                dataset_id=result.dataset_id,
                metrics=result.metrics,
                execution_time=result.execution_time,
                config=result.config,
                status=result.status,
                error_message=result.error_message,
                created_at=result.created_at,
                updated_at=result.updated_at
            ))
        
        # 다음 페이지 존재 여부
        has_next = offset + page_size < total_count
        
        return EvaluationHistoryResponse(
            results=result_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=has_next
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"평가 히스토리 조회 실패: {str(e)}")


@router.get("/{evaluation_id}", response_model=EvaluationResultResponse)
async def get_evaluation_by_id(
    evaluation_id: int,
    db: Session = Depends(get_db)
):
    """
    ID로 특정 평가 결과 조회
    
    - **evaluation_id**: 조회할 평가 결과 ID
    
    Returns:
        평가 결과 상세 정보
    """
    try:
        result = evaluation_history_service.get_evaluation_by_id(db, evaluation_id)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"평가 결과를 찾을 수 없습니다: {evaluation_id}")
        
        return EvaluationResultResponse(
            id=result.id,
            system_id=result.system_id,
            system_name=result.system.name if result.system else None,
            dataset_id=result.dataset_id,
            metrics=result.metrics,
            execution_time=result.execution_time,
            config=result.config,
            status=result.status,
            error_message=result.error_message,
            created_at=result.created_at,
            updated_at=result.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"평가 결과 조회 실패: {str(e)}")


@router.get("/latest/{dataset_id}", response_model=EvaluationResultResponse)
async def get_latest_evaluation(
    dataset_id: str,
    system_name: Optional[str] = Query(None, description="시스템 이름으로 필터링"),
    db: Session = Depends(get_db)
):
    """
    특정 데이터셋의 최신 평가 결과 조회
    
    - **dataset_id**: 데이터셋 ID
    - **system_name**: 특정 시스템의 최신 결과만 조회 (선택사항)
    
    Returns:
        최신 평가 결과
    """
    try:
        result = evaluation_history_service.get_latest_evaluation(
            db=db,
            dataset_id=dataset_id,
            system_name=system_name
        )
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"평가 결과를 찾을 수 없습니다 (데이터셋: {dataset_id}, 시스템: {system_name})"
            )
        
        return EvaluationResultResponse(
            id=result.id,
            system_id=result.system_id,
            system_name=result.system.name if result.system else None,
            dataset_id=result.dataset_id,
            metrics=result.metrics,
            execution_time=result.execution_time,
            config=result.config,
            status=result.status,
            error_message=result.error_message,
            created_at=result.created_at,
            updated_at=result.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"최신 평가 결과 조회 실패: {str(e)}")


@router.delete("/{evaluation_id}")
async def delete_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db)
):
    """
    평가 결과 삭제
    
    - **evaluation_id**: 삭제할 평가 결과 ID
    
    Returns:
        삭제 성공 메시지
    """
    try:
        result = evaluation_history_service.delete_evaluation(db, evaluation_id)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"평가 결과를 찾을 수 없습니다: {evaluation_id}")
        
        return {"message": f"평가 결과가 삭제되었습니다 (ID: {evaluation_id})"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"평가 결과 삭제 실패: {str(e)}")


@router.get("/summary/system/{system_name}", response_model=EvaluationSummaryResponse)
async def get_system_performance_summary(
    system_name: str,
    db: Session = Depends(get_db)
):
    """
    시스템 성능 요약 조회
    
    - **system_name**: 시스템 이름
    
    Returns:
        시스템의 전체 평가 성능 요약
    """
    try:
        summary = evaluation_history_service.get_system_performance_summary(db, system_name)
        
        return EvaluationSummaryResponse(
            total_evaluations=summary["total_evaluations"],
            datasets=summary["datasets"],
            average_execution_time=summary["average_execution_time"],
            latest_evaluation=summary["latest_evaluation"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시스템 성능 요약 조회 실패: {str(e)}")


@router.get("/summary/dataset/{dataset_id}", response_model=EvaluationSummaryResponse)
async def get_dataset_evaluation_summary(
    dataset_id: str,
    db: Session = Depends(get_db)
):
    """
    데이터셋 평가 요약 조회
    
    - **dataset_id**: 데이터셋 ID
    
    Returns:
        데이터셋의 전체 평가 요약
    """
    try:
        summary = evaluation_history_service.get_dataset_evaluation_summary(db, dataset_id)
        
        return EvaluationSummaryResponse(
            total_evaluations=summary["total_evaluations"],
            datasets=[dataset_id],  # 단일 데이터셋
            systems=summary["systems"],
            average_execution_time=0.0,  # 데이터셋 요약에서는 평균 실행시간 제외
            latest_evaluation=summary["latest_evaluation"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터셋 평가 요약 조회 실패: {str(e)}") 