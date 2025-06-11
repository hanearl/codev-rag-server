#!/bin/bash

services=(
    "http://localhost:6333/health"
    "http://localhost:8001/health"
    "http://localhost:8002/health"
)

service_names=(
    "Vector DB (Qdrant)"
    "Embedding Server"
    "LLM Server"
)

all_healthy=true

for i in "${!services[@]}"; do
    service_url="${services[$i]}"
    service_name="${service_names[$i]}"
    
    echo "⏳ $service_name 헬스체크 중..."
    
    # 최대 30번 시도 (60초)
    for attempt in {1..30}; do
        if curl -f -s "$service_url" > /dev/null 2>&1; then
            echo "✅ $service_name 정상"
            break
        fi
        
        if [ $attempt -eq 30 ]; then
            echo "❌ $service_name 헬스체크 실패 (60초 타임아웃)"
            all_healthy=false
            break
        fi
        
        sleep 2
    done
done

if [ "$all_healthy" = true ]; then
    echo ""
    echo "🎉 모든 서비스 정상 동작!"
    exit 0
else
    echo ""
    echo "💥 일부 서비스에 문제가 있습니다."
    echo "📋 다음 명령어로 로그를 확인하세요:"
    echo "   make logs"
    exit 1
fi 