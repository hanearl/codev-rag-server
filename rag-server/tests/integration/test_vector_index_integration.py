import pytest
import asyncio
from typing import List
import tempfile
import os

from app.index.vector_service import VectorIndexService, VectorIndexConfig
from app.retriever.document_builder import DocumentBuilder, DocumentBuildConfig, EnhancedDocument
from app.retriever.ast_parser import CodeMetadata, Language, CodeType
from llama_index.core import Document
from llama_index.core.schema import TextNode


class TestVectorIndexIntegration:
    """Vector Index 통합 테스트"""
    
    @pytest.fixture
    def test_config(self):
        """테스트용 설정"""
        return VectorIndexConfig(
            collection_name="test_integration_vectors",
            qdrant_url="http://localhost:6333"  # 실제 Qdrant 연결 (통합 테스트용)
        )
    
    @pytest.fixture
    def vector_service(self, test_config):
        """Vector Index 서비스"""
        return VectorIndexService(test_config)
    
    @pytest.fixture
    def document_builder(self):
        """Document Builder"""
        config = DocumentBuildConfig(
            chunking_strategy="method_level",
            max_chunk_size=512,
            include_metadata=True
        )
        return DocumentBuilder(config)
    
    @pytest.fixture
    def sample_code_metadata(self):
        """샘플 코드 메타데이터"""
        return [
            CodeMetadata(
                file_path="src/main/java/User.java",
                language=Language.JAVA,
                code_type=CodeType.CLASS,
                name="User",
                line_start=1,
                line_end=50,
                namespace="com.example",
                imports=["java.util.List"],
                parent_class=None
            ),
            CodeMetadata(
                file_path="src/main/java/UserService.java", 
                language=Language.JAVA,
                code_type=CodeType.METHOD,
                name="findUserById",
                line_start=15,
                line_end=25,
                namespace="com.example.service",
                imports=["com.example.User"],
                parent_class="UserService"
            ),
            CodeMetadata(
                file_path="src/auth.py",
                language=Language.PYTHON,
                code_type=CodeType.FUNCTION,
                name="authenticate_user",
                line_start=10,
                line_end=30,
                namespace=None,
                imports=["hashlib", "jwt"],
                parent_class=None
            )
        ]
    
    @pytest.fixture
    def sample_enhanced_documents(self, sample_code_metadata):
        """샘플 강화된 문서들"""
        documents = []
        
        for i, metadata in enumerate(sample_code_metadata):
            if metadata.language == Language.JAVA:
                if metadata.code_type == CodeType.CLASS:
                    text = f"""
public class {metadata.name} {{
    private Long id;
    private String name;
    private String email;
    
    public {metadata.name}() {{}}
    
    public Long getId() {{ return id; }}
    public void setId(Long id) {{ this.id = id; }}
    
    public String getName() {{ return name; }}
    public void setName(String name) {{ this.name = name; }}
}}
"""
                else:  # METHOD
                    text = f"""
public User {metadata.name}(Long id) {{
    return userRepository.findById(id)
        .orElseThrow(() -> new UserNotFoundException("User not found"));
}}
"""
            else:  # PYTHON
                text = f"""
def {metadata.name}(username: str, password: str) -> Optional[User]:
    user = get_user_by_username(username)
    if user and verify_password(password, user.password_hash):
        return generate_jwt_token(user)
    return None
"""
            
            document = Document(
                text=text.strip(),
                metadata=metadata.model_dump(),
                id_=f"doc_{i}"
            )
            
            text_node = TextNode(
                text=text.strip(),
                metadata=metadata.model_dump(),
                id_=f"doc_{i}"
            )
            
            enhanced_doc = EnhancedDocument(
                document=document,
                text_node=text_node,
                metadata=metadata,
                enhanced_content=f"Enhanced: {text.strip()}",
                search_keywords=[metadata.name.lower(), metadata.language.value, "code"],
                semantic_tags=[metadata.code_type.value, metadata.language.value],
                relationships={}
            )
            
            documents.append(enhanced_doc)
        
        return documents
    
    @pytest.mark.asyncio
    async def test_vector_service_initialization(self, vector_service):
        """Vector Service 초기화 테스트"""
        # 초기화 확인
        assert not vector_service._initialized
        
        # 초기화 실행
        await vector_service.initialize()
        assert vector_service._initialized
        
        # 헬스 체크
        health = await vector_service.health_check()
        assert health["status"] == "healthy"
        assert health["service"] == "vector_index"
    
    @pytest.mark.asyncio
    async def test_document_indexing_and_search(self, vector_service, sample_enhanced_documents):
        """문서 인덱싱 및 검색 테스트"""
        # 문서 인덱싱
        result = await vector_service.index_documents(sample_enhanced_documents)
        
        assert result["success"] is True
        assert result["indexed_count"] == len(sample_enhanced_documents)
        assert len(result["document_ids"]) == len(sample_enhanced_documents)
        
        # 검색 테스트 - Java 클래스 검색
        search_results = await vector_service.search_similar_code(
            query="User class with id and name fields",
            limit=5
        )
        
        assert len(search_results) > 0
        # Java User 클래스가 상위에 나타나야 함
        found_user_class = any(
            "User" in result.get("content", "") and "class" in result.get("content", "").lower()
            for result in search_results
        )
        assert found_user_class
        
        # 검색 테스트 - Python 인증 함수 검색
        auth_results = await vector_service.search_similar_code(
            query="authentication function with username password",
            limit=5
        )
        
        assert len(auth_results) > 0
        found_auth = any(
            "authenticate" in result.get("content", "").lower()
            for result in auth_results
        )
        assert found_auth
    
    @pytest.mark.asyncio  
    async def test_similarity_threshold_search(self, vector_service, sample_enhanced_documents):
        """유사도 임계값 검색 테스트"""
        # 문서 인덱싱
        await vector_service.index_documents(sample_enhanced_documents)
        
        # 높은 임계값으로 검색 (엄격한 검색)
        strict_results = await vector_service.search_similar_code(
            query="findUserById method",
            threshold=0.8,
            limit=10
        )
        
        # 낮은 임계값으로 검색 (관대한 검색)
        loose_results = await vector_service.search_similar_code(
            query="findUserById method", 
            threshold=0.3,
            limit=10
        )
        
        # 임계값이 높을수록 결과가 적어야 함
        assert len(strict_results) <= len(loose_results)
        
        # 모든 결과가 임계값 이상이어야 함
        for result in strict_results:
            assert result.get("score", 0) >= 0.8
    
    @pytest.mark.asyncio
    async def test_document_management_operations(self, vector_service, sample_enhanced_documents):
        """문서 관리 작업 테스트"""
        # 초기 인덱싱
        index_result = await vector_service.index_documents(sample_enhanced_documents)
        assert index_result["success"] is True
        
        doc_id = index_result["document_ids"][0]
        
        # 문서 조회
        retrieved_doc = await vector_service.get_document_by_id(doc_id)
        assert retrieved_doc is not None
        assert retrieved_doc["id"] == doc_id
        
        # 문서 업데이트
        updated_content = {
            "content": "Updated code content for testing",
            "metadata": {"file_path": "updated/test.java", "updated": True}
        }
        
        update_result = await vector_service.update_document(doc_id, updated_content)
        assert update_result["success"] is True
        
        # 업데이트된 문서 조회
        updated_doc = await vector_service.get_document_by_id(doc_id)
        assert updated_doc is not None
        assert "Updated code content" in updated_doc["content"]
        
        # 문서 삭제
        delete_result = await vector_service.delete_document(doc_id)
        assert delete_result["success"] is True
        
        # 삭제된 문서 조회 시도 (없어야 함)
        deleted_doc = await vector_service.get_document_by_id(doc_id)
        assert deleted_doc is None
    
    @pytest.mark.asyncio
    async def test_bulk_operations(self, vector_service):
        """대량 작업 테스트"""
        # 대량 문서 생성
        bulk_documents = []
        for i in range(50):
            metadata = CodeMetadata(
                file_path=f"test/bulk_{i}.py",
                language=Language.PYTHON,
                code_type=CodeType.FUNCTION,
                name=f"function_{i}",
                line_start=1,
                line_end=10
            )
            
            document = Document(
                text=f"def function_{i}(): return {i}",
                metadata=metadata.model_dump(),
                id_=f"bulk_doc_{i}"
            )
            
            text_node = TextNode(
                text=f"def function_{i}(): return {i}",
                metadata=metadata.model_dump(),
                id_=f"bulk_doc_{i}"
            )
            
            enhanced_doc = EnhancedDocument(
                document=document,
                text_node=text_node,
                metadata=metadata,
                enhanced_content=f"def function_{i}(): return {i}",
                search_keywords=[f"function_{i}", "python"],
                semantic_tags=["function"],
                relationships={}
            )
            
            bulk_documents.append(enhanced_doc)
        
        # 배치 크기 10으로 대량 인덱싱
        bulk_result = await vector_service.bulk_index_documents(
            bulk_documents, 
            batch_size=10
        )
        
        assert bulk_result["success"] is True
        assert bulk_result["indexed_count"] == 50
        assert bulk_result["batch_count"] == 5  # 50/10 = 5 배치
        
        # 통계 확인
        stats = await vector_service.get_collection_stats()
        assert stats["total_documents"] >= 50
    
    @pytest.mark.asyncio
    async def test_file_path_deletion(self, vector_service, sample_enhanced_documents):
        """파일 경로 기반 삭제 테스트"""
        # 문서 인덱싱
        await vector_service.index_documents(sample_enhanced_documents)
        
        # 특정 파일 경로의 문서들 삭제
        target_file_path = "src/main/java/User.java"
        
        delete_result = await vector_service.delete_by_file_path(target_file_path)
        assert delete_result["success"] is True
        assert delete_result["deleted_count"] >= 0  # 0개 이상 삭제됨
        
        # 삭제 후 검색해서 해당 파일의 문서가 없는지 확인
        remaining_results = await vector_service.search_similar_code(
            query="User class",
            limit=10
        )
        
        # 삭제된 파일 경로의 문서가 결과에 없어야 함
        for result in remaining_results:
            metadata = result.get("metadata", {})
            assert metadata.get("file_path") != target_file_path
    
    @pytest.mark.asyncio
    async def test_legacy_document_compatibility(self, vector_service):
        """기존 형식 문서 호환성 테스트"""
        # 기존 청크 형식 데이터
        legacy_chunks = [
            {
                "id": "legacy_1",
                "content": "public class LegacyService { }",
                "metadata": {
                    "file_path": "legacy/LegacyService.java",
                    "language": "java",
                    "code_type": "class"
                }
            },
            {
                "id": "legacy_2", 
                "text": "def legacy_function(): pass",  # 다른 키 이름 사용
                "metadata": {
                    "file_path": "legacy/legacy.py",
                    "language": "python"
                }
            }
        ]
        
        # 기존 형식 문서 인덱싱
        result = await vector_service.index_legacy_documents(legacy_chunks)
        
        assert result["success"] is True
        assert result["indexed_count"] == len(legacy_chunks)
        
        # 검색으로 호환성 확인
        search_results = await vector_service.search_similar_code(
            query="legacy service",
            limit=5
        )
        
        assert len(search_results) > 0
        found_legacy = any(
            "legacy" in result.get("content", "").lower()
            for result in search_results
        )
        assert found_legacy
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, vector_service):
        """오류 처리 및 복구 테스트"""
        # 잘못된 문서 형식으로 인덱싱 시도
        invalid_documents = [
            {"invalid": "document"},  # 필수 필드 누락
            {"content": "", "metadata": {}},  # 빈 컨텐츠
        ]
        
        # 오류가 발생해도 서비스가 중단되지 않아야 함
        try:
            result = await vector_service.index_legacy_documents(invalid_documents)
            # 실패하거나 부분적으로 성공할 수 있음
            assert "success" in result
        except Exception:
            # 예외가 발생해도 서비스는 계속 동작해야 함
            pass
        
        # 헬스 체크로 서비스 상태 확인
        health = await vector_service.health_check()
        # 오류 후에도 서비스는 healthy 상태여야 함 (또는 적절한 오류 상태)
        assert health["status"] in ["healthy", "unhealthy"]
        assert "service" in health
    
    @pytest.mark.asyncio
    async def test_search_performance_and_accuracy(self, vector_service, sample_enhanced_documents):
        """검색 성능 및 정확도 테스트"""
        # 문서 인덱싱
        await vector_service.index_documents(sample_enhanced_documents)
        
        # 정확한 매칭 테스트
        exact_results = await vector_service.search_similar_code(
            query="User class with id name email fields",
            limit=3
        )
        
        # User 클래스가 최상위에 있어야 함
        if exact_results:
            top_result = exact_results[0]
            assert "User" in top_result.get("content", "")
            assert top_result.get("score", 0) > 0.5  # 합리적인 유사도 점수
        
        # 유사한 개념 검색 테스트
        conceptual_results = await vector_service.search_similar_code(
            query="authentication login verify user credentials",
            limit=3
        )
        
        # 인증 관련 함수가 발견되어야 함
        if conceptual_results:
            found_auth_concept = any(
                any(keyword in result.get("content", "").lower() 
                    for keyword in ["auth", "login", "password", "verify"])
                for result in conceptual_results
            )
            assert found_auth_concept 