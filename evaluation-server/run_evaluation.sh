#!/bin/bash

# 5개 RAG 시스템 종합 평가 실행 스크립트

set -e

echo "=============================================="
echo "RAG 시스템 종합 평가 시작"
echo "=============================================="

# 현재 디렉토리 확인
if [ ! -f "run_comprehensive_evaluation.py" ]; then
    echo "오류: run_comprehensive_evaluation.py 파일을 찾을 수 없습니다."
    echo "evaluation-server 디렉토리에서 실행해주세요."
    exit 1
fi

# 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    echo "가상환경 활성화 중..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "가상환경 활성화 중..."
    source .venv/bin/activate
fi

# 필요한 패키지 설치 확인
echo "패키지 의존성 확인 중..."
python -c "import app.features.systems.factory" 2>/dev/null || {
    echo "오류: 필요한 패키지가 설치되지 않았습니다."
    echo "pip install -r requirements.txt를 실행해주세요."
    exit 1
}

# 데이터셋 존재 확인
if [ ! -d "datasets/combined-dataset" ]; then
    echo "경고: datasets/combined-dataset 디렉토리를 찾을 수 없습니다."
    echo "평가가 실패할 수 있습니다."
fi

# 로그 디렉토리 생성
mkdir -p logs

# 시작 시간 기록
START_TIME=$(date)
echo "시작 시간: $START_TIME"

# 평가 실행
echo ""
echo "평가 실행 중..."
echo "진행 상황은 evaluation_results.log 파일에서 확인할 수 있습니다."
echo ""

# Python 스크립트 실행
python run_comprehensive_evaluation.py

# 종료 시간 기록
END_TIME=$(date)
echo ""
echo "=============================================="
echo "평가 완료"
echo "시작 시간: $START_TIME"
echo "종료 시간: $END_TIME"
echo "=============================================="

# 결과 파일 목록 표시
echo ""
echo "생성된 파일들:"
ls -la comprehensive_evaluation_results_*.json 2>/dev/null || echo "  - 결과 JSON 파일 없음"
ls -la evaluation_results.log 2>/dev/null || echo "  - 로그 파일 없음"

echo ""
echo "평가 결과를 확인하려면 다음 명령어를 실행하세요:"
echo "  cat evaluation_results.log | grep -A 20 '성능 비교'"
echo "  또는"
echo "  python -c \"import json; print(json.dumps(json.load(open('comprehensive_evaluation_results_$(date +%Y%m%d)*.json')), indent=2))\""

exit 0 