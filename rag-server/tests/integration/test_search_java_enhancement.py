"""
검색 API Java 메타데이터 향상 통합 테스트
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.features.search.service import HybridSearchService
from app.features.search.schema import (
    VectorSearchRequest, BM25SearchRequest, HybridSearchRequest
)


@pytest.fixture
def mock_search_service():
    """모의 검색 서비스를 생성합니다."""
    service = HybridSearchService()
    return service


@pytest.fixture
def sample_java_content():
    """테스트용 Java 파일 내용"""
    return """
package com.example.user.service;

import java.util.List;
import com.example.user.model.User;

/**
 * 사용자 관리 서비스
 */
public class UserService {
    
    public List<User> getAllUsers() {
        // 모든 사용자 조회 로직
        return userRepository.findAll();
    }
    
    public User createUser(UserCreateRequest request) {
        // 사용자 생성 로직
        User user = new User();
        user.setName(request.getName());
        user.setEmail(request.getEmail());
        return userRepository.save(user);
    }
}
"""


@pytest.fixture
def sample_java_search_results():
    """모의 Java 검색 결과"""
    return [
        {
            "id": "java_file_1",
            "content": """
package com.example.user.service;

public class UserService {
    public void createUser() {
        // 사용자 생성 로직
    }
}
""",
            "score": 0.95,
            "metadata": {
                "type": "java",
                "file_path": "/src/main/java/com/example/user/service/UserService.java",
                "author": "test_user"
            }
        },
        {
            "id": "java_file_2", 
            "content": """
package com.example.user.model;

public class User {
    private String name;
    private String email;
}
""",
            "score": 0.85,
            "metadata": {
                "language": "java",
                "file_path": "/src/main/java/com/example/user/model/User.java",
                "size": 1024
            }
        },
        {
            "id": "python_file_1",
            "content": """
def create_user():
    return {"name": "test"}
""",
            "score": 0.75,
            "metadata": {
                "type": "python",
                "file_path": "/src/user_service.py"
            }
        }
    ]


class TestJavaMetadataEnhancement:
    """Java 메타데이터 향상 통합 테스트"""
    
    @pytest.mark.asyncio
    async def test_vector_search_enhances_java_metadata(
        self, 
        mock_search_service, 
        sample_java_search_results
    ):
        """벡터 검색에서 Java 메타데이터가 향상되어야 함"""
        
        # Given
        request = VectorSearchRequest(
            query="user service",
            collection_name="test_collection",
            top_k=3
        )
        
        # 벡터 서비스 모킹
        with patch.object(mock_search_service.vector_service, 'search_similar_code') as mock_vector_search:
            mock_vector_search.return_value = sample_java_search_results
            
            # When
            response = await mock_search_service.vector_search(request)
            
            # Then
            assert response.success is True
            assert len(response.results) == 3
            
            # Java 파일들의 메타데이터 확인
            java_result_1 = response.results[0]
            assert java_result_1.metadata["package"] == "com.example.user.service"
            assert java_result_1.metadata["class_name"] == "UserService"
            assert java_result_1.metadata["full_class_name"] == "com.example.user.service.UserService"
            assert java_result_1.metadata["type"] == "java"  # 기존 필드 보존
            assert java_result_1.metadata["author"] == "test_user"  # 기존 필드 보존
            
            java_result_2 = response.results[1]
            assert java_result_2.metadata["package"] == "com.example.user.model"
            assert java_result_2.metadata["class_name"] == "User"
            assert java_result_2.metadata["full_class_name"] == "com.example.user.model.User"
            assert java_result_2.metadata["language"] == "java"  # 기존 필드 보존
            assert java_result_2.metadata["size"] == 1024  # 기존 필드 보존
            
            # Python 파일은 변경되지 않아야 함
            python_result = response.results[2]
            assert "package" not in python_result.metadata
            assert "class_name" not in python_result.metadata
            assert python_result.metadata["type"] == "python"
    
    @pytest.mark.asyncio
    async def test_bm25_search_enhances_java_metadata(
        self, 
        mock_search_service, 
        sample_java_search_results
    ):
        """BM25 검색에서 Java 메타데이터가 향상되어야 함"""
        
        # Given
        request = BM25SearchRequest(
            query="user service",
            index_name="test_index",
            top_k=3
        )
        
        # BM25 서비스 모킹
        with patch.object(mock_search_service.bm25_service, 'search_keywords') as mock_bm25_search:
            mock_bm25_search.return_value = sample_java_search_results
            
            # When
            response = await mock_search_service.bm25_search(request)
            
            # Then
            assert response.success is True
            assert len(response.results) == 3
            
            # Java 파일의 메타데이터 확인
            java_result = response.results[0]
            assert java_result.metadata["package"] == "com.example.user.service"
            assert java_result.metadata["class_name"] == "UserService"
            assert java_result.metadata["full_class_name"] == "com.example.user.service.UserService"
    
    @pytest.mark.asyncio
    async def test_hybrid_search_enhances_java_metadata(
        self, 
        mock_search_service, 
        sample_java_search_results
    ):
        """하이브리드 검색에서 Java 메타데이터가 향상되어야 함"""
        
        # Given
        request = HybridSearchRequest(
            query="user service",
            collection_name="test_collection",
            index_name="test_index",
            top_k=2,
            use_rrf=True
        )
        
        # 서비스 모킹
        with patch.object(mock_search_service.vector_service, 'search_similar_code') as mock_vector_search, \
             patch.object(mock_search_service.bm25_service, 'search_keywords') as mock_bm25_search:
            
            mock_vector_search.return_value = sample_java_search_results[:2]
            mock_bm25_search.return_value = sample_java_search_results[:2]
            
            # When
            response = await mock_search_service.hybrid_search(request)
            
            # Then
            assert response.success is True
            assert len(response.results) > 0
            
            # 결과에서 Java 파일 찾기
            java_results = [r for r in response.results if r.metadata.get('type') == 'java' or r.metadata.get('language') == 'java']
            assert len(java_results) > 0
            
            # Java 메타데이터 확인
            for java_result in java_results:
                if "com.example.user.service" in java_result.content:
                    assert java_result.metadata["package"] == "com.example.user.service"
                    assert java_result.metadata["class_name"] == "UserService"
                elif "com.example.user.model" in java_result.content:
                    assert java_result.metadata["package"] == "com.example.user.model"
                    assert java_result.metadata["class_name"] == "User"
    
    @pytest.mark.asyncio
    async def test_java_file_without_package_declaration(
        self, 
        mock_search_service
    ):
        """패키지 선언이 없는 Java 파일 처리 테스트"""
        
        # Given - 패키지 선언이 없는 Java 파일
        search_results = [
            {
                "id": "simple_java_file",
                "content": """
