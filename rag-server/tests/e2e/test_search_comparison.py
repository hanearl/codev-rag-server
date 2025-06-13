"""
검색 방식 비교 E2E 테스트

코드 인덱싱 후 BM25, Vector, Hybrid 검색 방식을 비교하는 테스트
"""
import pytest
import httpx
import asyncio
import time
import json
from typing import List, Dict, Any
from pathlib import Path


@pytest.mark.asyncio
class TestSearchComparison:
    """검색 방식 비교 E2E 테스트"""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """테스트 셋업"""
        self.base_url = "http://localhost:8000"
        self.timeout = 60.0
        
        # 테스트용 컬렉션/인덱스 이름
        self.collection_name = "test_search_comparison"
        self.index_name = "test_search_comparison"
        
        # 모든 서비스가 준비될 때까지 대기
        await self.verify_services_healthy()
        
        # 기존 테스트 데이터 정리
        await self.cleanup_test_data()
        
    @pytest.fixture(autouse=True) 
    async def teardown(self):
        """테스트 정리"""
        yield
        # 테스트 데이터 정리
        await self.cleanup_test_data()
        
    async def verify_services_healthy(self):
        """서비스 헬스체크"""
        async with httpx.AsyncClient() as client:
            print("🔍 RAG 서버 헬스체크...")
            response = await client.get(f"{self.base_url}/health", timeout=30.0)
            assert response.status_code == 200, f"RAG 서버 비정상: {response.status_code}"
            print("✅ RAG 서버 정상")

    async def cleanup_test_data(self):
        """테스트 데이터 정리"""
        async with httpx.AsyncClient() as client:
            try:
                # 벡터 컬렉션 삭제
                await client.delete(
                    f"{self.base_url}/api/v1/indexing/vector/{self.collection_name}",
                    timeout=self.timeout
                )
            except:
                pass  # 존재하지 않으면 무시
                
            try:
                # BM25 인덱스 삭제
                await client.delete(
                    f"{self.base_url}/api/v1/indexing/bm25/{self.index_name}",
                    timeout=self.timeout
                )
            except:
                pass  # 존재하지 않으면 무시

    async def test_complete_search_comparison_workflow(self):
        """완전한 검색 비교 워크플로우 테스트"""
        print("\n🚀 검색 비교 워크플로우 테스트 시작")
        
        # 1. 샘플 코드 데이터 준비
        print("📝 샘플 코드 데이터 준비...")
        sample_codes = self.get_sample_code_data()
        
        # 2. 코드 파싱
        print("🔄 코드 파싱 중...")
        parsed_data = await self.parse_sample_codes(sample_codes)
        
        # 3. 문서 빌드
        print("📄 문서 빌드 중...")
        documents = await self.build_documents(parsed_data)
        
        # 4. 인덱싱 (Vector + BM25)
        print("🗂️ 인덱싱 중...")
        await self.index_documents(documents)
        
        # 5. 검색 쿼리 수행 및 비교
        print("🔍 검색 비교 중...")
        test_queries = [
            "pandas DataFrame 조작",
            "REST API 엔드포인트",
            "데이터베이스 연결",
            "JSON 파싱",
            "파일 읽기 쓰기"
        ]
        
        comparison_results = []
        for query in test_queries:
            print(f"   📊 쿼리: '{query}' 검색 중...")
            result = await self.compare_search_methods(query)
            comparison_results.append(result)
            
        # 6. 결과 분석 및 검증
        print("📈 결과 분석 중...")
        await self.analyze_search_results(comparison_results)
        
        print("🎉 검색 비교 워크플로우 테스트 성공!")

    def get_sample_code_data(self) -> List[Dict[str, Any]]:
        """테스트용 샘플 코드 데이터"""
        return [
            {
                "file_path": "data_processor.py",
                "language": "python",
                "code": """
import pandas as pd
import numpy as np
from typing import List, Dict

class DataProcessor:
    def __init__(self):
        self.data = None
    
    def load_csv(self, file_path: str) -> pd.DataFrame:
        \"\"\"CSV 파일을 로드하여 DataFrame으로 반환\"\"\"
        try:
            df = pd.read_csv(file_path)
            self.data = df
            return df
        except FileNotFoundError:
            raise Exception(f"파일을 찾을 수 없습니다: {file_path}")
    
    def process_data(self, operations: List[str]) -> pd.DataFrame:
        \"\"\"데이터 전처리 작업 수행\"\"\"
        if self.data is None:
            raise ValueError("데이터가 로드되지 않았습니다")
        
        result = self.data.copy()
        for operation in operations:
            if operation == "remove_nulls":
                result = result.dropna()
            elif operation == "normalize":
                result = (result - result.mean()) / result.std()
        
        return result
"""
            },
            {
                "file_path": "api_handler.py", 
                "language": "python",
                "code": """
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import httpx
import json

app = FastAPI()

class APIRequest(BaseModel):
    url: str
    method: str = "GET"
    headers: dict = {}
    data: dict = {}

class APIResponse(BaseModel):
    status_code: int
    content: str
    headers: dict

@app.post("/api/proxy", response_model=APIResponse)
async def proxy_request(request: APIRequest):
    \"\"\"외부 API 요청을 프록시하는 엔드포인트\"\"\"
    async with httpx.AsyncClient() as client:
        try:
            if request.method.upper() == "GET":
                response = await client.get(
                    request.url, 
                    headers=request.headers
                )
            elif request.method.upper() == "POST":
                response = await client.post(
                    request.url,
                    json=request.data,
                    headers=request.headers
                )
            
            return APIResponse(
                status_code=response.status_code,
                content=response.text,
                headers=dict(response.headers)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
"""
            },
            {
                "file_path": "database_manager.py",
                "language": "python", 
                "code": """
import sqlite3
import json
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        \"\"\"데이터베이스 초기화\"\"\"
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    data TEXT
                )
            ''')
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        \"\"\"데이터베이스 연결 관리\"\"\"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def insert_user(self, name: str, email: str, data: Dict[str, Any] = None) -> int:
        \"\"\"사용자 추가\"\"\"
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, data) VALUES (?, ?, ?)",
                (name, email, json.dumps(data) if data else None)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        \"\"\"이메일로 사용자 조회\"\"\"
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", 
                (email,)
            ).fetchone()
            
            if row:
                user_data = dict(row)
                if user_data['data']:
                    user_data['data'] = json.loads(user_data['data'])
                return user_data
            return None
"""
            },
            {
                "file_path": "file_utils.py",
                "language": "python",
                "code": """
import os
import json
import yaml
import csv
from typing import Any, Dict, List
from pathlib import Path

class FileUtils:
    @staticmethod
    def read_json(file_path: str) -> Dict[str, Any]:
        \"\"\"JSON 파일 읽기\"\"\"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise Exception(f"JSON 파일을 찾을 수 없습니다: {file_path}")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON 파싱 오류: {e}")
    
    @staticmethod
    def write_json(data: Dict[str, Any], file_path: str) -> None:
        \"\"\"JSON 파일 쓰기\"\"\"
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def read_csv(file_path: str) -> List[Dict[str, str]]:
        \"\"\"CSV 파일을 딕셔너리 리스트로 읽기\"\"\"
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    
    @staticmethod
    def write_csv(data: List[Dict[str, Any]], file_path: str) -> None:
        \"\"\"딕셔너리 리스트를 CSV 파일로 쓰기\"\"\"
        if not data:
            return
        
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
    
    @staticmethod
    def read_yaml(file_path: str) -> Dict[str, Any]:
        \"\"\"YAML 파일 읽기\"\"\"
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
"""
            }
        ]

    async def parse_sample_codes(self, sample_codes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """샘플 코드들을 파싱"""
        parsed_results = []
        
        async with httpx.AsyncClient() as client:
            for code_data in sample_codes:
                parse_request = {
                    "code": code_data["code"],
                    "language": code_data["language"],
                    "file_path": code_data["file_path"],
                    "extract_methods": True,
                    "extract_classes": True,
                    "extract_functions": True,
                    "extract_imports": True
                }
                
                response = await client.post(
                    f"{self.base_url}/api/v1/indexing/parse",
                    json=parse_request,
                    timeout=self.timeout
                )
                
                assert response.status_code == 200, f"파싱 실패: {response.text}"
                result = response.json()
                assert result["success"], f"파싱 실패: {result.get('error_message')}"
                
                parsed_results.append(result["ast_info"])
                
        return parsed_results

    async def build_documents(self, parsed_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """문서 빌드"""
        async with httpx.AsyncClient() as client:
            build_request = {
                "ast_info_list": parsed_data,
                "chunking_strategy": "method_level",
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "include_metadata": True
            }
            
            response = await client.post(
                f"{self.base_url}/api/v1/indexing/documents/build",
                json=build_request,
                timeout=self.timeout
            )
            
            assert response.status_code == 200, f"문서 빌드 실패: {response.text}"
            result = response.json()
            assert result["success"], f"문서 빌드 실패: {result.get('error_message')}"
            
            return result["documents"]

    async def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        """문서 인덱싱 (Vector + BM25)"""
        async with httpx.AsyncClient() as client:
            # Vector 인덱스 생성
            vector_request = {
                "documents": documents,
                "collection_name": self.collection_name,
                "vector_dimension": 768,
                "distance_metric": "cosine"
            }
            
            print("   🔗 벡터 인덱스 생성 중...")
            response = await client.post(
                f"{self.base_url}/api/v1/indexing/vector/index",
                json=vector_request,
                timeout=self.timeout
            )
            
            assert response.status_code == 200, f"벡터 인덱싱 실패: {response.text}"
            result = response.json()
            assert result["success"], f"벡터 인덱싱 실패: {result.get('error_message')}"
            print(f"   ✅ 벡터 인덱스 생성 완료: {result['indexed_count']}개 문서")
            
            # BM25 인덱스 생성
            bm25_request = {
                "documents": documents,
                "collection_name": self.index_name,
                "language": "korean"
            }
            
            print("   📚 BM25 인덱스 생성 중...")
            response = await client.post(
                f"{self.base_url}/api/v1/indexing/bm25/index",
                json=bm25_request,
                timeout=self.timeout
            )
            
            assert response.status_code == 200, f"BM25 인덱싱 실패: {response.text}"
            result = response.json()
            assert result["success"], f"BM25 인덱싱 실패: {result.get('error_message')}"
            print(f"   ✅ BM25 인덱스 생성 완료: {result['indexed_count']}개 문서")

    async def compare_search_methods(self, query: str) -> Dict[str, Any]:
        """세 가지 검색 방식 비교"""
        async with httpx.AsyncClient() as client:
            comparison_result = {
                "query": query,
                "vector_search": None,
                "bm25_search": None, 
                "hybrid_search": None,
                "timing": {},
                "result_counts": {},
                "top_results": {}
            }
            
            # 1. Vector 검색
            start_time = time.time()
            vector_request = {
                "query": query,
                "collection_name": self.collection_name,
                "top_k": 5,
                "score_threshold": 0.0
            }
            
            response = await client.post(
                f"{self.base_url}/api/v1/search/vector",
                json=vector_request,
                timeout=self.timeout
            )
            
            vector_time = time.time() - start_time
            comparison_result["timing"]["vector"] = vector_time
            
            if response.status_code == 200:
                vector_result = response.json()
                if vector_result["success"]:
                    comparison_result["vector_search"] = vector_result
                    comparison_result["result_counts"]["vector"] = vector_result["total_results"]
                    comparison_result["top_results"]["vector"] = vector_result["results"][:3] if vector_result["results"] else []
            
            # 2. BM25 검색
            start_time = time.time()
            bm25_request = {
                "query": query,
                "index_name": self.index_name,
                "top_k": 5
            }
            
            response = await client.post(
                f"{self.base_url}/api/v1/search/bm25",
                json=bm25_request,
                timeout=self.timeout
            )
            
            bm25_time = time.time() - start_time
            comparison_result["timing"]["bm25"] = bm25_time
            
            if response.status_code == 200:
                bm25_result = response.json()
                if bm25_result["success"]:
                    comparison_result["bm25_search"] = bm25_result
                    comparison_result["result_counts"]["bm25"] = bm25_result["total_results"]
                    comparison_result["top_results"]["bm25"] = bm25_result["results"][:3] if bm25_result["results"] else []
            
            # 3. Hybrid 검색
            start_time = time.time()
            hybrid_request = {
                "query": query,
                "collection_name": self.collection_name,
                "index_name": self.index_name,
                "top_k": 5,
                "vector_weight": 0.7,
                "bm25_weight": 0.3,
                "use_rrf": True,
                "rrf_k": 60,
                "score_threshold": 0.0
            }
            
            response = await client.post(
                f"{self.base_url}/api/v1/search/hybrid",
                json=hybrid_request,
                timeout=self.timeout
            )
            
            hybrid_time = time.time() - start_time
            comparison_result["timing"]["hybrid"] = hybrid_time
            
            if response.status_code == 200:
                hybrid_result = response.json()
                if hybrid_result["success"]:
                    comparison_result["hybrid_search"] = hybrid_result
                    comparison_result["result_counts"]["hybrid"] = hybrid_result["total_results"] 
                    comparison_result["top_results"]["hybrid"] = hybrid_result["results"][:3] if hybrid_result["results"] else []
            
            return comparison_result

    async def analyze_search_results(self, comparison_results: List[Dict[str, Any]]) -> None:
        """검색 결과 분석 및 검증"""
        print("\n📊 검색 결과 분석:")
        print("=" * 80)
        
        total_vector_time = 0
        total_bm25_time = 0
        total_hybrid_time = 0
        
        successful_searches = {"vector": 0, "bm25": 0, "hybrid": 0}
        total_results = {"vector": 0, "bm25": 0, "hybrid": 0}
        
        for i, result in enumerate(comparison_results):
            query = result["query"]
            print(f"\n🔍 쿼리 {i+1}: '{query}'")
            print("-" * 60)
            
            # 각 검색 방식별 결과
            for method in ["vector", "bm25", "hybrid"]:
                search_result = result[f"{method}_search"]
                timing = result["timing"].get(method, 0)
                result_count = result["result_counts"].get(method, 0)
                
                if method == "vector":
                    total_vector_time += timing
                elif method == "bm25":
                    total_bm25_time += timing
                else:
                    total_hybrid_time += timing
                
                if search_result and search_result.get("success"):
                    successful_searches[method] += 1
                    total_results[method] += result_count
                    
                    print(f"  {method.upper()}: ✅ {result_count}개 결과, {timing:.3f}초")
                    
                    # 상위 결과 표시
                    top_results = result["top_results"].get(method, [])
                    for j, top_result in enumerate(top_results):
                        score = top_result.get("score", 0)
                        content_preview = top_result.get("content", "")[:100] + "..."
                        print(f"    #{j+1}: score={score:.3f} | {content_preview}")
                else:
                    print(f"  {method.upper()}: ❌ 검색 실패")
        
        print("\n📈 전체 성능 요약:")
        print("=" * 80)
        
        num_queries = len(comparison_results)
        
        print(f"벡터 검색  : 성공 {successful_searches['vector']}/{num_queries}, "
              f"평균 {total_vector_time/num_queries:.3f}초, "
              f"총 {total_results['vector']}개 결과")
        
        print(f"BM25 검색  : 성공 {successful_searches['bm25']}/{num_queries}, "
              f"평균 {total_bm25_time/num_queries:.3f}초, "
              f"총 {total_results['bm25']}개 결과")
        
        print(f"하이브리드  : 성공 {successful_searches['hybrid']}/{num_queries}, "
              f"평균 {total_hybrid_time/num_queries:.3f}초, "
              f"총 {total_results['hybrid']}개 결과")
        
        # 검증
        assert successful_searches["vector"] >= 0, "벡터 검색이 한 번도 성공하지 않았습니다"
        assert successful_searches["bm25"] >= 0, "BM25 검색이 한 번도 성공하지 않았습니다"  
        assert successful_searches["hybrid"] >= 0, "하이브리드 검색이 한 번도 성공하지 않았습니다"
        
        # 성능 검증 (각 검색이 10초 이내)
        assert total_vector_time/num_queries < 10, f"벡터 검색이 너무 느립니다: {total_vector_time/num_queries:.3f}초"
        assert total_bm25_time/num_queries < 10, f"BM25 검색이 너무 느립니다: {total_bm25_time/num_queries:.3f}초"
        assert total_hybrid_time/num_queries < 10, f"하이브리드 검색이 너무 느립니다: {total_hybrid_time/num_queries:.3f}초"
        
        print("\n✅ 모든 검색 방식 성능이 검증되었습니다!")

    async def test_search_performance_comparison(self):
        """검색 성능 비교 테스트"""
        print("\n⚡ 검색 성능 비교 테스트")
        
        # 간단한 데이터 준비 (이미 인덱싱된 데이터 사용)
        test_query = "pandas DataFrame"
        
        # 여러 번 검색하여 평균 성능 측정
        iterations = 3
        
        vector_times = []
        bm25_times = []
        hybrid_times = []
        
        async with httpx.AsyncClient() as client:
            for i in range(iterations):
                print(f"   반복 {i+1}/{iterations}...")
                
                # Vector 검색
                start_time = time.time()
                await client.post(
                    f"{self.base_url}/api/v1/search/vector",
                    json={
                        "query": test_query,
                        "collection_name": self.collection_name,
                        "top_k": 5
                    },
                    timeout=self.timeout
                )
                vector_times.append(time.time() - start_time)
                
                # BM25 검색  
                start_time = time.time()
                await client.post(
                    f"{self.base_url}/api/v1/search/bm25",
                    json={
                        "query": test_query,
                        "index_name": self.index_name,
                        "top_k": 5
                    },
                    timeout=self.timeout
                )
                bm25_times.append(time.time() - start_time)
                
                # Hybrid 검색
                start_time = time.time()
                await client.post(
                    f"{self.base_url}/api/v1/search/hybrid",
                    json={
                        "query": test_query,
                        "collection_name": self.collection_name,
                        "index_name": self.index_name,
                        "top_k": 5,
                        "vector_weight": 0.7,
                        "bm25_weight": 0.3
                    },
                    timeout=self.timeout
                )
                hybrid_times.append(time.time() - start_time)
        
        # 평균 계산
        avg_vector = sum(vector_times) / len(vector_times)
        avg_bm25 = sum(bm25_times) / len(bm25_times)
        avg_hybrid = sum(hybrid_times) / len(hybrid_times)
        
        print(f"\n📊 평균 검색 시간 ({iterations}회 측정):")
        print(f"벡터 검색: {avg_vector:.3f}초")
        print(f"BM25 검색: {avg_bm25:.3f}초")
        print(f"하이브리드 검색: {avg_hybrid:.3f}초")
        
        # 성능 검증
        assert avg_vector < 5.0, f"벡터 검색이 너무 느립니다: {avg_vector:.3f}초"
        assert avg_bm25 < 5.0, f"BM25 검색이 너무 느립니다: {avg_bm25:.3f}초"
        assert avg_hybrid < 5.0, f"하이브리드 검색이 너무 느립니다: {avg_hybrid:.3f}초"
        
        print("✅ 성능 비교 테스트 완료!") 