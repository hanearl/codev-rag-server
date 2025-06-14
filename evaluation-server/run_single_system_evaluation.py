#!/usr/bin/env python3
"""
단일 시스템 평가 스크립트 - 로컬 테스트용

codev-v1 시스템만 사용하여 combined-dataset으로 평가를 실행합니다.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any
import httpx

from app.features.systems.factory import RAGSystemTemplates, create_rag_system
from app.features.systems.interface import RAGSystemInterface
from app.features.evaluation.service import EvaluationService
from app.features.evaluation.schema import (
    EvaluationRequest,
    SystemConfig,
    EvaluationOptions
)
from app.db.database import SessionLocal

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('single_evaluation_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SingleSystemEvaluator:
    """단일 시스템 평가 실행기"""
    
    def __init__(self):
        self.evaluation_service = EvaluationService()
        
    def create_codev_v1_system(self) -> RAGSystemInterface:
        """Codev V1 시스템 생성"""
        logger.info("Codev V1 시스템 생성 중...")
        codev_config = RAGSystemTemplates.codev_v1(
            base_url="http://10.250.121.100:8008"
        )
        return create_rag_system(codev_config)
    
    async def check_system_health(self, system: RAGSystemInterface) -> bool:
        """시스템 헬스체크"""
        try:
            is_healthy = await system.health_check()
            status = "정상" if is_healthy else "비정상"
            logger.info(f"codev-v1: {status}")
            return is_healthy
        except Exception as e:
            logger.error(f"codev-v1 헬스체크 실패: {e}")
            return False
    
    def create_evaluation_request(self, system_name: str, system_config: Any) -> EvaluationRequest:
        """평가 요청 생성"""
        return EvaluationRequest(
            dataset_name="combined-dataset",
            system_config=SystemConfig(
                name=system_name,
                base_url=getattr(system_config, 'base_url', 'http://10.250.121.100:8008'),
                system_type="codev_v1",  # 명시적으로 codev_v1 설정
                api_key=getattr(system_config, 'api_key', None)
            ),
            metrics=[
                "precision",  # 정밀도
                "recall",     # 재현율  
                "f1",         # F1 스코어
                "map",        # Mean Average Precision
                "mrr",        # Mean Reciprocal Rank
                "ndcg"        # Normalized Discounted Cumulative Gain
            ],
            k_values=[1, 3, 5, 10],  # Top-K 값들
            options=EvaluationOptions(
                convert_filepath_to_classpath=True,
                exclude_method_names=True,
                filepath_weight=0.8,
                content_weight=0.2
            ),
            save_results=True
        )
    
    async def run_evaluation(self) -> Dict[str, Any]:
        """평가 실행"""
        logger.info("=" * 60)
        logger.info("Codev V1 시스템 평가 시작")
        logger.info("=" * 60)
        
        system = None
        try:
            # 1. 시스템 생성
            system = self.create_codev_v1_system()
            
            # 2. 헬스체크
            is_healthy = await self.check_system_health(system)
            
            if not is_healthy:
                logger.error("시스템이 정상 상태가 아닙니다. 평가를 중단합니다.")
                return {"success": False, "error": "헬스체크 실패"}
            
            # 3. 평가 실행
            logger.info("=== codev-v1 평가 시작 ===")
            
            db = SessionLocal()
            try:
                # 평가 요청 생성
                request = self.create_evaluation_request("codev-v1", system.config)
                
                # 평가 실행
                start_time = time.time()
                result = await self.evaluation_service.evaluate_rag_system(request, db)
                execution_time = time.time() - start_time
                
                logger.info(f"codev-v1 평가 완료: {execution_time:.2f}초")
                
                # 결과 요약 로깅
                self.log_evaluation_summary("codev-v1", result)
                
                # 결과 저장
                await self.save_results({
                    "system_name": "codev-v1",
                    "system_type": str(system.config.system_type),
                    "retrieval_type": str(system.config.retrieval_type),
                    "result": result,
                    "execution_time": execution_time,
                    "success": True,
                    "error": None
                })
                
                return {
                    "success": True,
                    "result": result,
                    "execution_time": execution_time
                }
                
            except Exception as e:
                logger.error(f"codev-v1 평가 실패: {e}")
                return {"success": False, "error": str(e)}
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"시스템 생성 실패: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if system:
                try:
                    await system.close()
                except Exception as e:
                    logger.warning(f"시스템 정리 중 오류: {e}")
    
    def log_evaluation_summary(self, system_name: str, result):
        """평가 결과 요약 로깅"""
        logger.info(f"\n{system_name} 결과 요약:")
        logger.info(f"  데이터셋: {result.dataset_name}")
        logger.info(f"  질문 수: {result.question_count}")
        logger.info(f"  실행 시간: {result.execution_time}초")
        
        # 메트릭별 결과 출력
        for metric_name, metric_values in result.metrics.items():
            logger.info(f"  {metric_name.upper()}:")
            for k, value in metric_values.items():
                logger.info(f"    @{k}: {value:.4f}")
    
    async def save_results(self, result: Dict[str, Any]):
        """결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"single_evaluation_result_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"결과 파일 저장: {results_file}")


async def main():
    """메인 실행 함수"""
    try:
        evaluator = SingleSystemEvaluator()
        result = await evaluator.run_evaluation()
        
        if result["success"]:
            logger.info("평가가 성공적으로 완료되었습니다!")
        else:
            logger.error(f"평가 실패: {result.get('error', '알 수 없는 오류')}")
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"평가 실행 중 오류: {e}")
        raise
    finally:
        # 정리 작업
        try:
            # evaluation_service cleanup
            pass
        except:
            pass


if __name__ == "__main__":
    # Python 스크립트로 직접 실행
    asyncio.run(main()) 