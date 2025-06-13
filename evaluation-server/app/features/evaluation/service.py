import uuid
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import httpx
from sqlalchemy.orm import Session

from app.features.evaluation.schema import (
    EvaluationRequest,
    EvaluationResult,
    EvaluationMetrics,
    EvaluationOptions,
    EvaluationQuestion,
    RetrievalResult,
    QuestionEvaluationResult,
    DatasetMetadata,
    EvaluationResponse,
    SystemConfig
)
from app.features.evaluation.dataset_loader import DatasetLoader, create_default_dataset_loader
from app.core.classpath_utils import ClasspathMatcher, create_default_classpath_matcher, ClasspathConverter
from app.features.systems.interface import RAGSystemInterface, RAGSystemConfig
from app.features.systems.factory import create_rag_system, RAGSystemTemplates
from app.features.systems.http_client import HTTPRAGSystem
from app.features.systems.mock_client import MockRAGSystem
from app.features.metrics.manager import MetricsManager, default_metrics_manager
from app.features.evaluations.model import EvaluationResult as EvaluationResultModel
from app.features.systems.model import RAGSystem

logger = logging.getLogger(__name__)


class EvaluationService:
    """RAG 시스템 평가 서비스"""
    
    def __init__(
        self, 
        dataset_loader: Optional[DatasetLoader] = None,
        metrics_manager: Optional[MetricsManager] = None
    ):
        """
        Args:
            dataset_loader: 데이터셋 로더 (None이면 기본 로더 사용)
            metrics_manager: 메트릭 매니저 (None이면 기본 매니저 사용)
        """
        self.dataset_loader = dataset_loader or DatasetLoader()
        self.metrics_manager = metrics_manager or default_metrics_manager
        self.classpath_converter = ClasspathConverter()
        self.classpath_matcher = ClasspathMatcher(self.classpath_converter)
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def evaluate_rag_system(
        self, 
        request: EvaluationRequest,
        db: Session
    ) -> EvaluationResponse:
        """
        RAG 시스템 평가 수행
        
        Args:
            request: 평가 요청
            db: 데이터베이스 세션
            
        Returns:
            평가 결과
        """
        try:
            # 1. 데이터셋 로드
            logger.info(f"데이터셋 로드 시작: {request.dataset_name}")
            questions, metadata = self.dataset_loader.load_dataset(request.dataset_name)
            
            # 2. RAG 시스템 초기화
            logger.info(f"RAG 시스템 초기화: {request.system_config.base_url}")
            rag_system = self._create_rag_system(request.system_config)
            
            # 3. 평가 실행
            logger.info(f"평가 시작: {len(questions)}개 질문")
            start_time = time.time()
            
            all_predictions = []
            all_ground_truth = []
            
            for question in questions:
                try:
                    # 질문에 대한 검색 수행
                    retrieval_results = await rag_system.retrieve(
                        question.question, 
                        top_k=max(request.k_values)
                    )
                    
                    # 검색 결과에서 예측값 추출
                    predictions = [result.content for result in retrieval_results]
                    
                    # 클래스패스 변환 적용
                    if request.options.convert_filepath_to_classpath:
                        predictions = self._convert_predictions_to_classpaths(
                            predictions, retrieval_results, request.options
                        )
                        ground_truth = self._convert_ground_truth_to_classpaths(
                            question.answer, request.options
                        )
                        logger.info(f"질문: {question.question[:50]}...")
                        logger.info(f"변환된 예측값: {predictions[:3]}")
                        logger.info(f"변환된 정답: {ground_truth}")
                    else:
                        ground_truth = question.answer if isinstance(question.answer, list) else [question.answer]
                    
                    all_predictions.append(predictions)
                    all_ground_truth.append(ground_truth)
                    
                except Exception as e:
                    logger.warning(f"질문 처리 중 오류: {str(e)}")
                    # 빈 결과로 처리
                    all_predictions.append([])
                    all_ground_truth.append([])
            
            # 4. 메트릭 계산
            logger.info("메트릭 계산 시작")
            metrics_results = {}
            
            for metric_name in request.metrics:
                if metric_name in self.metrics_manager.metrics:
                    metric_calculator = self.metrics_manager.metrics[metric_name]
                    
                    # k값별 메트릭 계산
                    metric_results = {}
                    for k in request.k_values:
                        scores = []
                        for pred, gt in zip(all_predictions, all_ground_truth):
                            score = metric_calculator.calculate(pred[:k], gt, k)
                            scores.append(score)
                        
                        avg_score = sum(scores) / len(scores) if scores else 0.0
                        metric_results[str(k)] = round(avg_score, 4)
                    
                    metrics_results[metric_name] = metric_results
            
            execution_time = time.time() - start_time
            
            # 5. 결과 저장 (옵션)
            if request.save_results:
                await self._save_evaluation_result(
                    db, request, metrics_results, execution_time, len(questions)
                )
            
            logger.info(f"평가 완료: {execution_time:.2f}초")
            
            # 6. 응답 생성
            return EvaluationResponse(
                dataset_name=request.dataset_name,
                system_name=request.system_config.name,
                metrics=metrics_results,
                execution_time=round(execution_time, 2),
                question_count=len(questions),
                k_values=request.k_values,
                options=request.options
            )
            
        except FileNotFoundError as e:
            logger.error(f"데이터셋 로드 실패: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"평가 중 오류 발생: {str(e)}")
            raise
        
        finally:
            # RAG 시스템 정리
            if 'rag_system' in locals():
                await rag_system.close()
    
    def _create_rag_system(self, system_config: SystemConfig) -> RAGSystemInterface:
        """RAG 시스템 생성"""
        # 새로운 RAGSystemConfig 형식인지 확인
        if hasattr(system_config, 'system_type') and hasattr(system_config, 'endpoints'):
            # 이미 RAGSystemConfig 형식
            return create_rag_system(system_config)
        
        # 기존 SystemConfig를 RAGSystemConfig로 변환
        from app.features.systems.interface import RAGSystemType
        
        if system_config.system_type == "mock":
            config = RAGSystemTemplates.mock_rag()
            return create_rag_system(config)
        elif system_config.system_type == "openai_rag":
            config = RAGSystemTemplates.openai_rag(
                api_key=getattr(system_config, 'api_key', None),
                base_url=system_config.base_url
            )
            return create_rag_system(config)
        elif system_config.system_type == "langchain_rag":
            config = RAGSystemTemplates.langchain_rag(
                base_url=system_config.base_url,
                api_key=getattr(system_config, 'api_key', None)
            )
            return create_rag_system(config)
        elif system_config.system_type == "llamaindex_rag":
            config = RAGSystemTemplates.llamaindex_rag(
                base_url=system_config.base_url,
                api_key=getattr(system_config, 'api_key', None)
            )
            return create_rag_system(config)
        elif system_config.system_type == "rag_server":
            config = RAGSystemTemplates.rag_server(
                base_url=system_config.base_url,
                api_key=getattr(system_config, 'api_key', None)
            )
            return create_rag_system(config)
        elif system_config.system_type == "codev_v1":
            config = RAGSystemTemplates.codev_v1(
                base_url=system_config.base_url
            )
            return create_rag_system(config)
        else:
            # 기본값: 커스텀 HTTP
            config = RAGSystemTemplates.custom_http_rag(
                name=system_config.name,
                base_url=system_config.base_url,
                api_key=getattr(system_config, 'api_key', None)
            )
            return create_rag_system(config)
    
    def _convert_predictions_to_classpaths(
        self, 
        predictions: List[str], 
        retrieval_results: List[Any],
        options: EvaluationOptions
    ) -> List[str]:
        """검색 결과를 클래스패스로 변환"""
        converted_predictions = []
        
        for i, prediction in enumerate(predictions):
            try:
                # 파일패스가 있으면 사용, 없으면 content에서 추출 시도
                if i < len(retrieval_results) and retrieval_results[i].filepath:
                    filepath = retrieval_results[i].filepath
                    logger.info(f"원본 파일패스: {filepath}")
                    classpath = self.classpath_converter.filepath_to_classpath(filepath)
                    logger.info(f"변환된 클래스패스: {classpath}")
                    
                    # 메서드명 제거 옵션 적용
                    if options.ignore_method_names and classpath:
                        classpath = self.classpath_converter.extract_class_from_classpath(
                            classpath, ignore_method=True
                        )
                        logger.info(f"메서드명 제거 후: {classpath}")
                    
                    converted_predictions.append(classpath or prediction)
                else:
                    # 파일패스가 없으면 원본 사용
                    logger.info(f"파일패스 없음, 원본 사용: {prediction}")
                    converted_predictions.append(prediction)
                    
            except Exception as e:
                logger.warning(f"클래스패스 변환 실패: {str(e)}")
                converted_predictions.append(prediction)
        
        return converted_predictions
    
    def _convert_ground_truth_to_classpaths(
        self, 
        ground_truth: Any, 
        options: EvaluationOptions
    ) -> List[str]:
        """정답을 클래스패스로 변환"""
        if isinstance(ground_truth, str):
            ground_truth_list = [ground_truth]
        elif isinstance(ground_truth, list):
            ground_truth_list = ground_truth
        else:
            ground_truth_list = [str(ground_truth)]
        
        converted_ground_truth = []
        
        for gt in ground_truth_list:
            try:
                # 이미 클래스패스 형태인지 확인 (간단한 휴리스틱)
                if "." in gt and not gt.endswith(".java"):
                    classpath = gt
                else:
                    # 파일패스에서 클래스패스로 변환
                    classpath = self.classpath_converter.filepath_to_classpath(gt)
                
                # 메서드명 제거 옵션 적용
                if options.ignore_method_names and classpath:
                    classpath = self.classpath_converter.extract_class_from_classpath(
                        classpath, ignore_method=True
                    )
                
                converted_ground_truth.append(classpath or gt)
                
            except Exception as e:
                logger.warning(f"정답 클래스패스 변환 실패: {str(e)}")
                converted_ground_truth.append(gt)
        
        return converted_ground_truth
    
    async def _save_evaluation_result(
        self,
        db: Session,
        request: EvaluationRequest,
        metrics_results: Dict[str, Dict[str, float]],
        execution_time: float,
        question_count: int
    ) -> None:
        """평가 결과를 데이터베이스에 저장"""
        try:
            # RAG 시스템 정보 조회 또는 생성
            rag_system = db.query(RAGSystem).filter(
                RAGSystem.name == request.system_config.name
            ).first()
            
            if not rag_system:
                rag_system = RAGSystem(
                    name=request.system_config.name,
                    description=f"Auto-created for evaluation",
                    base_url=request.system_config.base_url,
                    system_type=request.system_config.system_type
                )
                db.add(rag_system)
                db.flush()  # ID 생성을 위해
            
            # 평가 결과 저장
            evaluation_result = EvaluationResultModel(
                system_id=rag_system.id,
                dataset_id=request.dataset_name,
                metrics=metrics_results,
                execution_time=execution_time,
                config={
                    "k_values": request.k_values,
                    "metrics": request.metrics,
                    "options": request.options.model_dump(),
                    "question_count": question_count
                },
                status="completed"
            )
            
            db.add(evaluation_result)
            db.commit()
            
            logger.info(f"평가 결과 저장 완료: ID {evaluation_result.id}")
            
        except Exception as e:
            logger.error(f"평가 결과 저장 실패: {str(e)}")
            db.rollback()
            # 저장 실패해도 평가는 계속 진행
    
    async def get_available_datasets(self) -> List[str]:
        """사용 가능한 데이터셋 목록 조회"""
        try:
            return self.dataset_loader.list_datasets()
        except Exception as e:
            logger.error(f"데이터셋 목록 조회 실패: {str(e)}")
            return []
    
    async def get_dataset_info(self, dataset_name: str) -> Dict[str, Any]:
        """데이터셋 정보 조회"""
        try:
            questions, metadata = self.dataset_loader.load_dataset(dataset_name)
            
            return {
                "name": dataset_name,
                "metadata": metadata.model_dump(),
                "question_count": len(questions),
                "sample_questions": [q.model_dump() for q in questions[:3]]  # 처음 3개만
            }
        except Exception as e:
            logger.error(f"데이터셋 정보 조회 실패: {str(e)}")
            raise
    
    def get_available_metrics(self) -> Dict[str, Dict[str, str]]:
        """사용 가능한 메트릭 정보 조회"""
        return self.metrics_manager.get_metric_info()
    
    async def test_classpath_conversion(
        self, 
        filepaths: List[str], 
        options: EvaluationOptions
    ) -> Dict[str, str]:
        """클래스패스 변환 테스트 (디버깅용)"""
        results = {}
        
        for filepath in filepaths:
            try:
                classpath = self.classpath_converter.filepath_to_classpath(filepath)
                
                if options.ignore_method_names and classpath:
                    classpath = self.classpath_converter.extract_class_from_classpath(
                        classpath, ignore_method=True
                    )
                
                results[filepath] = classpath or f"No conversion for: {filepath}"
                
            except Exception as e:
                results[filepath] = f"Error: {str(e)}"
        
        return results
    
    async def close(self):
        """리소스 정리"""
        await self.http_client.aclose()


def create_evaluation_service() -> EvaluationService:
    """평가 서비스 인스턴스 생성"""
    return EvaluationService()


# 전역 평가 서비스 인스턴스
evaluation_service = EvaluationService() 