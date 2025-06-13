class RetrieverError(Exception):
    """리트리버 기본 예외"""
    pass

class RetrieverSetupError(RetrieverError):
    """리트리버 설정 예외"""
    pass

class RetrieverQueryError(RetrieverError):
    """리트리버 쿼리 예외"""
    pass

class RetrieverConnectionError(RetrieverError):
    """리트리버 연결 예외"""
    pass 