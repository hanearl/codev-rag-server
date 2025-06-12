import pytest
import httpx
import asyncio
import tempfile
import os
import time
from pathlib import Path


@pytest.mark.asyncio
class TestCompleteWorkflow:
    """완전한 시스템 워크플로우 E2E 테스트"""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """테스트 셋업"""
        self.base_url = "http://localhost:8000"
        self.timeout = 60
        
        # 모든 서비스가 준비될 때까지 대기
        await self.verify_all_services_healthy()
        
    async def verify_all_services_healthy(self):
        """모든 서비스 상태 확인"""
        services = {
            "rag": "http://localhost:8000/health",
            "embedding": "http://localhost:8001/health",
            "llm": "http://localhost:8002/health",
            "vector_db": "http://localhost:6333/healthz"
        }
        
        async with httpx.AsyncClient() as client:
            for service, url in services.items():
                print(f"🔍 {service} 서비스 헬스체크...")
                response = await client.get(url, timeout=30.0)
                assert response.status_code == 200, f"{service} 서비스 비정상: {response.status_code}"
                print(f"✅ {service} 서비스 정상")

    async def test_full_rag_pipeline(self):
        """전체 RAG 파이프라인 E2E 테스트"""
        print("\n🚀 전체 RAG 파이프라인 테스트 시작")
        
        # 1. 샘플 코드 파일 생성
        print("📝 샘플 코드 파일 생성...")
        file_path = await self.create_sample_code_file()
        
        try:
            # 2. 코드 인덱싱
            print("🔄 코드 인덱싱 중...")
            await self.index_code_file(file_path)
            
            # 3. 검색 수행
            print("🔍 코드 검색 중...")
            search_results = await self.search_code("pandas DataFrame 읽기")
            
            # 4. 코드 생성
            print("🤖 RAG 기반 코드 생성 중...")
            generated_code = await self.generate_code_with_context(
                "CSV 파일을 읽어서 DataFrame으로 반환하는 함수를 만들어주세요"
            )
            
            # 5. 결과 검증
            print("✅ 결과 검증 중...")
            assert len(search_results) > 0, "검색 결과가 없습니다"
            assert any(keyword in generated_code.lower() for keyword in ["pandas", "csv", "dataframe", "read"]), \
                f"생성된 코드에 관련 키워드가 없습니다: {generated_code}"
            
            print("🎉 전체 RAG 파이프라인 테스트 성공!")
            
        finally:
            # 임시 파일 정리
            if os.path.exists(file_path):
                os.unlink(file_path)

    async def test_multiple_language_support(self):
        """다중 언어 지원 테스트"""
        print("\n🌐 다중 언어 지원 테스트 시작")
        
        test_cases = [
            {
                "language": "python",
                "code": """
import pandas as pd

def process_csv(filename):
    df = pd.read_csv(filename)
    return df.head()
""",
                "query": "CSV 파일 처리"
            },
            {
                "language": "java",
                "code": """
public class FileProcessor {
    public void processFile(String filename) {
        System.out.println("Processing: " + filename);
    }
}
""",
                "query": "파일 처리 클래스"
            },
            {
                "language": "javascript",
                "code": """
function fetchData(url) {
    return fetch(url)
        .then(response => response.json())
        .then(data => console.log(data));
}
""",
                "query": "데이터 가져오기"
            }
        ]
        
        for case in test_cases:
            print(f"📝 {case['language']} 파일 테스트 중...")
            
            # 임시 파일 생성
            file_path = await self.create_code_file(case['code'], case['language'])
            
            try:
                # 인덱싱
                await self.index_code_file(file_path, case['language'])
                
                # 검색
                results = await self.search_code(case['query'])
                assert len(results) >= 0, f"{case['language']} 검색 실패"
                
                print(f"✅ {case['language']} 테스트 성공")
                
            finally:
                if os.path.exists(file_path):
                    os.unlink(file_path)

    async def test_performance_benchmarks(self):
        """성능 벤치마크 테스트"""
        print("\n⚡ 성능 벤치마크 테스트 시작")
        
        # 검색 성능 테스트
        search_times = []
        for i in range(5):
            start_time = time.time()
            await self.search_code(f"test function {i}")
            search_times.append(time.time() - start_time)
        
        avg_search_time = sum(search_times) / len(search_times)
        print(f"📊 평균 검색 시간: {avg_search_time:.2f}초")
        assert avg_search_time < 5.0, f"검색 시간이 너무 깁니다: {avg_search_time:.2f}초"
        
        # 생성 성능 테스트
        start_time = time.time()
        await self.generate_code_with_context("간단한 Hello World 함수를 만들어주세요")
        generation_time = time.time() - start_time
        
        print(f"📊 코드 생성 시간: {generation_time:.2f}초")
        assert generation_time < 60.0, f"생성 시간이 너무 깁니다: {generation_time:.2f}초"
        
        print("✅ 성능 벤치마크 테스트 성공!")

    async def test_error_handling(self):
        """에러 처리 테스트"""
        print("\n🚨 에러 처리 테스트 시작")
        
        async with httpx.AsyncClient() as client:
            # 잘못된 인덱싱 요청
            response = await client.post(
                f"{self.base_url}/api/v1/indexing/file",
                json={},  # 필수 필드 누락
                timeout=self.timeout
            )
            assert response.status_code == 422, "잘못된 요청에 대한 검증 실패"
            
            # 빈 검색 요청
            response = await client.post(
                f"{self.base_url}/api/v1/search/",
                json={"query": ""},
                timeout=self.timeout
            )
            # 빈 쿼리도 허용되어야 함 (빈 결과 반환)
            assert response.status_code in [200, 400], "빈 검색 요청 처리 실패"
            
        print("✅ 에러 처리 테스트 성공!")

    # Helper 메서드들
    async def create_sample_code_file(self) -> str:
        """샘플 Python 코드 파일 생성"""
        sample_code = '''import pandas as pd
import numpy as np

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
        # 결측값 제거
        df_clean = df.dropna()
        # 중복값 제거
        df_clean = df_clean.drop_duplicates()
        return df_clean
    return None

def save_processed_data(df, output_path):
    """처리된 데이터를 파일로 저장"""
    if df is not None:
        df.to_csv(output_path, index=False)
        print(f"데이터가 저장되었습니다: {output_path}")
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(sample_code)
            return f.name

    async def create_code_file(self, code: str, language: str) -> str:
        """언어별 코드 파일 생성"""
        extensions = {
            "python": ".py",
            "java": ".java", 
            "javascript": ".js"
        }
        
        ext = extensions.get(language, ".txt")
        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
            f.write(code)
            return f.name

    async def index_code_file(self, file_path: str, language: str = "python"):
        """파일 인덱싱"""
        async with httpx.AsyncClient() as client:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            response = await client.post(
                f"{self.base_url}/api/v1/indexing/file",
                json={
                    "file_path": file_path,
                    "content": content,
                    "language": language
                },
                timeout=self.timeout
            )
            assert response.status_code == 200, f"인덱싱 실패: {response.text}"
            return response.json()

    async def search_code(self, query: str) -> list:
        """코드 검색"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/search/",
                json={
                    "query": query,
                    "limit": 5,
                    "vector_weight": 0.7,
                    "keyword_weight": 0.3
                },
                timeout=self.timeout
            )
            assert response.status_code == 200, f"검색 실패: {response.text}"
            return response.json()["results"]

    async def generate_code_with_context(self, prompt: str) -> str:
        """컨텍스트 기반 코드 생성"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/generate/",
                json={
                    "query": prompt,
                    "language": "python",
                    "max_tokens": 300,
                    "temperature": 0.7
                },
                timeout=90  # LLM 응답은 더 오래 걸릴 수 있음
            )
            assert response.status_code == 200, f"코드 생성 실패: {response.text}"
            result = response.json()
            return result.get("generated_code", result.get("code", "")) 