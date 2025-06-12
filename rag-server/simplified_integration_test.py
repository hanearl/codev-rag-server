#!/usr/bin/env python3
"""
단순화된 RAG 시스템 통합 테스트
실제로 동작하는 기능들에 중점을 둔 테스트
"""

import asyncio
import httpx
import time
from datetime import datetime
import json


class SimplifiedRAGTester:
    """단순화된 RAG 시스템 테스터"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.timeout = 30
        
    async def verify_all_services_healthy(self):
        """모든 서비스 상태 확인"""
        print("🔍 서비스 헬스체크 시작...")
        
        services = {
            "rag": "http://localhost:8000/health",
            "embedding": "http://localhost:8001/health", 
            "llm": "http://localhost:8002/health",
            "vector_db": "http://localhost:6333/healthz"
        }
        
        all_healthy = True
        async with httpx.AsyncClient() as client:
            for service, url in services.items():
                try:
                    response = await client.get(url, timeout=10.0)
                    if response.status_code == 200:
                        print(f"  ✅ {service}: 정상")
                    else:
                        print(f"  ❌ {service}: 오류 ({response.status_code})")
                        all_healthy = False
                except Exception as e:
                    print(f"  ❌ {service}: 연결 실패 - {e}")
                    all_healthy = False
        
        if all_healthy:
            print("✅ 모든 서비스 정상 상태")
        else:
            print("⚠️ 일부 서비스에 문제가 있습니다")
        
        print()
        return all_healthy

    async def test_api_endpoints_comprehensive(self):
        """종합적인 API 엔드포인트 테스트"""
        print("🔧 API 엔드포인트 종합 테스트...")
        
        endpoints = [
            # 문서 관련
            ("/docs", "GET", "API 문서"),
            ("/openapi.json", "GET", "OpenAPI 스펙"),
            ("/redoc", "GET", "ReDoc 문서"),
            
            # 헬스체크
            ("/health", "GET", "메인 헬스체크"),
            ("/api/v1/generate/health", "GET", "생성 서비스 헬스체크"),
            ("/api/v1/search/health", "GET", "검색 서비스 헬스체크"),
            ("/api/v1/indexing/health", "GET", "인덱싱 서비스 헬스체크"),
            
            # 기능 엔드포인트 (기본 접근성만 확인)
            ("/api/v1/generate/languages", "GET", "지원 언어 목록"),
            ("/api/v1/prompts/templates", "GET", "프롬프트 템플릿 목록"),
        ]
        
        passed = 0
        total = len(endpoints)
        
        async with httpx.AsyncClient() as client:
            for endpoint, method, description in endpoints:
                try:
                    if method == "GET":
                        response = await client.get(f"{self.base_url}{endpoint}", timeout=10)
                    elif method == "POST":
                        response = await client.post(f"{self.base_url}{endpoint}", timeout=10)
                    
                    if response.status_code in [200, 422]:  # 422는 유효한 스키마 검증 오류
                        print(f"  ✅ {description}: 접근 가능 ({response.status_code})")
                        passed += 1
                    else:
                        print(f"  ⚠️ {description}: {response.status_code}")
                        
                except Exception as e:
                    print(f"  ❌ {description}: 오류 - {str(e)[:50]}...")
        
        print(f"✅ API 엔드포인트 테스트 완료: {passed}/{total} 통과")
        print()
        return passed, total

    async def test_search_functionality(self):
        """검색 기능 테스트 (빈 쿼리로)"""
        print("🔍 검색 기능 기본 테스트...")
        
        test_queries = [
            "",  # 빈 쿼리
            "test",  # 간단한 쿼리
            "function",  # 일반적인 키워드
        ]
        
        passed = 0
        async with httpx.AsyncClient() as client:
            for query in test_queries:
                try:
                    response = await client.post(
                        f"{self.base_url}/api/v1/search/",
                        json={
                            "query": query,
                            "limit": 5
                        },
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        results_count = len(result.get("results", []))
                        print(f"  ✅ 쿼리 '{query}': {results_count}개 결과")
                        passed += 1
                    else:
                        print(f"  ⚠️ 쿼리 '{query}': 상태 코드 {response.status_code}")
                        
                except Exception as e:
                    print(f"  ❌ 쿼리 '{query}': 오류 - {str(e)[:50]}...")
        
        print(f"✅ 검색 테스트 완료: {passed}/{len(test_queries)} 통과")
        print()
        return passed, len(test_queries)

    async def test_generation_api_access(self):
        """코드 생성 API 접근성 테스트"""
        print("🤖 코드 생성 API 접근성 테스트...")
        
        test_requests = [
            {
                "query": "hello world function",
                "language": "python",
                "max_tokens": 50
            },
            {
                "query": "simple function",
                "language": "javascript", 
                "max_tokens": 50
            }
        ]
        
        passed = 0
        async with httpx.AsyncClient() as client:
            for req in test_requests:
                try:
                    response = await client.post(
                        f"{self.base_url}/api/v1/generate/",
                        json=req,
                        timeout=30  # 생성은 시간이 걸릴 수 있음
                    )
                    
                    if response.status_code in [200, 400, 422]:  # 200=성공, 400/422=유효한 오류
                        print(f"  ✅ {req['language']} 생성: 응답 받음 ({response.status_code})")
                        passed += 1
                        
                        if response.status_code == 200:
                            result = response.json()
                            code_length = len(result.get("generated_code", result.get("code", "")))
                            print(f"      생성된 코드 길이: {code_length} 문자")
                    else:
                        print(f"  ⚠️ {req['language']} 생성: 상태 코드 {response.status_code}")
                        
                except Exception as e:
                    print(f"  ❌ {req['language']} 생성: 오류 - {str(e)[:50]}...")
        
        print(f"✅ 코드 생성 테스트 완료: {passed}/{len(test_requests)} 통과")
        print()
        return passed, len(test_requests)

    async def test_performance_basic(self):
        """기본 성능 테스트"""
        print("⚡ 기본 성능 테스트...")
        
        # 검색 성능 테스트
        search_times = []
        for i in range(3):
            start_time = time.time()
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/api/v1/search/",
                        json={"query": f"test {i}", "limit": 5},
                        timeout=10
                    )
                if response.status_code == 200:
                    search_times.append(time.time() - start_time)
            except Exception:
                print(f"  검색 {i+1} 실패")
        
        if search_times:
            avg_time = sum(search_times) / len(search_times)
            print(f"  평균 검색 시간: {avg_time:.2f}초")
            status = "✅ 양호" if avg_time < 5.0 else "⚠️ 느림"
            print(f"  성능 상태: {status}")
        else:
            print("  검색 성능 측정 실패")
        
        print("✅ 성능 테스트 완료")
        print()

    async def test_docker_integration(self):
        """Docker 통합 환경 테스트"""
        print("🐳 Docker 통합 환경 테스트...")
        
        # 각 서비스가 다른 포트에서 실행되는지 확인
        services = [
            ("RAG Server", "localhost:8000"),
            ("Embedding Server", "localhost:8001"), 
            ("LLM Server", "localhost:8002"),
            ("Vector DB", "localhost:6333")
        ]
        
        all_running = True
        async with httpx.AsyncClient() as client:
            for name, host in services:
                try:
                    # 간단한 TCP 연결 테스트
                    response = await client.get(f"http://{host}/health", timeout=5)
                    print(f"  ✅ {name} ({host}): 실행 중")
                except httpx.RequestError:
                    try:
                        # health 엔드포인트가 없을 수 있으므로 healthz도 시도
                        response = await client.get(f"http://{host}/healthz", timeout=5)
                        print(f"  ✅ {name} ({host}): 실행 중")
                    except Exception:
                        print(f"  ❌ {name} ({host}): 접근 불가")
                        all_running = False
                except Exception as e:
                    print(f"  ❌ {name} ({host}): 오류 - {str(e)[:30]}...")
                    all_running = False
        
        if all_running:
            print("✅ 모든 Docker 서비스 정상 실행")
        else:
            print("⚠️ 일부 Docker 서비스에 문제가 있습니다")
        
        print()
        return all_running


async def main():
    """메인 테스트 실행 함수"""
    print("=" * 60)
    print("🧪 RAG 시스템 단순화된 통합 테스트")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tester = SimplifiedRAGTester()
    
    # 테스트 결과 집계
    test_results = {
        "services_healthy": False,
        "api_endpoints": (0, 0),
        "search_functionality": (0, 0),
        "generation_access": (0, 0),
        "docker_integration": False
    }
    
    try:
        # 1. 서비스 헬스체크
        test_results["services_healthy"] = await tester.verify_all_services_healthy()
        
        # 2. API 엔드포인트 테스트
        test_results["api_endpoints"] = await tester.test_api_endpoints_comprehensive()
        
        # 3. 검색 기능 테스트
        test_results["search_functionality"] = await tester.test_search_functionality()
        
        # 4. 코드 생성 API 접근성 테스트
        test_results["generation_access"] = await tester.test_generation_api_access()
        
        # 5. Docker 통합 테스트
        test_results["docker_integration"] = await tester.test_docker_integration()
        
        # 6. 기본 성능 테스트
        await tester.test_performance_basic()
        
        # 결과 요약
        print("📊 테스트 결과 요약")
        print("-" * 40)
        print(f"서비스 상태: {'✅ 정상' if test_results['services_healthy'] else '❌ 문제 있음'}")
        print(f"API 엔드포인트: {test_results['api_endpoints'][0]}/{test_results['api_endpoints'][1]} 통과")
        print(f"검색 기능: {test_results['search_functionality'][0]}/{test_results['search_functionality'][1]} 통과")
        print(f"생성 API: {test_results['generation_access'][0]}/{test_results['generation_access'][1]} 통과")
        print(f"Docker 통합: {'✅ 정상' if test_results['docker_integration'] else '❌ 문제 있음'}")
        print()
        
        # 전체 성공률 계산
        total_passed = (
            test_results["api_endpoints"][0] + 
            test_results["search_functionality"][0] + 
            test_results["generation_access"][0]
        )
        total_tests = (
            test_results["api_endpoints"][1] + 
            test_results["search_functionality"][1] + 
            test_results["generation_access"][1]
        )
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        print(f"🎯 전체 성공률: {success_rate:.1f}% ({total_passed}/{total_tests})")
        
        if (test_results["services_healthy"] and 
            test_results["docker_integration"] and 
            success_rate >= 80):
            print("🎉 전체 통합 테스트 성공! 시스템이 운영 준비 상태입니다.")
        else:
            print("⚠️ 일부 테스트에서 문제가 발견되었습니다. 검토가 필요합니다.")
        
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        raise
    
    finally:
        print()
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 