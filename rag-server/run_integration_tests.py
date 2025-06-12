#!/usr/bin/env python3
"""
RAG 시스템 통합 테스트 실행 스크립트

이 스크립트는 Task 06에서 정의한 모든 통합 테스트를 순차적으로 실행합니다.
"""

import subprocess
import sys
import time
import os
import argparse
from pathlib import Path


def print_header(title: str):
    """테스트 섹션 헤더 출력"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def run_command(command: list, description: str, timeout: int = 300) -> bool:
    """명령어 실행 및 결과 반환"""
    print(f"\n🔄 {description}")
    print(f"   명령어: {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=Path(__file__).parent
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - 성공")
            if result.stdout:
                print("   출력:")
                print("   " + "\n   ".join(result.stdout.strip().split('\n')))
            return True
        else:
            print(f"❌ {description} - 실패 (코드: {result.returncode})")
            if result.stderr:
                print("   에러:")
                print("   " + "\n   ".join(result.stderr.strip().split('\n')))
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - 타임아웃 ({timeout}초)")
        return False
    except Exception as e:
        print(f"💥 {description} - 예외 발생: {e}")
        return False


def check_services_health():
    """모든 서비스 헬스체크"""
    print_header("서비스 상태 확인")
    
    services = {
        "RAG Server": "http://localhost:8000/health",
        "Embedding Server": "http://localhost:8001/health", 
        "LLM Server": "http://localhost:8002/health",
        "Vector DB": "http://localhost:6333/health"
    }
    
    import requests
    
    all_healthy = True
    for service_name, url in services.items():
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ {service_name}: 정상")
            else:
                print(f"❌ {service_name}: HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            print(f"💀 {service_name}: 연결 실패 - {e}")
            all_healthy = False
    
    return all_healthy


def run_e2e_tests():
    """E2E 테스트 실행"""
    print_header("E2E 테스트 실행")
    
    test_commands = [
        {
            "cmd": ["python", "-m", "pytest", "tests/e2e/test_complete_workflow.py", "-v", "-s"],
            "desc": "전체 워크플로우 E2E 테스트",
            "timeout": 600  # 10분
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/e2e/test_failure_scenarios.py::TestFailureScenarios::test_embedding_service_failure_recovery", "-v", "-s"],
            "desc": "임베딩 서비스 장애 복구 테스트",
            "timeout": 300
        },
        {
            "cmd": ["python", "-m", "pytest", "tests/e2e/test_production_readiness.py", "-v", "-s"],
            "desc": "운영 준비성 테스트",
            "timeout": 180
        }
    ]
    
    passed = 0
    total = len(test_commands)
    
    for test in test_commands:
        if run_command(test["cmd"], test["desc"], test["timeout"]):
            passed += 1
    
    print(f"\n📊 E2E 테스트 결과: {passed}/{total} 통과")
    return passed == total


def run_performance_tests():
    """성능 테스트 실행"""
    print_header("성능 테스트 실행")
    
    # Locust 성능 테스트 (헤드리스 모드로 짧게 실행)
    locust_cmd = [
        "locust", 
        "-f", "tests/performance/locustfile.py",
        "--host", "http://localhost:8000",
        "--users", "10",
        "--spawn-rate", "2", 
        "--run-time", "60s",
        "--headless"
    ]
    
    performance_passed = run_command(
        locust_cmd, 
        "Locust 부하 테스트 (60초)", 
        timeout=120
    )
    
    return performance_passed


def run_integration_tests():
    """통합 테스트 실행"""
    print_header("통합 테스트 실행")
    
    integration_cmd = [
        "python", "-m", "pytest", 
        "tests/integration/", 
        "-v", "-x", "--tb=short"
    ]
    
    return run_command(
        integration_cmd,
        "기존 통합 테스트",
        timeout=300
    )


def generate_test_report(results: dict):
    """테스트 결과 리포트 생성"""
    print_header("테스트 결과 요약")
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    print(f"📊 전체 테스트 결과: {passed_tests}/{total_tests}")
    print()
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print()
    
    if passed_tests == total_tests:
        print("🎉 모든 테스트가 통과했습니다!")
        print("✅ 시스템이 운영 환경 배포 준비가 완료되었습니다.")
        return True
    else:
        print("⚠️ 일부 테스트가 실패했습니다.")
        print("🔧 실패한 테스트를 확인하고 문제를 해결해주세요.")
        return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="RAG 시스템 통합 테스트 실행")
    parser.add_argument("--skip-health", action="store_true", help="헬스체크 건너뛰기")
    parser.add_argument("--skip-e2e", action="store_true", help="E2E 테스트 건너뛰기")
    parser.add_argument("--skip-performance", action="store_true", help="성능 테스트 건너뛰기")
    parser.add_argument("--skip-integration", action="store_true", help="통합 테스트 건너뛰기")
    parser.add_argument("--quick", action="store_true", help="빠른 테스트 (성능 테스트 제외)")
    
    args = parser.parse_args()
    
    print("🚀 RAG 시스템 통합 테스트 시작")
    print(f"⏰ 시작 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # 서비스 헬스체크
    if not args.skip_health:
        results["서비스 헬스체크"] = check_services_health()
        if not results["서비스 헬스체크"]:
            print("\n💀 서비스가 정상적으로 실행되지 않았습니다.")
            print("🔧 docker-compose up -d 명령으로 서비스를 시작해주세요.")
            return False
    
    # 통합 테스트 실행
    if not args.skip_integration:
        results["통합 테스트"] = run_integration_tests()
    
    # E2E 테스트 실행
    if not args.skip_e2e:
        results["E2E 테스트"] = run_e2e_tests()
    
    # 성능 테스트 실행 (quick 모드가 아닐 때만)
    if not args.skip_performance and not args.quick:
        results["성능 테스트"] = run_performance_tests()
    
    # 결과 리포트 생성
    all_passed = generate_test_report(results)
    
    print(f"\n⏰ 완료 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 종료 코드 설정
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    # 필요한 패키지 설치 확인
    try:
        import requests
    except ImportError:
        print("⚠️ requests 패키지가 필요합니다: pip install requests")
        sys.exit(1)
    
    main() 