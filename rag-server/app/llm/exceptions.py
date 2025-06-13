class LLMError(Exception):
    """LLM 기본 예외"""
    pass

class LLMConfigError(LLMError):
    """LLM 설정 예외"""
    pass

class LLMProcessingError(LLMError):
    """LLM 처리 예외"""
    pass

class LLMConnectionError(LLMError):
    """LLM 연결 예외"""
    pass 