# Task 13: LangChain PromptTemplate 구현

## 📋 작업 개요
LangChain PromptTemplate을 활용하여 코드 설명, 질의응답, 코드 생성 등 다양한 RAG 시나리오에 최적화된 프롬프트 시스템을 구현합니다.

## 🎯 작업 목표
- LangChain PromptTemplate 기반 프롬프트 관리 시스템 구축
- 코드 특화 프롬프트 템플릿 설계 및 구현
- 동적 컨텍스트 삽입 및 템플릿 조합 기능
- 기존 프롬프트 로직과의 호환성 보장

## 🔗 의존성
- **선행 Task**: Task 12 (Hybrid Retriever 구현)
- **활용할 기존 코드**: `app/features/prompts/service.py`

## 🔧 구현 사항

### 1. 코드 특화 PromptTemplate 구현

```python
# app/llm/langchain_prompt.py
from typing import List, Dict, Any, Optional, Union
from langchain.prompts import PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.prompts.base import BasePromptTemplate
from langchain.schema import BaseMessage
from pydantic import BaseModel, Field
from enum import Enum

class PromptType(str, Enum):
    """프롬프트 타입"""
    CODE_EXPLANATION = "code_explanation"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    API_DOCUMENTATION = "api_documentation"
    DEBUGGING_HELP = "debugging_help"
    CODE_COMPARISON = "code_comparison"
    BEST_PRACTICES = "best_practices"
    GENERAL_QA = "general_qa"

class CodeContext(BaseModel):
    """코드 컨텍스트 모델"""
    code_content: str
    language: str
    file_path: Optional[str] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    line_numbers: Optional[str] = None
    related_code: List[str] = []
    metadata: Dict[str, Any] = {}

class PromptConfig(BaseModel):
    """프롬프트 설정"""
    max_context_length: int = Field(default=4000, description="최대 컨텍스트 길이")
    include_metadata: bool = Field(default=True, description="메타데이터 포함 여부")
    language_preference: str = Field(default="korean", description="응답 언어")
    detail_level: str = Field(default="medium", description="설명 상세도 (brief/medium/detailed)")
    include_examples: bool = Field(default=True, description="예시 포함 여부")

class CodePromptBuilder:
    """코드 특화 프롬프트 빌더"""
    
    def __init__(self, config: PromptConfig = None):
        self.config = config or PromptConfig()
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[PromptType, BasePromptTemplate]:
        """기본 템플릿 초기화"""
        templates = {}
        
        # 코드 설명 템플릿
        templates[PromptType.CODE_EXPLANATION] = self._create_code_explanation_template()
        
        # 코드 생성 템플릿
        templates[PromptType.CODE_GENERATION] = self._create_code_generation_template()
        
        # 코드 리뷰 템플릿
        templates[PromptType.CODE_REVIEW] = self._create_code_review_template()
        
        # API 문서화 템플릿
        templates[PromptType.API_DOCUMENTATION] = self._create_api_documentation_template()
        
        # 디버깅 도움 템플릿
        templates[PromptType.DEBUGGING_HELP] = self._create_debugging_help_template()
        
        # 일반 QA 템플릿
        templates[PromptType.GENERAL_QA] = self._create_general_qa_template()
        
        return templates
    
    def _create_code_explanation_template(self) -> ChatPromptTemplate:
        """코드 설명 템플릿"""
        system_template = """당신은 숙련된 소프트웨어 개발자이자 코드 멘토입니다. 
주어진 코드를 분석하고 {detail_level} 수준으로 설명해주세요.

설명 가이드라인:
1. 코드의 주요 목적과 기능 설명
2. 중요한 로직과 알고리즘 분석
3. 사용된 패턴이나 기법 설명
4. 주의점이나 개선 포인트 제시
{examples_instruction}

응답은 {language_preference}로 해주세요."""

        human_template = """분석할 코드:

```{language}
{code_content}
```

{metadata_section}

질문: {question}

위 코드에 대해 설명해주세요."""

        system_prompt = SystemMessagePromptTemplate.from_template(system_template)
        human_prompt = HumanMessagePromptTemplate.from_template(human_template)
        
        return ChatPromptTemplate.from_messages([system_prompt, human_prompt])
    
    def _create_code_generation_template(self) -> ChatPromptTemplate:
        """코드 생성 템플릿"""
        system_template = """당신은 전문 소프트웨어 개발자입니다. 
주어진 요구사항에 따라 {language} 코드를 생성해주세요.

코드 생성 가이드라인:
1. 클린 코드 원칙 준수
2. 적절한 주석 포함
3. 에러 처리 고려
4. 성능과 가독성 모두 고려
5. 최신 언어 기능 활용

{related_code_instruction}

응답은 {language_preference}로 해주세요."""

        human_template = """요구사항: {requirements}

{context_section}

{related_code_section}

위 요구사항에 맞는 {language} 코드를 생성해주세요."""

        system_prompt = SystemMessagePromptTemplate.from_template(system_template)
        human_prompt = HumanMessagePromptTemplate.from_template(human_template)
        
        return ChatPromptTemplate.from_messages([system_prompt, human_prompt])
    
    def _create_code_review_template(self) -> ChatPromptTemplate:
        """코드 리뷰 템플릿"""
        system_template = """당신은 시니어 개발자로서 코드 리뷰를 수행합니다.
다음 관점에서 코드를 분석해주세요:

리뷰 체크리스트:
1. 코드 품질 (가독성, 유지보수성)
2. 성능 최적화 가능성
3. 보안 취약점
4. 버그 가능성
5. 설계 패턴 적용
6. 테스트 가능성
7. 코딩 컨벤션 준수

응답 형식:
- 👍 좋은 점
- ⚠️ 개선 필요한 점
- 💡 제안사항
- 🐛 잠재적 이슈

응답은 {language_preference}로 해주세요."""

        human_template = """리뷰할 코드:

```{language}
{code_content}
```

{metadata_section}

{context_section}

위 코드에 대한 상세한 리뷰를 제공해주세요."""

        system_prompt = SystemMessagePromptTemplate.from_template(system_template)
        human_prompt = HumanMessagePromptTemplate.from_template(human_template)
        
        return ChatPromptTemplate.from_messages([system_prompt, human_prompt])
    
    def _create_api_documentation_template(self) -> ChatPromptTemplate:
        """API 문서화 템플릿"""
        system_template = """당신은 API 문서 작성 전문가입니다.
주어진 코드를 바탕으로 완전하고 명확한 API 문서를 작성해주세요.

문서 구조:
1. 함수/메서드 개요
2. 매개변수 설명 (타입, 설명, 필수/선택)
3. 반환값 설명
4. 사용 예시
5. 예외 처리
6. 주의사항

응답은 {language_preference}로 해주세요."""

        human_template = """문서화할 API 코드:

```{language}
{code_content}
```

{metadata_section}

위 API에 대한 완전한 문서를 작성해주세요."""

        system_prompt = SystemMessagePromptTemplate.from_template(system_template)
        human_prompt = HumanMessagePromptTemplate.from_template(human_template)
        
        return ChatPromptTemplate.from_messages([system_prompt, human_prompt])
    
    def _create_debugging_help_template(self) -> ChatPromptTemplate:
        """디버깅 도움 템플릿"""
        system_template = """당신은 디버깅 전문가입니다. 
코드 문제를 분석하고 해결 방안을 제시해주세요.

디버깅 접근법:
1. 문제 상황 분석
2. 가능한 원인 파악
3. 단계별 해결 방법
4. 예방 방법 제안
5. 테스트 방법 안내

응답은 {language_preference}로 해주세요."""

        human_template = """문제가 있는 코드:

```{language}
{code_content}
```

{error_info}

{metadata_section}

문제 설명: {problem_description}

위 코드의 문제를 분석하고 해결 방법을 제시해주세요."""

        system_prompt = SystemMessagePromptTemplate.from_template(system_template)
        human_prompt = HumanMessagePromptTemplate.from_template(human_template)
        
        return ChatPromptTemplate.from_messages([system_prompt, human_prompt])
    
    def _create_general_qa_template(self) -> ChatPromptTemplate:
        """일반 QA 템플릿"""
        system_template = """당신은 소프트웨어 개발 전문가입니다.
주어진 코드 컨텍스트를 바탕으로 질문에 답변해주세요.

답변 원칙:
1. 정확하고 구체적인 정보 제공
2. 관련 코드 예시 포함
3. 실용적인 조언 제공
4. 추가 학습 자료 제안

응답은 {language_preference}로 해주세요."""

        human_template = """관련 코드:

{code_context}

질문: {question}

위 코드를 참고하여 질문에 답변해주세요."""

        system_prompt = SystemMessagePromptTemplate.from_template(system_template)
        human_prompt = HumanMessagePromptTemplate.from_template(human_template)
        
        return ChatPromptTemplate.from_messages([system_prompt, human_prompt])
    
    def build_prompt(
        self,
        prompt_type: PromptType,
        context: CodeContext,
        question: str,
        **kwargs
    ) -> str:
        """프롬프트 빌드"""
        template = self.templates.get(prompt_type)
        if not template:
            raise ValueError(f"지원하지 않는 프롬프트 타입: {prompt_type}")
        
        # 기본 변수 설정
        variables = {
            "language": context.language,
            "code_content": self._truncate_content(context.code_content),
            "question": question,
            "language_preference": self.config.language_preference,
            "detail_level": self.config.detail_level,
        }
        
        # 메타데이터 섹션 생성
        if self.config.include_metadata:
            variables["metadata_section"] = self._build_metadata_section(context)
        else:
            variables["metadata_section"] = ""
        
        # 컨텍스트 섹션 생성
        variables["context_section"] = self._build_context_section(context)
        
        # 예시 포함 지시사항
        if self.config.include_examples:
            variables["examples_instruction"] = "5. 가능하면 간단한 사용 예시 포함"
            variables["related_code_instruction"] = "참고할 만한 관련 코드가 있다면 활용하세요."
        else:
            variables["examples_instruction"] = ""
            variables["related_code_instruction"] = ""
        
        # 관련 코드 섹션
        if context.related_code:
            variables["related_code_section"] = self._build_related_code_section(context.related_code)
        else:
            variables["related_code_section"] = ""
        
        # 추가 변수들 병합
        variables.update(kwargs)
        
        # 프롬프트 생성
        try:
            if isinstance(template, ChatPromptTemplate):
                messages = template.format_messages(**variables)
                return "\n".join([msg.content for msg in messages])
            else:
                return template.format(**variables)
        except KeyError as e:
            raise ValueError(f"프롬프트 변수 누락: {e}")
    
    def _truncate_content(self, content: str) -> str:
        """컨텐츠 길이 제한"""
        if len(content) <= self.config.max_context_length:
            return content
        
        # 중요한 부분을 유지하면서 자르기
        lines = content.split('\n')
        truncated_lines = []
        current_length = 0
        
        for line in lines:
            if current_length + len(line) > self.config.max_context_length:
                truncated_lines.append("... (코드가 길어서 일부 생략됨)")
                break
            truncated_lines.append(line)
            current_length += len(line) + 1  # +1 for newline
        
        return '\n'.join(truncated_lines)
    
    def _build_metadata_section(self, context: CodeContext) -> str:
        """메타데이터 섹션 빌드"""
        sections = []
        
        if context.file_path:
            sections.append(f"파일 경로: {context.file_path}")
        
        if context.function_name:
            sections.append(f"함수명: {context.function_name}")
        
        if context.class_name:
            sections.append(f"클래스명: {context.class_name}")
        
        if context.line_numbers:
            sections.append(f"라인 번호: {context.line_numbers}")
        
        if context.metadata:
            for key, value in context.metadata.items():
                if isinstance(value, (str, int, float)):
                    sections.append(f"{key}: {value}")
        
        return "\n".join(sections) if sections else ""
    
    def _build_context_section(self, context: CodeContext) -> str:
        """컨텍스트 섹션 빌드"""
        if not context.related_code:
            return ""
        
        return f"관련 코드 컨텍스트:\n{self._build_related_code_section(context.related_code)}"
    
    def _build_related_code_section(self, related_code: List[str]) -> str:
        """관련 코드 섹션 빌드"""
        if not related_code:
            return ""
        
        sections = []
        for i, code in enumerate(related_code[:3]):  # 최대 3개까지만
            sections.append(f"관련 코드 {i+1}:\n```\n{code}\n```")
        
        return "\n\n".join(sections)
    
    def get_template(self, prompt_type: PromptType) -> Optional[BasePromptTemplate]:
        """템플릿 조회"""
        return self.templates.get(prompt_type)
    
    def add_custom_template(self, prompt_type: PromptType, template: BasePromptTemplate):
        """커스텀 템플릿 추가"""
        self.templates[prompt_type] = template
    
    def list_available_types(self) -> List[PromptType]:
        """사용 가능한 프롬프트 타입 목록"""
        return list(self.templates.keys())
```

