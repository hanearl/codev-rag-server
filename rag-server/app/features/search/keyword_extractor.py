import re
import logging
from typing import List, Set

logger = logging.getLogger(__name__)

class QueryKeywordExtractor:
    """쿼리에서 키워드를 자동 추출하는 클래스"""
    
    def __init__(self):
        # NLTK 사용 가능 여부 확인
        self.nltk_available = False
        try:
            from nltk.corpus import stopwords
            from nltk.tokenize import word_tokenize
            from nltk.stem import PorterStemmer
            self.stop_words = set(stopwords.words('english'))
            self.stemmer = PorterStemmer()
            self.word_tokenize = word_tokenize
            self.nltk_available = True
        except (ImportError, LookupError):
            # NLTK 없거나 데이터 없으면 기본 불용어 사용
            self.stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
                'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 
                'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 
                'would', 'could', 'should', 'can', 'may', 'might', 'must',
                'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
                'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
            }
        
        # 프로그래밍 관련 키워드
        self.programming_keywords = {
            'function', 'method', 'class', 'interface', 'variable', 'parameter',
            'return', 'type', 'string', 'int', 'boolean', 'array', 'list',
            'api', 'endpoint', 'controller', 'service', 'repository', 'model',
            'database', 'query', 'search', 'create', 'update', 'delete',
            'get', 'post', 'put', 'patch', 'async', 'await', 'promise',
            'exception', 'error', 'try', 'catch', 'throw', 'handle',
            'process', 'data', 'response', 'request', 'json', 'xml'
        }
    
    def extract_keywords(self, query: str, min_length: int = 2) -> List[str]:
        """쿼리에서 의미있는 키워드 추출"""
        try:
            keywords = set()
            
            # 1. 기본 토큰화 및 정제
            basic_keywords = self._extract_basic_keywords(query, min_length)
            keywords.update(basic_keywords)
            
            # 2. 프로그래밍 용어 추출
            programming_keywords = self._extract_programming_keywords(query)
            keywords.update(programming_keywords)
            
            # 3. CamelCase, snake_case 분해
            compound_keywords = self._extract_compound_keywords(query)
            keywords.update(compound_keywords)
            
            return list(keywords)
            
        except Exception as e:
            logger.error(f"키워드 추출 실패: {e}")
            return self._fallback_extraction(query)
    
    def _extract_basic_keywords(self, query: str, min_length: int) -> Set[str]:
        """기본적인 키워드 추출"""
        keywords = set()
        
        # 소문자 변환 및 토큰화
        if self.nltk_available:
            try:
                tokens = self.word_tokenize(query.lower())
            except:
                tokens = re.findall(r'\b\w+\b', query.lower())
        else:
            # NLTK 없을 경우 정규식 사용
            tokens = re.findall(r'\b\w+\b', query.lower())
        
        for token in tokens:
            # 조건 필터링
            if (len(token) >= min_length and 
                token not in self.stop_words and 
                token.isalpha()):
                keywords.add(token)
        
        return keywords
    
    def _extract_programming_keywords(self, query: str) -> Set[str]:
        """프로그래밍 관련 키워드 추출"""
        keywords = set()
        query_lower = query.lower()
        
        for keyword in self.programming_keywords:
            if keyword in query_lower:
                keywords.add(keyword)
        
        return keywords
    
    def _extract_compound_keywords(self, query: str) -> Set[str]:
        """복합 키워드 분해 (CamelCase, snake_case)"""
        keywords = set()
        
        # CamelCase 분해: getUserById -> get, user, by, id
        camel_pattern = r'([a-z])([A-Z])'
        camel_split = re.sub(camel_pattern, r'\1 \2', query)
        
        # snake_case 분해: get_user_by_id -> get, user, by, id
        snake_split = camel_split.replace('_', ' ')
        
        # 분해된 단어들 추출
        words = re.findall(r'\b\w+\b', snake_split.lower())
        for word in words:
            if len(word) >= 2 and word not in self.stop_words:
                keywords.add(word)
        
        return keywords
    
    def _fallback_extraction(self, query: str) -> List[str]:
        """NLTK 없을 경우 fallback 추출"""
        # 단순 정규식 기반 추출
        words = re.findall(r'\b\w{2,}\b', query.lower())
        
        # 기본 불용어 제거
        basic_stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        
        return [word for word in words if word not in basic_stopwords]

# 전역 인스턴스
keyword_extractor = QueryKeywordExtractor() 