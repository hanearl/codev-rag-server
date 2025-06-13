#!/usr/bin/env python3
"""
검색 비교 E2E 테스트 실행 스크립트

BM25, Vector, Hybrid 검색 방식을 비교하는 E2E 테스트를 실행합니다.
"""
import subprocess
import sys
import os
import time
import requests
from pathlib import Path


def check_service_health(url: str, service_name: str, timeout: int = 30) -> bool:
    """서비스 헬스체크"""
    print(f"🔍 {service_name} 서비스 헬스체크 중...")
    
    for i in range(timeout):
        try:
            response = requests.get(url, timeout=5.0)
            if response.status_code == 200:
                print(f"✅ {service_name} 서비스 정상")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if i % 5 == 0:
            print(f"   대기 중... ({i}/{timeout}초)")
        time.sleep(1)
    
    print(f"❌ {service_name} 서비스 응답 없음")
    return False


def wait_for_services():
    """모든 서비스가 준비될 때까지 대기"""
    print("\n🔄 서비스 준비 대기 중...")
    
    services = [
        ("http://localhost:8000/health", "RAG Server")
    ]
    
    all_healthy = True
    for url, name in services:
        if not check_service_health(url, name):
            all_healthy = False
    
    if not all_healthy:
        print("\n❌ 일부 서비스가 준비되지 않았습니다.")
        print("다음 명령으로 서비스를 시작하세요:")
        print("  cd rag-server && uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return False
    
    print("\n✅ 모든 서비스가 준비되었습니다!")
    return True


def run_test():
    """테스트 실행"""
    print("\n🧪 검색 비교 E2E 테스트 실행 중...")
    
    # 현재 디렉토리를 rag-server로 변경
    os.chdir(Path(__file__).parent)
    
    try:
        # pytest 실행
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/e2e/test_search_comparison.py",
            "-v",
            "-s",
            "--tb=short"
        ]
        
        print(f"실행 명령: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n🎉 검색 비교 E2E 테스트 성공!")
        else:
            print(f"\n❌ 테스트 실패 (종료 코드: {result.returncode})")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류: {e}")
        return False


def main():
    """메인 함수"""
    print("=" * 80)
    print("🚀 검색 방식 비교 E2E 테스트 시작")
    print("=" * 80)
    
    # 서비스 준비 확인
    if not wait_for_services():
        return 1
    
    # 테스트 실행
    success = run_test()
    
    print("\n" + "=" * 80)
    if success:
        print("🎉 검색 비교 테스트가 성공적으로 완료되었습니다!")
    else:
        print("❌ 검색 비교 테스트가 실패했습니다.")
    print("=" * 80)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 