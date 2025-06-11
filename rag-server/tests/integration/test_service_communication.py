import pytest
import requests
import time
from typing import Dict, Any


class TestServiceCommunication:
    """서비스 간 통신 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 설정"""
        self.base_urls = {
            'vector-db': 'http://localhost:6333',
            'embedding-server': 'http://localhost:8001',
            'llm-server': 'http://localhost:8002'
        }
        self.timeout = 10
    
    def test_embedding_server_communication(self):
        """Embedding Server 통신 테스트"""
        # Given: Embedding Server가 실행 중
        base_url = self.base_urls['embedding-server']
        
        # When: 텍스트 임베딩 요청
        response = requests.post(
            f'{base_url}/embedding/embed',
            json={'text': 'def hello_world():\n    print("Hello, World!")'},
            timeout=self.timeout
        )
        
        # Then: 정상적인 임베딩 결과 반환
        assert response.status_code == 200
        data = response.json()
        assert 'embedding' in data
        assert 'text' in data
        assert 'model' in data
        assert len(data['embedding']) == 384  # all-MiniLM-L6-v2 차원
        assert isinstance(data['embedding'], list)
        assert all(isinstance(x, float) for x in data['embedding'])
    
    def test_embedding_server_bulk_communication(self):
        """Embedding Server 벌크 통신 테스트"""
        # Given: Embedding Server가 실행 중
        base_url = self.base_urls['embedding-server']
        
        # When: 벌크 텍스트 임베딩 요청
        response = requests.post(
            f'{base_url}/embedding/embed/bulk',
            json={
                'texts': [
                    'def function_one():\n    pass',
                    'class MyClass:\n    def __init__(self):\n        pass'
                ]
            },
            timeout=self.timeout
        )
        
        # Then: 정상적인 벌크 임베딩 결과 반환
        assert response.status_code == 200
        data = response.json()
        assert 'embeddings' in data
        assert 'count' in data
        assert data['count'] == 2
        assert len(data['embeddings']) == 2
        
        for embedding_data in data['embeddings']:
            assert 'embedding' in embedding_data
            assert 'text' in embedding_data
            assert len(embedding_data['embedding']) == 384
    
    def test_llm_server_communication(self):
        """LLM Server 통신 테스트"""
        # Given: LLM Server가 실행 중
        base_url = self.base_urls['llm-server']
        
        # When: 채팅 완성 요청
        response = requests.post(
            f'{base_url}/v1/chat/completions',
            json={
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'user', 'content': 'Write a simple Python function that returns "Hello"'}
                ],
                'max_tokens': 100
            },
            timeout=30  # LLM 응답은 더 오래 걸릴 수 있음
        )
        
        # Then: 정상적인 응답 반환
        assert response.status_code == 200
        data = response.json()
        assert 'choices' in data
        assert 'model' in data
        assert 'usage' in data
        assert len(data['choices']) > 0
        assert 'message' in data['choices'][0]
        assert 'content' in data['choices'][0]['message']
    
    def test_llm_server_models_endpoint(self):
        """LLM Server 모델 목록 엔드포인트 테스트"""
        # Given: LLM Server가 실행 중
        base_url = self.base_urls['llm-server']
        
        # When: 모델 목록 요청
        response = requests.get(f'{base_url}/v1/models', timeout=self.timeout)
        
        # Then: 정상적인 모델 목록 반환
        assert response.status_code == 200
        data = response.json()
        assert 'object' in data
        assert 'data' in data
        assert data['object'] == 'list'
        assert len(data['data']) > 0
    
    def test_vector_db_communication(self):
        """Vector DB 통신 테스트"""
        # Given: Vector DB가 실행 중
        base_url = self.base_urls['vector-db']
        
        # When: 컬렉션 리스트 요청
        response = requests.get(f'{base_url}/collections', timeout=self.timeout)
        
        # Then: 정상적인 응답 반환
        assert response.status_code == 200
        data = response.json()
        assert 'result' in data
        assert 'collections' in data['result']
    
    def test_vector_db_collection_info(self):
        """Vector DB 컬렉션 정보 테스트"""
        # Given: Vector DB가 실행 중이고 code_embeddings 컬렉션이 존재
        base_url = self.base_urls['vector-db']
        collection_name = 'code_embeddings'
        
        # When: 컬렉션 정보 요청
        response = requests.get(
            f'{base_url}/collections/{collection_name}',
            timeout=self.timeout
        )
        
        # Then: 정상적인 컬렉션 정보 반환
        if response.status_code == 200:
            data = response.json()
            assert 'result' in data
            assert 'config' in data['result']
            assert 'vectors_count' in data['result']
        else:
            # 컬렉션이 아직 생성되지 않은 경우 404는 정상
            assert response.status_code == 404
    
    def test_service_error_handling(self):
        """서비스 오류 처리 테스트"""
        # Given: Embedding Server가 실행 중
        base_url = self.base_urls['embedding-server']
        
        # When: 잘못된 요청 전송
        response = requests.post(
            f'{base_url}/embedding/embed',
            json={},  # 필수 필드 누락
            timeout=self.timeout
        )
        
        # Then: 적절한 오류 응답
        assert response.status_code == 422  # Validation Error
    
    def test_cross_service_workflow(self):
        """서비스 간 워크플로우 테스트"""
        # Given: 모든 서비스가 실행 중
        embedding_url = self.base_urls['embedding-server']
        vector_db_url = self.base_urls['vector-db']
        
        # When: 임베딩 생성
        embed_response = requests.post(
            f'{embedding_url}/embedding/embed',
            json={'text': 'def test_function():\n    return "test"'},
            timeout=self.timeout
        )
        
        # Then: 임베딩 생성 성공
        assert embed_response.status_code == 200
        embedding_data = embed_response.json()
        
        # When: Vector DB에 데이터 삽입 시도 (실제로는 RAG Server에서 수행)
        # 여기서는 Vector DB 연결만 확인
        health_response = requests.get(f'{vector_db_url}/health', timeout=self.timeout)
        
        # Then: Vector DB 연결 성공
        assert health_response.status_code == 200 