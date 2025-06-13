import numpy as np
import platform
import psutil
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EvaluationStatistics:
    """평가 통계 계산 클래스"""
    
    @staticmethod
    def calculate_response_time_stats(response_times: List[float]) -> Dict[str, float]:
        """
        응답 시간 통계 계산
        
        Args:
            response_times: 응답 시간 리스트 (초 단위)
            
        Returns:
            통계 정보 딕셔너리 (평균, 중앙값, 표준편차, 최소/최대값)
        """
        if not response_times:
            return {
                'average': 0.0,
                'median': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0
            }
        
        times_array = np.array(response_times)
        
        return {
            'average': float(np.mean(times_array)),
            'median': float(np.median(times_array)),
            'std': float(np.std(times_array)),
            'min': float(np.min(times_array)),
            'max': float(np.max(times_array))
        }
    
    @staticmethod
    def collect_environment_info() -> Dict[str, Any]:
        """
        실행 환경 정보 수집
        
        Returns:
            환경 정보 딕셔너리
        """
        try:
            memory_info = psutil.virtual_memory()
            memory_gb = round(memory_info.total / (1024**3), 2)
            
            return {
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_gb': memory_gb,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.warning(f"환경 정보 수집 중 오류: {str(e)}")
            return {
                'platform': 'unknown',
                'python_version': 'unknown',
                'cpu_count': 0,
                'memory_gb': 0.0,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def calculate_percentiles(
        data: List[float], 
        percentiles: List[int] = [25, 50, 75, 90, 95]
    ) -> Dict[int, float]:
        """
        백분위수 계산
        
        Args:
            data: 수치 데이터 리스트
            percentiles: 계산할 백분위수 리스트
            
        Returns:
            백분위수별 값 딕셔너리
        """
        if not data:
            return {}
        
        data_array = np.array(data)
        result = {}
        
        for p in percentiles:
            result[p] = float(np.percentile(data_array, p))
        
        return result
    
    @staticmethod
    def calculate_error_rate(failed_queries: int, total_queries: int) -> float:
        """
        에러율 계산
        
        Args:
            failed_queries: 실패한 쿼리 수
            total_queries: 총 쿼리 수
            
        Returns:
            에러율 (백분율)
        """
        if total_queries == 0:
            return 0.0
        
        return (failed_queries / total_queries) * 100.0
    
    @staticmethod
    def aggregate_metrics(metrics: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """
        메트릭별 요약 통계 계산
        
        Args:
            metrics: 메트릭별 k값별 점수 딕셔너리
            
        Returns:
            메트릭별 통계 정보 (평균, 최소, 최대, 표준편차)
        """
        result = {}
        
        for metric_name, k_values in metrics.items():
            if not k_values:
                continue
                
            values = list(k_values.values())
            values_array = np.array(values)
            
            result[metric_name] = {
                'mean': float(np.mean(values_array)),
                'min': float(np.min(values_array)),
                'max': float(np.max(values_array)),
                'std': float(np.std(values_array)),
                'count': len(values)
            }
        
        return result
    
    @staticmethod
    def calculate_throughput(total_queries: int, execution_time: float) -> float:
        """
        처리량 계산 (초당 쿼리 수)
        
        Args:
            total_queries: 총 쿼리 수
            execution_time: 총 실행 시간 (초)
            
        Returns:
            처리량 (queries per second)
        """
        if execution_time <= 0:
            return 0.0
        
        return total_queries / execution_time
    
    @staticmethod
    def calculate_trend_analysis(
        current_metrics: Dict[str, Dict[str, float]], 
        previous_metrics: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict[str, float]]:
        """
        트렌드 분석 (이전 결과와 비교)
        
        Args:
            current_metrics: 현재 메트릭
            previous_metrics: 이전 메트릭
            
        Returns:
            메트릭별 변화율
        """
        trends = {}
        
        for metric_name in current_metrics.keys():
            if metric_name not in previous_metrics:
                continue
                
            trends[metric_name] = {}
            current_k_values = current_metrics[metric_name]
            previous_k_values = previous_metrics[metric_name]
            
            for k in current_k_values.keys():
                if k in previous_k_values:
                    current_val = current_k_values[k]
                    previous_val = previous_k_values[k]
                    
                    if previous_val != 0:
                        change_rate = ((current_val - previous_val) / previous_val) * 100
                    else:
                        change_rate = 0.0 if current_val == 0 else 100.0
                        
                    trends[metric_name][k] = change_rate
        
        return trends
    
    @classmethod
    def generate_evaluation_summary(
        cls,
        metrics: Dict[str, Dict[str, float]],
        response_times: List[float],
        total_queries: int,
        failed_queries: int,
        execution_time: float
    ) -> Dict[str, Any]:
        """
        종합 평가 요약 생성
        
        Args:
            metrics: 평가 메트릭
            response_times: 응답 시간 리스트
            total_queries: 총 쿼리 수
            failed_queries: 실패 쿼리 수
            execution_time: 총 실행 시간
            
        Returns:
            종합 요약 정보
        """
        # 기본 통계
        response_stats = cls.calculate_response_time_stats(response_times)
        metrics_summary = cls.aggregate_metrics(metrics)
        error_rate = cls.calculate_error_rate(failed_queries, total_queries)
        throughput = cls.calculate_throughput(total_queries, execution_time)
        environment_info = cls.collect_environment_info()
        
        # 백분위수 계산
        response_percentiles = cls.calculate_percentiles(response_times) if response_times else {}
        
        return {
            'metrics_summary': metrics_summary,
            'response_time_stats': response_stats,
            'response_time_percentiles': response_percentiles,
            'error_rate': error_rate,
            'throughput': throughput,
            'total_queries': total_queries,
            'failed_queries': failed_queries,
            'execution_time': execution_time,
            'environment_info': environment_info
        } 