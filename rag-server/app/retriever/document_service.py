from typing import List, Dict, Any, Optional
from .document_builder import DocumentBuilder, DocumentBuildConfig, DocumentBuildResult, EnhancedDocument
from .ast_parser import ParseResult
import logging

logger = logging.getLogger(__name__)

class DocumentService:
    """Document 생성 서비스"""
    
    def __init__(self, embedding_client=None):
        self.embedding_client = embedding_client
        self.builder = DocumentBuilder()
    
    async def create_documents_from_parse_result(
        self, 
        parse_result: ParseResult,
        config: Optional[DocumentBuildConfig] = None
    ) -> DocumentBuildResult:
        """파싱 결과로부터 Document 생성"""
        if config:
            self.builder.config = config
        
        result = await self.builder.build_from_parse_result(parse_result)
        
        # 임베딩 생성 (옵션)
        if self.embedding_client:
            await self._generate_embeddings(result.documents)
        
        return result
    
    async def create_documents_from_legacy_chunks(
        self,
        chunks: List[Dict[str, Any]],
        config: Optional[DocumentBuildConfig] = None
    ) -> DocumentBuildResult:
        """기존 청크로부터 Document 생성"""
        if config:
            self.builder.config = config
        
        result = await self.builder.build_from_legacy_chunks(chunks)
        
        # 임베딩 생성 (옵션)
        if self.embedding_client:
            await self._generate_embeddings(result.documents)
        
        return result
    
    async def _generate_embeddings(self, documents: List[EnhancedDocument]):
        """Document들에 대한 임베딩 생성"""
        texts = [doc.enhanced_content for doc in documents]
        
        try:
            # 임베딩 클라이언트가 있는 경우에만 실행
            if hasattr(self.embedding_client, 'embed_bulk'):
                embedding_response = await self.embedding_client.embed_bulk({"texts": texts})
                embeddings = [emb["embedding"] for emb in embedding_response["embeddings"]]
                
                # Document에 임베딩 추가
                for doc, embedding in zip(documents, embeddings):
                    doc.document.embedding = embedding
                    doc.text_node.embedding = embedding
            else:
                logger.warning("임베딩 클라이언트가 embed_bulk 메서드를 지원하지 않습니다.")
                
        except Exception as e:
            # 임베딩 생성 실패 시 로그만 남기고 계속 진행
            logger.warning(f"임베딩 생성 실패: {e}")
    
    def update_config(self, config: DocumentBuildConfig):
        """Document Builder 설정 업데이트"""
        self.builder.config = config
    
    def get_statistics(self, result: DocumentBuildResult) -> Dict[str, Any]:
        """Document 빌드 결과 통계 반환"""
        return {
            "total_documents": result.total_documents,
            "build_time_ms": result.build_time_ms,
            "statistics": result.statistics,
            "average_keywords_per_doc": sum(len(doc.search_keywords) for doc in result.documents) / len(result.documents) if result.documents else 0,
            "average_tags_per_doc": sum(len(doc.semantic_tags) for doc in result.documents) / len(result.documents) if result.documents else 0,
            "languages": list(set(doc.metadata.language.value for doc in result.documents)),
            "code_types": list(set(doc.metadata.code_type.value for doc in result.documents))
        } 