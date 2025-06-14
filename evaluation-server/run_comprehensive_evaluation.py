#!/usr/bin/env python3
"""
5개 RAG 시스템 종합 평가 스크립트

이 스크립트는 다음 시스템들을 combined-dataset으로 평가합니다:
1. rag-server-vector (벡터 검색)
2. rag-server-bm25 (BM25 검색)  
3. rag-server-hybrid (하이브리드 검색)
4. rag-server (기존 레거시 시스템)
5. codev-v1 (기존 Codev V1 시스템)
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from app.features.systems.factory import (
    RAGSystemTemplates,
    create_rag_system,
    create_rag_server_vector,
    create_rag_server_bm25,
    create_rag_server_hybrid
)
from app.features.systems.interface import RAGSystemInterface, RAGSystemType, RetrievalType
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
        logging.FileHandler('evaluation_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ComprehensiveEvaluator:
    """종합 평가 실행기"""
    
    def __init__(self):
        self.evaluation_service = EvaluationService()
        self.results = []
        
    def create_rag_systems(self) -> Dict[str, RAGSystemInterface]:
        """5개 RAG 시스템 생성"""
        systems = {}
        
        try:
            # 1. RAG 서버 벡터 검색
            logger.info("RAG 서버 벡터 검색 시스템 생성 중...")
            systems["rag-server-vector"] = create_rag_server_vector(
                base_url="http://localhost:8000",
                collection_name="springboot-real-test",
                name="rag-server-vector"
            )
            
            # 2. RAG 서버 BM25 검색
            logger.info("RAG 서버 BM25 검색 시스템 생성 중...")
            systems["rag-server-bm25"] = create_rag_server_bm25(
                base_url="http://localhost:8000",
                index_name="springboot-real-test",
                name="rag-server-bm25"
            )
            
            # 3. RAG 서버 하이브리드 검색
            logger.info("RAG 서버 하이브리드 검색 시스템 생성 중...")
            systems["rag-server-hybrid"] = create_rag_server_hybrid(
                base_url="http://localhost:8000",
                collection_name="springboot-real-test",
                index_name="springboot-real-test",
                vector_weight=0.7,
                bm25_weight=0.3,
                use_rrf=True,
                rrf_k=60,
                name="rag-server-hybrid"
            )
            
            # 4. RAG 서버 (레거시 - 하이브리드 검색 사용)
            logger.info("기존 RAG 서버 시스템 생성 중...")
            legacy_config = RAGSystemTemplates.rag_server_hybrid(
                base_url="http://localhost:8000"
            )
            legacy_config.name = "rag-server-legacy"
            legacy_config.collection_name = "springboot-real-test"
            legacy_config.index_name = "springboot-real-test"
            systems["rag-server-legacy"] = create_rag_system(legacy_config)
            
            # 5. Codev V1
            logger.info("Codev V1 시스템 생성 중...")
            codev_config = RAGSystemTemplates.codev_v1(
                base_url="http://10.250.121.100:8008"
            )
            systems["codev-v1"] = create_rag_system(codev_config)
            
            logger.info(f"총 {len(systems)}개 시스템 생성 완료")
            return systems
            
        except Exception as e:
            logger.error(f"시스템 생성 실패: {e}")
            # 이미 생성된 시스템들 정리
            for system in systems.values():
                try:
                    asyncio.run(system.close())
                except:
                    pass
            raise
    
    async def check_system_health(self, systems: Dict[str, RAGSystemInterface]) -> Dict[str, bool]:
        """시스템 헬스체크"""
        logger.info("시스템 헬스체크 시작...")
        health_status = {}
        
        for name, system in systems.items():
            try:
                is_healthy = await system.health_check()
                health_status[name] = is_healthy
                status = "정상" if is_healthy else "비정상"
                logger.info(f"{name}: {status}")
            except Exception as e:
                health_status[name] = False
                logger.error(f"{name} 헬스체크 실패: {e}")
        
        healthy_count = sum(health_status.values())
        logger.info(f"헬스체크 완료: {healthy_count}/{len(systems)}개 시스템 정상")
        
        return health_status
    
    def create_evaluation_request(self, system_name: str, system_config: Any) -> EvaluationRequest:
        """평가 요청 생성"""
        # system_name에 따라 system_type 명시적 설정
        if system_name == "codev-v1":
            system_type = "codev_v1"
        else:
            system_type = str(getattr(system_config, 'system_type', 'unknown'))
        
        return EvaluationRequest(
            dataset_name="combined-dataset",
            system_config=SystemConfig(
                name=system_name,
                base_url=getattr(system_config, 'base_url', 'unknown'),
                system_type=system_type,
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
    
    async def run_single_evaluation(self, system_name: str, system: RAGSystemInterface) -> Dict[str, Any]:
        """단일 시스템 평가 실행"""
        logger.info(f"=== {system_name} 평가 시작 ===")
        
        db = SessionLocal()
        try:
            # 평가 요청 생성
            request = self.create_evaluation_request(system_name, system.config)
            
            # 평가 실행
            start_time = time.time()
            result = await self.evaluation_service.evaluate_rag_system(request, db)
            execution_time = time.time() - start_time
            
            logger.info(f"{system_name} 평가 완료: {execution_time:.2f}초")
            
            # 결과 요약 로깅
            self.log_evaluation_summary(system_name, result)
            
            return {
                "system_name": system_name,
                "system_type": str(system.config.system_type),
                "retrieval_type": str(system.config.retrieval_type),
                "result": result,
                "execution_time": execution_time,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"{system_name} 평가 실패: {e}")
            return {
                "system_name": system_name,
                "system_type": "unknown",
                "retrieval_type": "unknown", 
                "result": None,
                "execution_time": 0,
                "success": False,
                "error": str(e)
            }
        finally:
            db.close()
    
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
    
    async def run_comprehensive_evaluation(self):
        """종합 평가 실행"""
        logger.info("=" * 60)
        logger.info("5개 RAG 시스템 종합 평가 시작")
        logger.info("=" * 60)
        
        systems = {}
        try:
            # 1. 시스템 생성
            systems = self.create_rag_systems()
            
            # 2. 헬스체크
            health_status = await self.check_system_health(systems)
            
            # 3. 각 시스템별 평가 실행
            evaluation_results = []
            
            for system_name, system in systems.items():
                if health_status.get(system_name, False):
                    result = await self.run_single_evaluation(system_name, system)
                    evaluation_results.append(result)
                else:
                    logger.warning(f"{system_name} 스킵 (헬스체크 실패)")
                    evaluation_results.append({
                        "system_name": system_name,
                        "success": False,
                        "error": "헬스체크 실패"
                    })
            
            # 4. 결과 분석 및 저장
            await self.analyze_and_save_results(evaluation_results)
            
            logger.info("=" * 60)
            logger.info("종합 평가 완료")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"종합 평가 실패: {e}")
            raise
        finally:
            # 시스템 정리
            for system in systems.values():
                try:
                    await system.close()
                except Exception as e:
                    logger.warning(f"시스템 정리 중 오류: {e}")
    
    async def analyze_and_save_results(self, results: List[Dict[str, Any]]):
        """결과 분석 및 저장"""
        logger.info("\n=== 평가 결과 분석 ===")
        
        # 성공한 평가만 필터링
        successful_results = [r for r in results if r.get("success", False)]
        failed_results = [r for r in results if not r.get("success", False)]
        
        logger.info(f"성공: {len(successful_results)}개, 실패: {len(failed_results)}개")
        
        if failed_results:
            logger.warning("실패한 평가:")
            for result in failed_results:
                logger.warning(f"  - {result['system_name']}: {result.get('error', '알 수 없는 오류')}")
        
        if successful_results:
            # 성능 비교 테이블 생성
            self.create_performance_comparison(successful_results)
            
            # 결과를 JSON 파일로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f"comprehensive_evaluation_results_{timestamp}.json"
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"결과 파일 저장: {results_file}")
    
    def create_performance_comparison(self, results: List[Dict[str, Any]]):
        """성능 비교 테이블 생성"""
        logger.info("\n=== 성능 비교 (F1@10 기준) ===")
        
        # F1@10 점수로 정렬
        sorted_results = sorted(
            results,
            key=lambda x: x['result'].metrics.get('f1', {}).get('10', 0),
            reverse=True
        )
        
        print("\n시스템별 성능 순위:")
        print("-" * 80)
        print(f"{'순위':<4} {'시스템명':<20} {'검색타입':<10} {'F1@10':<8} {'실행시간(초)':<12}")
        print("-" * 80)
        
        for i, result in enumerate(sorted_results, 1):
            system_name = result['system_name']
            retrieval_type = result.get('retrieval_type', 'unknown')
            f1_10 = result['result'].metrics.get('f1', {}).get('10', 0)
            exec_time = result['execution_time']
            
            print(f"{i:<4} {system_name:<20} {retrieval_type:<10} {f1_10:<8.4f} {exec_time:<12.2f}")
        
        print("-" * 80)
        
        # 상세 메트릭 비교
        logger.info("\n=== 상세 메트릭 비교 ===")
        for result in sorted_results:
            system_name = result['system_name']
            metrics = result['result'].metrics
            
            print(f"\n{system_name}:")
            for metric_name, metric_values in metrics.items():
                values_str = ", ".join([f"@{k}:{v:.4f}" for k, v in metric_values.items()])
                print(f"  {metric_name.upper()}: {values_str}")


async def main():
    """메인 실행 함수"""
    try:
        evaluator = ComprehensiveEvaluator()
        await evaluator.run_comprehensive_evaluation()
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"평가 실행 중 오류: {e}")
        raise
    finally:
        # 정리 작업
        try:
            await evaluator.evaluation_service.close()
        except:
            pass


if __name__ == "__main__":
    # Python 스크립트로 직접 실행
    asyncio.run(main()) 