### 2. 프롬프트 서비스 관리자

```python
# app/llm/prompt_service.py
from typing import List, Dict, Any, Optional, Union
from .langchain_prompt import CodePromptBuilder, PromptType, CodeContext, PromptConfig
import logging

logger = logging.getLogger(__name__)

class PromptService:
    """프롬프트 서비스 관리자"""
    
    def __init__(self, config: PromptConfig = None):
        self.config = config or PromptConfig()
        self.prompt_builder = CodePromptBuilder(self.config)
        self._template_cache = {}
    
    async def create_code_explanation_prompt(
        self,
        code_content: str,
        language: str,
        question: str,
        context_data: Dict[str, Any] = None
    ) -> str:
        """코드 설명 프롬프트 생성"""
        context = self._build_code_context(
            code_content, language, context_data
        )
        
        return self.prompt_builder.build_prompt(
            PromptType.CODE_EXPLANATION,
            context,
            question
        )
    
    async def create_code_generation_prompt(
        self,
        requirements: str,
        language: str,
        related_code: List[str] = None,
        context_data: Dict[str, Any] = None
    ) -> str:
        """코드 생성 프롬프트 생성"""
        context = CodeContext(
            code_content="",  # 생성할 코드이므로 빈 문자열
            language=language,
            related_code=related_code or [],
            metadata=context_data or {}
        )
        
        return self.prompt_builder.build_prompt(
            PromptType.CODE_GENERATION,
            context,
            requirements,
            requirements=requirements
        )
    
    async def create_code_review_prompt(
        self,
        code_content: str,
        language: str,
        context_data: Dict[str, Any] = None
    ) -> str:
        """코드 리뷰 프롬프트 생성"""
        context = self._build_code_context(
            code_content, language, context_data
        )
        
        return self.prompt_builder.build_prompt(
            PromptType.CODE_REVIEW,
            context,
            "이 코드를 리뷰해주세요"
        )
    
    async def create_debugging_help_prompt(
        self,
        code_content: str,
        language: str,
        problem_description: str,
        error_info: str = None,
        context_data: Dict[str, Any] = None
    ) -> str:
        """디버깅 도움 프롬프트 생성"""
        context = self._build_code_context(
            code_content, language, context_data
        )
        
        return self.prompt_builder.build_prompt(
            PromptType.DEBUGGING_HELP,
            context,
            problem_description,
            problem_description=problem_description,
            error_info=f"오류 정보:\n{error_info}" if error_info else ""
        )
    
    async def create_general_qa_prompt(
        self,
        question: str,
        code_contexts: List[Dict[str, Any]],
        language: str = "java"
    ) -> str:
        """일반 QA 프롬프트 생성"""
        # 여러 코드 컨텍스트를 하나의 문자열로 결합
        code_context_str = self._build_multiple_code_contexts(code_contexts)
        
        context = CodeContext(
            code_content="",
            language=language,
            metadata={}
        )
        
        return self.prompt_builder.build_prompt(
            PromptType.GENERAL_QA,
            context,
            question,
            code_context=code_context_str
        )
    
    def _build_code_context(
        self,
        code_content: str,
        language: str,
        context_data: Dict[str, Any] = None
    ) -> CodeContext:
        """CodeContext 객체 생성"""
        context_data = context_data or {}
        
        return CodeContext(
            code_content=code_content,
            language=language,
            file_path=context_data.get('file_path'),
            function_name=context_data.get('function_name'),
            class_name=context_data.get('class_name'),
            line_numbers=context_data.get('line_numbers'),
            related_code=context_data.get('related_code', []),
            metadata=context_data.get('metadata', {})
        )
    
    def _build_multiple_code_contexts(
        self,
        code_contexts: List[Dict[str, Any]]
    ) -> str:
        """여러 코드 컨텍스트를 문자열로 결합"""
        context_parts = []
        
        for i, ctx in enumerate(code_contexts[:5]):  # 최대 5개까지
            code_content = ctx.get('content', '')
            file_path = ctx.get('file_path', f'코드 {i+1}')
            language = ctx.get('language', 'unknown')
            
            context_part = f"""
코드 {i+1} ({file_path}):
```{language}
{code_content}
```
"""
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    async def get_prompt_templates(self) -> Dict[str, str]:
        """사용 가능한 프롬프트 템플릿 목록"""
        templates = {}
        for prompt_type in self.prompt_builder.list_available_types():
            template = self.prompt_builder.get_template(prompt_type)
            if template:
                templates[prompt_type.value] = str(template)
        
        return templates
    
    async def update_config(self, new_config: Dict[str, Any]):
        """설정 업데이트"""
        # 새 설정으로 PromptConfig 생성
        current_config = self.config.dict()
        current_config.update(new_config)
        
        self.config = PromptConfig(**current_config)
        self.prompt_builder = CodePromptBuilder(self.config)
        
        logger.info(f"프롬프트 설정 업데이트: {new_config}")
    
    async def validate_prompt(self, prompt: str) -> Dict[str, Any]:
        """프롬프트 유효성 검사"""
        validation_result = {
            "is_valid": True,
            "length": len(prompt),
            "estimated_tokens": len(prompt.split()) * 1.3,  # 대략적인 토큰 수
            "warnings": []
        }
        
        # 길이 검사
        if len(prompt) > 10000:
            validation_result["warnings"].append("프롬프트가 너무 깁니다. 응답 품질이 저하될 수 있습니다.")
        
        # 필수 정보 포함 검사
        if "```" not in prompt:
            validation_result["warnings"].append("코드 블록이 포함되지 않았습니다.")
        
        # 질문 포함 검사
        if "?" not in prompt and "질문" not in prompt:
            validation_result["warnings"].append("명확한 질문이나 요청이 포함되지 않았습니다.")
        
        return validation_result
