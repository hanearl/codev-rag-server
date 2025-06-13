class IndexError(Exception):
    """인덱스 기본 예외"""
    pass

class IndexBuildError(IndexError):
    """인덱스 빌드 예외"""
    pass

class IndexQueryError(IndexError):
    """인덱스 쿼리 예외"""
    pass

class IndexUpdateError(IndexError):
    """인덱스 업데이트 예외"""
    pass 