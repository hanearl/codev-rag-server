import re
import os
from typing import List, Set, Optional
from pathlib import Path


class ClasspathConverter:
    """Java 파일 경로를 클래스패스로 변환하는 유틸리티"""
    
    def __init__(self, source_roots: List[str] = None):
        """
        Args:
            source_roots: Java 소스 루트 경로들 (예: ["src/main/java", "src/test/java"])
        """
        self.source_roots = source_roots or ["src/main/java", "src/test/java"]
    
    def filepath_to_classpath(self, filepath: str) -> Optional[str]:
        """
        파일 경로를 Java 클래스패스로 변환
        
        Args:
            filepath: 파일 경로 (예: "src/main/java/com/skax/library/controller/BookController.java")
            
        Returns:
            클래스패스 (예: "com.skax.library.controller.BookController") 또는 None
        """
        if not filepath:
            return None
            
        # 경로 정규화
        normalized_path = filepath.replace("\\", "/")
        
        # .java 확장자 제거
        if normalized_path.endswith(".java"):
            normalized_path = normalized_path[:-5]
        
        # 소스 루트에서 클래스패스 추출
        for source_root in self.source_roots:
            source_pattern = f"{source_root}/"
            if source_pattern in normalized_path:
                # 소스 루트 이후 경로 추출
                classpath_part = normalized_path.split(source_pattern)[-1]
                # 슬래시를 점으로 변환
                classpath = classpath_part.replace("/", ".")
                return classpath
        
        # 소스 루트가 없는 경우, 파일명에서 패키지 구조 추정
        path_parts = normalized_path.split("/")
        
        # com, org 등으로 시작하는 부분 찾기
        for i, part in enumerate(path_parts):
            if part in ["com", "org", "net", "java", "javax"]:
                classpath_parts = path_parts[i:]
                return ".".join(classpath_parts)
        
        # 마지막 방법: 파일명만 사용
        return path_parts[-1] if path_parts else None
    
    def extract_class_from_classpath(self, classpath: str, ignore_method: bool = True) -> str:
        """
        클래스패스에서 클래스 부분만 추출 (메서드명 제거)
        
        Args:
            classpath: 클래스패스 (예: "com.skax.library.service.impl.BookServiceImpl.createBook")
            ignore_method: 메서드명 무시 여부
            
        Returns:
            클래스 부분 (예: "com.skax.library.service.impl.BookServiceImpl")
        """
        if not classpath:
            return ""
            
        if not ignore_method:
            return classpath
        
        # 메서드명 패턴 감지 (일반적으로 소문자로 시작)
        parts = classpath.split(".")
        
        # 마지막 부분이 소문자로 시작하면 메서드명으로 간주
        if len(parts) > 1 and parts[-1] and parts[-1][0].islower():
            return ".".join(parts[:-1])
            
        return classpath
    
    def normalize_classpath(self, classpath: str, case_sensitive: bool = False) -> str:
        """
        클래스패스 정규화
        
        Args:
            classpath: 클래스패스
            case_sensitive: 대소문자 구분 여부
            
        Returns:
            정규화된 클래스패스
        """
        if not classpath:
            return ""
            
        normalized = classpath.strip()
        
        if not case_sensitive:
            normalized = normalized.lower()
            
        return normalized