```

## ✅ 완료 조건

1. **PromptTemplate 구현**: LangChain 기반 프롬프트 시스템 완전 구현
2. **다양한 템플릿**: 코드 설명, 생성, 리뷰 등 다양한 시나리오 지원
3. **동적 컨텍스트**: 검색 결과 기반 동적 프롬프트 생성
4. **설정 관리**: 언어, 상세도 등 유연한 설정 관리
5. **유효성 검사**: 프롬프트 품질 검증 기능
6. **템플릿 확장**: 커스텀 템플릿 추가 지원
7. **기존 호환성**: 기존 프롬프트 로직과 호환

## 📋 다음 Task와의 연관관계

- **Task 14**: 이 PromptTemplate들을 LLMChain에서 활용
- **Task 15**: HybridRAG 서비스에서 프롬프트 서비스 통합

## 🧪 테스트 계획

```python
# tests/unit/llm/test_langchain_prompt.py
def test_prompt_builder_initialization():
    """프롬프트 빌더 초기화 테스트"""
    builder = CodePromptBuilder()
    assert len(builder.templates) > 0
    assert PromptType.CODE_EXPLANATION in builder.templates

async def test_code_explanation_prompt():
    """코드 설명 프롬프트 생성 테스트"""
    service = PromptService()
    prompt = await service.create_code_explanation_prompt(
        "public void test() {}", "java", "이 메서드가 하는 일을 설명해주세요"
    )
    assert "java" in prompt
    assert "설명해주세요" in prompt

def test_context_truncation():
    """컨텍스트 길이 제한 테스트"""
    config = PromptConfig(max_context_length=100)
    builder = CodePromptBuilder(config)
    long_content = "x" * 200
    truncated = builder._truncate_content(long_content)
    assert len(truncated) <= 150  # 여유있게 확인
```

이 Task는 LLM과의 효과적인 상호작용을 위한 핵심 구성요소입니다. 잘 설계된 프롬프트를 통해 검색된 코드에 대한 고품질 응답을 생성할 수 있습니다. 