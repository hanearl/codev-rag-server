#!/bin/bash

echo "🚀 개발 환경 설정 시작..."

# 환경 변수 확인
if [ ! -f .env ]; then
    echo "❌ .env 파일이 없습니다."
    echo "📝 env.example을 참고하여 .env 파일을 생성해주세요:"
    echo "   cp env.example .env"
    echo "   # .env 파일을 편집하여 OPENAI_API_KEY 등을 설정하세요"
    exit 1
fi

# Docker 및 Docker Compose 확인
if ! command -v docker &> /dev/null; then
    echo "❌ Docker가 설치되지 않았습니다."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose가 설치되지 않았습니다."
    exit 1
fi

# Docker Compose 파일 검증
echo "🔍 Docker Compose 설정 검증 중..."
docker-compose -f docker-compose.dev.yml config > /dev/null
if [ $? -ne 0 ]; then
    echo "❌ Docker Compose 설정에 오류가 있습니다."
    exit 1
fi
echo "✅ Docker Compose 설정 검증 완료"

# 필요한 디렉토리 생성
echo "📁 필요한 디렉토리 생성 중..."
mkdir -p data/qdrant
mkdir -p vector-db/backups
mkdir -p test-codebase

# 서비스 시작
echo "📦 Docker Compose 서비스 시작..."
docker-compose -f docker-compose.dev.yml up -d

# 서비스 시작 대기
echo "⏳ 서비스 시작 대기 중..."
sleep 30

# 서비스 헬스체크
echo "🔍 서비스 헬스체크..."
./scripts/health-check.sh

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 개발 환경 설정 완료!"
    echo ""
    echo "🌐 서비스 URL:"
    echo "  - Vector DB (Qdrant): http://localhost:6333"
    echo "  - Embedding Server: http://localhost:8001"
    echo "  - LLM Server: http://localhost:8002"
    echo "  - RAG Server: http://localhost:8000 (구현 후)"
    echo ""
    echo "📊 대시보드:"
    echo "  - Qdrant Dashboard: http://localhost:6333/dashboard"
    echo ""
    echo "🔧 유용한 명령어:"
    echo "  - 로그 확인: make logs"
    echo "  - 서비스 중지: make down"
    echo "  - 헬스체크: make health"
    echo "  - 데이터베이스 초기화: make init-db"
else
    echo "❌ 일부 서비스가 정상적으로 시작되지 않았습니다."
    echo "📋 로그를 확인해주세요: make logs"
    exit 1
fi 