class ClasspathMatcher:
    """클래스패스 매칭 유틸리티"""
    
    def __init__(self, converter: ClasspathConverter):
        self.converter = converter
    
    def match_classpaths(
        self, 
        expected: List[str], 
        retrieved_filepaths: List[str],
        ignore_method_names: bool = True,
        case_sensitive: bool = False,
        convert_filepath: bool = True
    ) -> List[bool]:
        """
        기대 클래스패스와 검색된 파일패스들을 매칭
        
        Args:
            expected: 기대하는 클래스패스들
            retrieved_filepaths: 검색된 파일패스들
            ignore_method_names: 메서드명 무시 여부
            case_sensitive: 대소문자 구분 여부
            convert_filepath: 파일패스를 클래스패스로 변환할지 여부
            
        Returns:
            각 검색 결과의 매칭 여부 리스트
        """
        # 기대 클래스패스 정규화
        normalized_expected = set()
        for exp in expected:
            normalized = self.converter.extract_class_from_classpath(exp, ignore_method_names)
            normalized = self.converter.normalize_classpath(normalized, case_sensitive)
            if normalized:
                normalized_expected.add(normalized)
        
        # 검색 결과 매칭 확인
        matches = []
        for filepath in retrieved_filepaths:
            if convert_filepath:
                # 파일패스를 클래스패스로 변환
                classpath = self.converter.filepath_to_classpath(filepath)
            else:
                # 이미 클래스패스라고 가정
                classpath = filepath
            
            if classpath:
                # 클래스패스 정규화
                normalized_classpath = self.converter.extract_class_from_classpath(
                    classpath, ignore_method_names
                )
                normalized_classpath = self.converter.normalize_classpath(
                    normalized_classpath, case_sensitive
                )
                
                # 매칭 확인
                is_match = normalized_classpath in normalized_expected
                matches.append(is_match)
            else:
                matches.append(False)
        
        return matches
    
    def calculate_metrics_at_k(
        self, 
        expected: List[str], 
        retrieved_filepaths: List[str],
        k_values: List[int],
        ignore_method_names: bool = True,
        case_sensitive: bool = False,
        convert_filepath: bool = True
    ) -> dict:
        """
        k값별 메트릭 계산
        
        Args:
            expected: 기대하는 클래스패스들
            retrieved_filepaths: 검색된 파일패스들 (순서대로)
            k_values: 계산할 k 값들
            ignore_method_names: 메서드명 무시 여부
            case_sensitive: 대소문자 구분 여부
            convert_filepath: 파일패스를 클래스패스로 변환할지 여부
            
        Returns:
            메트릭 결과 딕셔너리
        """
        matches = self.match_classpaths(
            expected, retrieved_filepaths, ignore_method_names, case_sensitive, convert_filepath
        )
        
        results = {
            "matches": matches,
            "recall_at_k": {},
            "precision_at_k": {},
            "hit_at_k": {},
            "reciprocal_rank": 0.0
        }
        
        # 각 k에 대해 메트릭 계산
        for k in k_values:
            if k > len(matches):
                k_actual = len(matches)
            else:
                k_actual = k
            
            if k_actual == 0:
                results["recall_at_k"][k] = 0.0
                results["precision_at_k"][k] = 0.0
                results["hit_at_k"][k] = 0.0
                continue
            
            # 상위 k개에서 매칭된 수
            matches_at_k = sum(matches[:k_actual])
            
            # Recall@k = 찾은 관련 문서 수 / 전체 관련 문서 수
            results["recall_at_k"][k] = matches_at_k / len(expected)
            
            # Precision@k = 찾은 관련 문서 수 / k
            results["precision_at_k"][k] = matches_at_k / k_actual
            
            # Hit@k = 상위 k개에 관련 문서가 하나라도 있으면 1, 없으면 0
            results["hit_at_k"][k] = 1.0 if matches_at_k > 0 else 0.0
        
        # Reciprocal Rank 계산 (첫 번째 매칭의 역순위)
        for i, match in enumerate(matches):
            if match:
                results["reciprocal_rank"] = 1.0 / (i + 1)
                break
        
        return results


def create_default_classpath_converter() -> ClasspathConverter:
    """기본 클래스패스 변환기 생성"""
    return ClasspathConverter([
        "src/main/java",
        "src/test/java", 
        "main/java",
        "test/java",
        "java"
    ])


def create_default_classpath_matcher() -> ClasspathMatcher:
    """기본 클래스패스 매처 생성"""
    return ClasspathMatcher(create_default_classpath_converter()) 