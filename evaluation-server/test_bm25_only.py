#!/usr/bin/env python3
"""
BM25 검색만 테스트하는 스크립트
"""

import asyncio
import logging
from app.features.systems.factory import create_rag_server_bm25
from app.features.evaluation.service import EvaluationService
from app.features.evaluation.schema import (
    EvaluationRequest,
    SystemConfig,
    EvaluationOptions
)
from app.db.database import SessionLocal

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_bm25_only():
    """BM25 검색만 테스트"""
    
    # 1. BM25 시스템 생성 (올바른 인덱스명 사용)
    logger.info("BM25 시스템 생성 중...")
    bm25_system = create_rag_server_bm25(
        base_url="http://localhost:8000",
        index_name="default",
        name="test-bm25"
    )
    
    try:
        # 2. 헬스체크
        logger.info("헬스체크 수행 중...")
        is_healthy = await bm25_system.health_check()
        logger.info(f"헬스체크 결과: {'정상' if is_healthy else '비정상'}")
        
        if not is_healthy:
            logger.error("헬스체크 실패, 종료")
            return
        
        # 3. 간단한 검색 테스트
        logger.info("검색 테스트 수행 중...")
        results = await bm25_system.retrieve("FastAPI 라우터", top_k=3)
        logger.info(f"검색 결과: {len(results)}개")
        
        for i, result in enumerate(results):
            logger.info(f"  {i+1}. Score: {result.score:.4f}, Content: {result.content[:100]}...")
        
        # 4. 평가 테스트 (최소 5개 질문만)
        logger.info("평가 테스트 수행 중...")
        evaluation_service = EvaluationService()
        
        request = EvaluationRequest(
            dataset_name="combined-dataset",
            system_config=SystemConfig(
                name="test-bm25",
                base_url="http://localhost:8000",
                system_type="rag_server_bm25",
                api_key=None
            ),
            metrics=["precision", "recall"],
            k_values=[1, 3, 5],
            options=EvaluationOptions(
                convert_filepath_to_classpath=True,
                exclude_method_names=True,
                filepath_weight=0.8,
                content_weight=0.2,
                max_questions=5  # 최소한의 테스트만
            ),
            save_results=False
        )
        
        db = SessionLocal()
        try:
            result = await evaluation_service.evaluate_rag_system(request, db)
            logger.info(f"평가 완료: {result.question_count}개 질문")
            
            for metric_name, values in result.metrics.items():
                logger.info(f"{metric_name}: {values}")
                
        finally:
            db.close()
        
    finally:
        await bm25_system.close()

if __name__ == "__main__":
    asyncio.run(test_bm25_only()) 