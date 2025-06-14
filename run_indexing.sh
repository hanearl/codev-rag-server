#!/bin/bash

# Spring Boot 샘플 프로젝트 인덱싱 실행 스크립트

echo "=== Spring Boot 샘플 프로젝트 RAG 인덱싱 시작 ==="
echo ""

# RAG 서버가 실행 중인지 확인
echo "1. RAG 서버 상태 확인 중..."
if curl -s http://localhost:8000/api/v1/indexing/health > /dev/null; then
    echo "✅ RAG 서버가 정상적으로 실행 중입니다."
else
    echo "❌ RAG 서버가 실행되지 않았거나 응답하지 않습니다."
    echo "먼저 RAG 서버를 시작하세요:"
    echo "  cd rag-server && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    exit 1
fi

echo ""
echo "2. 필요한 Python 패키지 확인 중..."
python3 -c "import httpx, asyncio; print('✅ 필요한 패키지가 설치되어 있습니다.')" 2>/dev/null || {
    echo "❌ 필요한 패키지를 설치합니다..."
    pip install httpx asyncio
}

echo ""
echo "3. 프로젝트 경로 확인 중..."
if [ -d "data/springboot-sample-pjt" ]; then
    echo "✅ 프로젝트 경로를 찾았습니다: data/springboot-sample-pjt"
    echo "   Java 파일 개수: $(find data/springboot-sample-pjt -name "*.java" | wc -l | tr -d ' ')"
else
    echo "❌ 프로젝트 경로를 찾을 수 없습니다: data/springboot-sample-pjt"
    exit 1
fi

echo ""
echo "4. 인덱싱 시작..."
echo "   - Vector 인덱싱과 BM25 인덱싱을 모두 수행합니다"
echo "   - 컬렉션명: springboot-sample-pjt"
echo "   - 로그는 indexing.log 파일에 저장됩니다"
echo ""

# 인덱싱 실행
python3 index_sample_project.py

# 결과 확인
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 인덱싱이 성공적으로 완료되었습니다!"
    echo ""
    echo "📊 결과 파일들:"
    ls -la indexing_result_*.json 2>/dev/null | tail -1
    ls -la indexing.log 2>/dev/null
    echo ""
    echo "🔍 인덱스 테스트:"
    echo "  Vector 검색 테스트: curl -X POST http://localhost:8000/api/v1/search/vector -H 'Content-Type: application/json' -d '{\"query\": \"BookController\", \"collection_name\": \"springboot-sample-pjt\", \"top_k\": 5}'"
    echo "  BM25 검색 테스트: curl -X POST http://localhost:8000/api/v1/search/bm25 -H 'Content-Type: application/json' -d '{\"query\": \"BookController\", \"collection_name\": \"springboot-sample-pjt\", \"top_k\": 5}'"
    echo "  하이브리드 검색 테스트: curl -X POST http://localhost:8000/api/v1/search/hybrid -H 'Content-Type: application/json' -d '{\"query\": \"BookController\", \"collection_name\": \"springboot-sample-pjt\", \"top_k\": 5}'"
else
    echo ""
    echo "❌ 인덱싱 중 오류가 발생했습니다."
    echo "상세한 오류 정보는 indexing.log 파일을 확인하세요."
    exit 1
fi 