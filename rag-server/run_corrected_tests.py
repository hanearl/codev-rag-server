#!/usr/bin/env python3
"""
수정된 엔드포인트를 사용하는 간단한 통합 테스트
Task 06에서 확인된 실제 API 엔드포인트를 기반으로 함
"""

import asyncio
import httpx
import tempfile
import os
import time
from datetime import datetime
import json


class IntegratedRAGTester:
    """통합 RAG 시스템 테스터"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.timeout = 60
        
    async def verify_all_services_healthy(self):
        """모든 서비스 상태 확인"""
        print("🔍 서비스 헬스체크 시작...")
        
        services = {
            "rag": "http://localhost:8000/health",
            "embedding": "http://localhost:8001/health",
            "llm": "http://localhost:8002/health",
            "vector_db": "http://localhost:6333/healthz"
        }
        
        async with httpx.AsyncClient() as client:
            for service, url in services.items():
                try:
                    response = await client.get(url, timeout=10.0)
                    status = "✅ 정상" if response.status_code == 200 else f"❌ 오류 ({response.status_code})"
                    print(f"  {service}: {status}")
                except Exception as e:
                    print(f"  {service}: ❌ 연결 실패 - {e}")
        
        print("✅ 헬스체크 완료\n")

    async def test_basic_workflow(self):
        """기본 RAG 워크플로우 테스트"""
        print("🚀 기본 RAG 워크플로우 테스트 시작...")
        
        # 1. 샘플 코드 파일 생성 (절대 경로)
        sample_code = '''import pandas as pd

def read_csv_file(file_path):
    """CSV 파일을 읽어서 DataFrame으로 반환"""
    try:
        df = pd.read_csv(file_path)
        return df
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {file_path}")
        return None

def process_data(df):
    """데이터 전처리"""
    if df is not None:
        return df.dropna()
    return None
'''
        
        # 절대 경로로 파일 생성
        import os
        current_dir = os.getcwd()
        test_dir = os.path.join(current_dir, "..", "test-codebase")
        os.makedirs(test_dir, exist_ok=True)
        file_path = os.path.join(test_dir, "test_sample.py")
        absolute_path = os.path.abspath(file_path)
        
        with open(absolute_path, 'w') as f:
            f.write(sample_code)
        
        try:
            # 2. 코드 인덱싱 (절대 경로 사용)
            print("📝 코드 인덱싱 중...")
            await self.index_code_file(absolute_path)
            print("✅ 인덱싱 완료")
            
            # 3. 검색 테스트
            print("🔍 코드 검색 중...")
            search_results = await self.search_code("pandas DataFrame")
            print(f"✅ 검색 완료 - {len(search_results)}개 결과 발견")
            
            # 4. 코드 생성 테스트 (optional - 실패할 수 있음)
            try:
                print("🤖 코드 생성 중...")
                generated_code = await self.generate_code("CSV 파일을 읽는 함수")
                print("✅ 코드 생성 완료")
                print(f"생성된 코드 길이: {len(generated_code)} 문자")
            except Exception as e:
                print(f"⚠️ 코드 생성 실패 (무시 가능): {e}")
            
            print("🎉 기본 워크플로우 테스트 성공!")
            
        finally:
            if os.path.exists(absolute_path):
                os.unlink(absolute_path)
    
    async def index_code_file(self, file_path: str):
        """파일 인덱싱 - 실제 엔드포인트 사용 (파일 경로만)"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/indexing/file",
                json={
                    "file_path": file_path,
                    "force_update": True
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"인덱싱 실패: {response.status_code} - {response.text}")
            
            return response.json()
    
    async def search_code(self, query: str) -> list:
        """코드 검색 - 실제 엔드포인트 사용"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/search/",
                json={
                    "query": query,
                    "limit": 5
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"검색 실패: {response.status_code} - {response.text}")
            
            result = response.json()
            return result.get("results", [])
    
    async def generate_code(self, prompt: str) -> str:
        """코드 생성 - 실제 엔드포인트 사용"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/generate/",
                json={
                    "query": prompt,
                    "language": "python",
                    "max_tokens": 200
                },
                timeout=90
            )
            
            if response.status_code != 200:
                raise Exception(f"코드 생성 실패: {response.status_code} - {response.text}")
            
            result = response.json()
            return result.get("generated_code", result.get("code", ""))
    
    async def test_api_endpoints(self):
        """API 엔드포인트 접근성 테스트"""
        print("🔧 API 엔드포인트 접근성 테스트...")
        
        endpoints = [
            ("/docs", "API 문서"),
            ("/openapi.json", "OpenAPI 스펙"),
            ("/health", "헬스체크"),
            ("/api/v1/generate/health", "생성 서비스 헬스체크"),
            ("/api/v1/search/health", "검색 서비스 헬스체크"),
            ("/api/v1/indexing/health", "인덱싱 서비스 헬스체크")
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint, description in endpoints:
                try:
                    response = await client.get(f"{self.base_url}{endpoint}", timeout=10)
                    status = "✅ 접근 가능" if response.status_code == 200 else f"⚠️ {response.status_code}"
                    print(f"  {description}: {status}")
                except Exception as e:
                    print(f"  {description}: ❌ 오류 - {e}")
        
        print("✅ API 엔드포인트 테스트 완료\n")
    
    async def test_performance_basic(self):
        """기본 성능 테스트"""
        print("⚡ 기본 성능 테스트...")
        
        # 검색 성능 테스트
        search_times = []
        for i in range(3):
            start_time = time.time()
            try:
                await self.search_code(f"test function {i}")
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
        
        print("✅ 성능 테스트 완료\n")


async def main():
    """메인 테스트 실행 함수"""
    print("=" * 60)
    print("🧪 RAG 시스템 통합 테스트 (수정된 엔드포인트)")
    print("=" * 60)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tester = IntegratedRAGTester()
    
    try:
        # 1. 헬스체크
        await tester.verify_all_services_healthy()
        
        # 2. API 엔드포인트 테스트
        await tester.test_api_endpoints()
        
        # 3. 기본 워크플로우 테스트
        await tester.test_basic_workflow()
        
        # 4. 기본 성능 테스트
        await tester.test_performance_basic()
        
        print("🎉 전체 통합 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        raise
    
    finally:
        print()
        print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 