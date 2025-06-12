from typing import List
from .schema import GenerationRequest, GenerationResponse, CodeContext
from .generator import CodeGenerator
from .validator import CodeValidator
from app.features.search.service import SearchService
from app.features.search.schema import SearchRequest
import logging

logger = logging.getLogger(__name__)

class GenerationService:
    def __init__(
        self, 
        search_service: SearchService,
        generator: CodeGenerator,
        validator: CodeValidator
    ):
        self.search_service = search_service
        self.generator = generator
        self.validator = validator
    
    async def generate_code(self, request: GenerationRequest) -> GenerationResponse:
        """컨텍스트 기반 코드 생성"""
        try:
            # 관련 코드 검색
            contexts = await self._get_contexts(request)
            
            # 코드 생성
            generation_result = await self.generator.generate_code(request, contexts)
            
            # 코드 검증
            await self._validate_generated_code(generation_result)
            
            logger.info(f"코드 생성 완료: {len(generation_result.generated_code)}자, "
                       f"{generation_result.generation_time_ms}ms")
            
            return generation_result
            
        except Exception as e:
            logger.error(f"코드 생성 실패: {e}")
            raise
    
    async def _get_contexts(self, request: GenerationRequest) -> List[CodeContext]:
        """관련 컨텍스트 수집 (기존 SearchService 활용)"""
        search_request = SearchRequest(
            query=request.query,
            limit=request.context_limit,
            vector_weight=request.vector_weight,
            keyword_weight=request.keyword_weight,
            use_rrf=request.use_rrf
        )
        
        search_response = await self.search_service.search_code(search_request)
        
        contexts = []
        for result in search_response.results:
            context = CodeContext(
                function_name=result.function_name,
                code_content=result.code_content,
                file_path=result.file_path,
                relevance_score=result.combined_score,
                code_type=result.code_type,
                language=result.language
            )
            contexts.append(context)
        
        return contexts
    
    async def _validate_generated_code(self, generation_result: GenerationResponse) -> None:
        """생성된 코드 검증"""
        if generation_result.language == "python":
            validation_result = self.validator.validate_python_code(
                generation_result.generated_code
            )
        elif generation_result.language == "javascript":
            validation_result = self.validator.validate_javascript_code(
                generation_result.generated_code
            )
        elif generation_result.language == "java":
            validation_result = self.validator.validate_java_code(
                generation_result.generated_code
            )
        else:
            # 다른 언어는 기본 검증만 수행
            return
        
        if not validation_result.is_valid:
            error_msg = f"생성된 코드에 구문 오류가 있습니다: {', '.join(validation_result.syntax_errors)}"
            raise ValueError(error_msg)
        
        # 경고사항 로깅
        if validation_result.warnings:
            logger.warning(f"코드 품질 경고: {', '.join(validation_result.warnings)}")
        
        # Spring Boot 관련 제안사항 로깅
        if validation_result.suggestions and generation_result.language == "java":
            logger.info(f"Spring Boot 개선 제안: {', '.join(validation_result.suggestions)}") 