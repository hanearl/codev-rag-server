class HybridRAGError(Exception):
    """하이브리드 RAG 기본 예외"""
    pass

class HybridRAGConfigError(HybridRAGError):
    """하이브리드 RAG 설정 예외"""
    pass

class HybridRAGProcessingError(HybridRAGError):
    """하이브리드 RAG 처리 예외"""
    pass

class HybridRAGSearchError(HybridRAGError):
    """하이브리드 RAG 검색 예외"""
    pass 