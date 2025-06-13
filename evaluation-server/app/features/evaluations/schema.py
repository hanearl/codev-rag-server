from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class EvaluationResultResponse(BaseModel):
    """평가 결과 응답 스키마"""
    id: int
    system_id: int
    system_name: Optional[str] = None
    dataset_id: str
    metrics: Dict[str, Dict[str, float]]
    execution_time: float
    config: Dict[str, Any]
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EvaluationHistoryResponse(BaseModel):
    """평가 히스토리 응답 스키마"""
    results: List[EvaluationResultResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool


class EvaluationSummaryResponse(BaseModel):
    """평가 요약 응답 스키마"""
    total_evaluations: int
    datasets: List[str]
    systems: Optional[List[str]] = None
    average_execution_time: float
    latest_evaluation: Optional[Dict[str, Any]] = None


class EvaluationHistoryRequest(BaseModel):
    """평가 히스토리 조회 요청 스키마"""
    dataset_id: Optional[str] = None
    system_name: Optional[str] = None
    status: Optional[str] = None
    page: int = 1
    page_size: int = 20
    
    class Config:
        json_schema_extra = {
            "example": {
                "dataset_id": "test-dataset",
                "system_name": "my-rag-system",
                "status": "completed",
                "page": 1,
                "page_size": 20
            }
        } 