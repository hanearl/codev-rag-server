from typing import List
from .schema import CodeContext
from app.features.prompts.manager import PromptManager as BasePromptManager
from app.features.prompts.schema import CodeContext as PromptCodeContext
from app.features.prompts.repository import PromptRepository
import logging

logger = logging.getLogger(__name__)

class PromptManager:
    """코드 생성용 프롬프트 관리자 (기존 prompts 모듈 활용)"""
    
    def __init__(self, repository: PromptRepository = None):
        self.repository = repository or PromptRepository()
        self.base_manager = BasePromptManager(self.repository)
    
    def get_system_prompt(self, language: str, include_tests: bool = False) -> str:
        """언어별 시스템 프롬프트 생성 (기존 prompts 모듈 활용)"""
        try:
            return self.base_manager.get_system_prompt(language, include_tests)
        except Exception as e:
            logger.warning(f"기존 템플릿 사용 실패, 기본 프롬프트 사용: {e}")
            return self._get_fallback_system_prompt(language, include_tests)
    
    def get_user_prompt(self, query: str, contexts: List[CodeContext], language: str) -> str:
        """사용자 요청 프롬프트 생성 (기존 prompts 모듈 활용)"""
        try:
            # CodeContext를 PromptCodeContext로 변환
            prompt_contexts = self._convert_contexts(contexts)
            
            # 기존 manager 사용하여 사용자 프롬프트 생성
            base_prompt = self.base_manager.get_user_prompt(
                query=query, 
                contexts=prompt_contexts,
                include_tests=False
            )
            
            # 언어 정보 추가
            enhanced_prompt = f"언어: {language}\n요청: {query}\n\n{base_prompt}"
            
            return enhanced_prompt
            
        except Exception as e:
            logger.warning(f"기존 템플릿 사용 실패, 기본 프롬프트 사용: {e}")
            return self._get_fallback_user_prompt(query, contexts, language)
    
    def _convert_contexts(self, contexts: List[CodeContext]) -> List[PromptCodeContext]:
        """CodeContext를 PromptCodeContext로 변환"""
        prompt_contexts = []
        for context in contexts:
            prompt_context = PromptCodeContext(
                function_name=context.function_name or "unknown",
                code_content=context.code_content,
                file_path=context.file_path,
                relevance_score=context.relevance_score
            )
            prompt_contexts.append(prompt_context)
        return prompt_contexts
    
    def _get_fallback_system_prompt(self, language: str, include_tests: bool = False) -> str:
        """기본 시스템 프롬프트 (백업용)"""
        base_prompt = f"""당신은 {language.upper()} 전문가입니다.

주어진 요청에 따라 고품질의 {language} 코드를 생성해주세요.

## 코딩 표준
- 타입 힌트 사용 (Python의 경우)
- 명확한 변수명 및 함수명
- 적절한 주석 및 독스트링
- 에러 핸들링 고려
- 코딩 컨벤션 준수

## 응답 형식
- 실행 가능한 코드만 반환
- 추가 설명은 코드 주석으로 작성
- 마크다운 코드 블록 사용하지 말 것"""

        if include_tests:
            test_prompt = """

## 테스트 코드
- 생성한 함수에 대한 pytest 테스트 코드를 포함
- 정상 케이스와 에지 케이스 모두 테스트
- 테스트 함수명은 test_로 시작"""
            base_prompt += test_prompt

        return base_prompt
    
    def _get_fallback_user_prompt(self, query: str, contexts: List[CodeContext], language: str) -> str:
        """기본 사용자 프롬프트 (백업용)"""
        prompt = f"언어: {language}\n요청: {query}\n\n"
        
        if contexts:
            prompt += "참고 코드:\n"
            for i, context in enumerate(contexts, 1):
                prompt += f"\n{i}. 파일: {context.file_path}\n"
                if context.function_name:
                    prompt += f"   함수: {context.function_name}\n"
                prompt += f"   코드:\n```\n{context.code_content}\n```\n"
            
            prompt += "\n위 참고 코드의 패턴과 스타일을 참고하여 요청된 코드를 생성해주세요.\n"
        else:
            prompt += "관련 참고 코드가 없습니다. 요청에 맞는 새로운 코드를 생성해주세요.\n"
        
        return prompt 