public class SimpleClass {
    public void doSomething() {
        System.out.println("Hello World");
    }
}
""",
                "score": 0.9,
                "metadata": {
                    "type": "java",
                    "file_path": "/SimpleClass.java"
                }
            }
        ]
        
        request = VectorSearchRequest(
            query="simple class",
            collection_name="test_collection",
            top_k=1
        )
        
        with patch.object(mock_search_service.vector_service, 'search_similar_code') as mock_vector_search:
            mock_vector_search.return_value = search_results
            
            # When
            response = await mock_search_service.vector_search(request)
            
            # Then
            assert response.success is True
            assert len(response.results) == 1
            
            result = response.results[0]
            # 패키지가 없어도 클래스명은 추출되어야 함
            assert "package" not in result.metadata
            assert result.metadata["class_name"] == "SimpleClass"
            assert "full_class_name" not in result.metadata  # 패키지가 없으므로 full_class_name도 없음
    
    @pytest.mark.asyncio
    async def test_empty_java_file_with_file_path(
        self, 
        mock_search_service
    ):
        """내용이 비어있는 Java 파일에서 파일 경로로 클래스명 추출 테스트"""
        
        # Given - 내용이 거의 없는 Java 파일
        search_results = [
            {
                "id": "empty_java_file",
                "content": "// Empty file",
                "score": 0.1,
                "metadata": {
                    "type": "java",
                    "file_path": "/src/main/java/com/test/EmptyClass.java"
                }
            }
        ]
        
        request = VectorSearchRequest(
            query="empty",
            collection_name="test_collection",
            top_k=1
        )
        
        with patch.object(mock_search_service.vector_service, 'search_similar_code') as mock_vector_search:
            mock_vector_search.return_value = search_results
            
            # When
            response = await mock_search_service.vector_search(request)
            
            # Then
            assert response.success is True
            assert len(response.results) == 1
            
            result = response.results[0]
            # 파일 경로에서 클래스명이 추출되어야 함
            assert result.metadata["class_name"] == "EmptyClass" 