from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class BaselineCreateRequest(BaseModel):
    """베이스라인 생성 요청"""
    name: str = Field(..., description="베이스라인 이름", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="베이스라인 설명")
    evaluation_result_id: int = Field(..., description="평가 결과 ID", gt=0)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "baseline-v1.0",
                "description": "첫 번째 베이스라인 - GPT-4 기반",
                "evaluation_result_id": 1
            }
        }


class BaselineResponse(BaseModel):
    """베이스라인 응답"""
    id: int
    name: str
    description: Optional[str]
    dataset_id: str
    evaluation_result_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "id": 1,
                "name": "baseline-v1.0",
                "description": "첫 번째 베이스라인 - GPT-4 기반",
                "dataset_id": "java-coding-dataset",
                "evaluation_result_id": 1,
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": None
            }
        }


class BaselineDetailResponse(BaselineResponse):
    """베이스라인 상세 응답 (평가 결과 포함)"""
    evaluation_result: Optional[Dict[str, Any]] = Field(None, description="평가 결과 정보")
    
    class Config:
        from_attributes = True


class BaselineListResponse(BaseModel):
    """베이스라인 목록 응답"""
    baselines: List[BaselineResponse]
    total: int
    dataset_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "baselines": [
                    {
                        "id": 1,
                        "name": "baseline-v1.0",
                        "description": "첫 번째 베이스라인",
                        "dataset_id": "java-coding-dataset",
                        "evaluation_result_id": 1,
                        "is_active": True,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": None
                    }
                ],
                "total": 1,
                "dataset_id": "java-coding-dataset"
            }
        }


class BaselineComparisonRequest(BaseModel):
    """베이스라인 비교 요청"""
    baseline_id: int = Field(..., description="비교할 베이스라인 ID", gt=0)
    evaluation_result_id: int = Field(..., description="현재 평가 결과 ID", gt=0)
    
    class Config:
        schema_extra = {
            "example": {
                "baseline_id": 1,
                "evaluation_result_id": 5
            }
        }


class BaselineComparisonResponse(BaseModel):
    """베이스라인 비교 응답 (확장)"""
    baseline_id: str
    current_result_id: str
    baseline_name: str
    baseline_dataset: str
    metric_improvements: Dict[str, Dict[str, float]]
    is_better: bool
    summary: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "baseline_id": "1",
                "current_result_id": "5",
                "baseline_name": "baseline-v1.0",
                "baseline_dataset": "java-coding-dataset",
                "metric_improvements": {
                    "recall": {"1": 16.67, "3": 14.29, "5": 12.5},
                    "precision": {"1": -20.0, "3": -16.67, "5": -14.29},
                    "ndcg": {"1": 9.09, "3": 7.69, "5": 6.67}
                },
                "is_better": True,
                "summary": {
                    "total_improvements": 6,
                    "total_degradations": 3,
                    "avg_improvement": 5.24,
                    "best_metric": "recall",
                    "worst_metric": "precision"
                }
            }
        }


class BaselineDeactivateRequest(BaseModel):
    """베이스라인 비활성화 요청"""
    reason: Optional[str] = Field(None, description="비활성화 사유")
    
    class Config:
        schema_extra = {
            "example": {
                "reason": "새로운 베이스라인으로 교체"
            }
        } 