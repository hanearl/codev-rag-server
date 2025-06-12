import math
import logging
from typing import List, Dict, Set
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

class BM25KeywordScorer:
    """BM25 알고리즘을 사용한 키워드 유사도 스코어러"""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        BM25 매개변수 초기화
        
        Args:
            k1: 단어 빈도 포화 매개변수 (1.2-2.0 권장)
            b: 문서 길이 정규화 매개변수 (0.75 권장)
        """
        self.k1 = k1
        self.b = b
        
        # 문서 컬렉션 통계
        self.documents: List[List[str]] = []
        self.doc_freqs: List[Counter] = []
        self.idf: Dict[str, float] = {}
        self.avg_doc_len: float = 0.0
        self.num_docs: int = 0
        
    def fit(self, documents: List[List[str]]) -> None:
        """문서 컬렉션으로 BM25 모델 학습"""
        self.documents = documents
        self.num_docs = len(documents)
        
        if self.num_docs == 0:
            return
            
        # 각 문서의 단어 빈도 계산
        self.doc_freqs = [Counter(doc) for doc in documents]
        
        # 평균 문서 길이 계산
        total_len = sum(len(doc) for doc in documents)
        self.avg_doc_len = total_len / self.num_docs
        
        # IDF 계산
        self._calculate_idf()
        
        logger.info(f"BM25 모델 학습 완료: {self.num_docs}개 문서, 평균 길이: {self.avg_doc_len:.2f}")
    
    def _calculate_idf(self) -> None:
        """역문서 빈도(IDF) 계산"""
        # 모든 고유 단어 수집
        all_words: Set[str] = set()
        for doc in self.documents:
            all_words.update(doc)
        
        # 각 단어가 나타나는 문서 수 계산
        word_doc_count = defaultdict(int)
        for doc in self.documents:
            unique_words = set(doc)
            for word in unique_words:
                word_doc_count[word] += 1
        
        # IDF 계산: log((N - df + 0.5) / (df + 0.5))
        self.idf = {}
        for word in all_words:
            df = word_doc_count[word]  # 단어가 포함된 문서 수
            idf_value = math.log((self.num_docs - df + 0.5) / (df + 0.5))
            self.idf[word] = max(idf_value, 0.01)  # 최소값 보장
    
    def score(self, query: List[str], doc_index: int) -> float:
        """쿼리와 문서 간 BM25 점수 계산"""
        if not query or doc_index >= len(self.documents):
            return 0.0
        
        doc = self.documents[doc_index]
        doc_freq = self.doc_freqs[doc_index]
        doc_len = len(doc)
        
        score = 0.0
        
        for term in query:
            if term not in self.idf:
                continue  # 모르는 단어는 무시
                
            # 단어 빈도 (TF)
            tf = doc_freq.get(term, 0)
            
            if tf == 0:
                continue  # 문서에 없는 단어
            
            # BM25 점수 계산
            idf = self.idf[term]
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
            
            term_score = idf * (numerator / denominator)
            score += term_score
        
        return score
    
    def get_scores(self, query: List[str]) -> List[float]:
        """모든 문서에 대한 BM25 점수 계산"""
        return [self.score(query, i) for i in range(len(self.documents))]
    
    def get_top_k(self, query: List[str], k: int = 10) -> List[tuple]:
        """상위 k개 문서 반환 (doc_index, score)"""
        scores = self.get_scores(query)
        indexed_scores = [(i, score) for i, score in enumerate(scores)]
        
        # 점수 기준 내림차순 정렬
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        return indexed_scores[:k]
    
    def normalize_scores(self, scores: List[float]) -> List[float]:
        """점수를 0-1 범위로 정규화 (기본 방식 - 하위 호환성)"""
        return self.adaptive_normalize(scores)
    
    def normalize_scores_improved(self, scores: List[float]) -> List[float]:
        """개선된 정규화 - 절대적 품질 반영"""
        return self.adaptive_normalize(scores)
    
    def sigmoid_normalize(self, scores: List[float], scale: float = 2.0) -> List[float]:
        """시그모이드 함수를 사용한 정규화"""
        if not scores:
            return scores
            
        # 시그모이드 함수: 1 / (1 + exp(-scale * x))
        normalized = []
        for score in scores:
            sigmoid_score = 1 / (1 + math.exp(-scale * score))
            normalized.append(sigmoid_score)
        
        return normalized
    
    def percentile_normalize(self, scores: List[float], 
                           percentile_95: float = None) -> List[float]:
        """백분위 기반 정규화"""
        if not scores:
            return scores
            
        # 95 백분위를 1.0으로 설정
        if percentile_95 is None:
            sorted_scores = sorted(scores)
            idx_95 = int(len(sorted_scores) * 0.95)
            percentile_95 = sorted_scores[min(idx_95, len(sorted_scores) - 1)]
        
        if percentile_95 == 0:
            return [0.0] * len(scores)
            
        # 95 백분위로 나누고 1.0으로 클리핑
        normalized = [min(score / percentile_95, 1.0) for score in scores]
        return normalized
    
    def adaptive_normalize(self, scores: List[float]) -> List[float]:
        """적응형 정규화 - 절대적 품질 기반 정규화"""
        if not scores:
            return scores
            
        # 모든 점수가 0인 경우
        if all(score == 0 for score in scores):
            return scores
            
        # 절대적 품질 기반 정규화
        return self._quality_based_normalize(scores)
    
    def _quality_based_normalize(self, scores: List[float]) -> List[float]:
        """품질 기반 정규화 - BM25 점수의 절대적 의미 반영"""
        if not scores:
            return scores
            
        # BM25 점수 품질 임계값 정의
        EXCELLENT_THRESHOLD = 5.0    # 매우 좋은 매칭
        GOOD_THRESHOLD = 2.0         # 좋은 매칭  
        FAIR_THRESHOLD = 0.5         # 보통 매칭
        POOR_THRESHOLD = 0.1         # 낮은 매칭
        
        normalized = []
        for score in scores:
            if score >= EXCELLENT_THRESHOLD:
                # 매우 좋은 매칭: 0.9-1.0
                norm_score = 0.9 + min(0.1, (score - EXCELLENT_THRESHOLD) / 10.0)
            elif score >= GOOD_THRESHOLD:
                # 좋은 매칭: 0.7-0.9
                norm_score = 0.7 + 0.2 * (score - GOOD_THRESHOLD) / (EXCELLENT_THRESHOLD - GOOD_THRESHOLD)
            elif score >= FAIR_THRESHOLD:
                # 보통 매칭: 0.4-0.7
                norm_score = 0.4 + 0.3 * (score - FAIR_THRESHOLD) / (GOOD_THRESHOLD - FAIR_THRESHOLD)
            elif score >= POOR_THRESHOLD:
                # 낮은 매칭: 0.1-0.4
                norm_score = 0.1 + 0.3 * (score - POOR_THRESHOLD) / (FAIR_THRESHOLD - POOR_THRESHOLD)
            elif score > 0:
                # 매우 낮은 매칭: 0.01-0.1
                norm_score = 0.01 + 0.09 * score / POOR_THRESHOLD
            else:
                # 매칭 없음: 0.0
                norm_score = 0.0
                
            normalized.append(norm_score)
        
        return normalized
    
    def _log_scale_normalize(self, scores: List[float]) -> List[float]:
        """로그 스케일 정규화 - 매우 낮은 점수 범위용"""
        if not scores:
            return scores
            
        # 로그 변환 후 정규화
        log_scores = []
        for score in scores:
            if score > 0:
                log_score = math.log(1 + score * 100)  # 스케일 조정
                log_scores.append(log_score)
            else:
                log_scores.append(0.0)
        
        if not log_scores or max(log_scores) == 0:
            return [0.0] * len(scores)
            
        max_log = max(log_scores)
        return [score / max_log for score in log_scores]
    
    def _sqrt_normalize(self, scores: List[float]) -> List[float]:
        """제곱근 정규화 - 낮은 점수 범위의 차이 강조"""
        if not scores:
            return scores
            
        sqrt_scores = [math.sqrt(score) if score > 0 else 0.0 for score in scores]
        max_sqrt = max(sqrt_scores) if sqrt_scores else 0
        
        if max_sqrt == 0:
            return [0.0] * len(scores)
            
        return [score / max_sqrt for score in sqrt_scores]
    
    def _linear_normalize_improved(self, scores: List[float]) -> List[float]:
        """개선된 선형 정규화 - 1.0 만점 방지"""
        if not scores:
            return scores
            
        max_score = max(scores)
        if max_score == 0:
            return scores
            
        # 최대값의 90%를 1.0으로 설정하여 완벽한 매칭이 아니면 1.0이 안되도록 함
        threshold = max_score * 0.9
        normalized = [min(score / threshold, 1.0) for score in scores]
        
        return normalized 