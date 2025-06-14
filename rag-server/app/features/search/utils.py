"""
검색 관련 유틸리티 함수들
"""
import re
from typing import Optional, Dict, Any


def extract_java_package_name(content: str) -> Optional[str]:
    """
    Java 파일 내용에서 패키지명을 추출합니다.
    
    Args:
        content: Java 파일 내용
        
    Returns:
        패키지명 (없으면 None)
    """
    if not content:
        return None
    
    # package 선언을 찾는 정규식
    # 주석이나 문자열 안의 package는 제외하고 실제 package 선언만 찾음
    package_pattern = r'^\s*package\s+([a-zA-Z_$][a-zA-Z0-9_$]*(?:\.[a-zA-Z_$][a-zA-Z0-9_$]*)*)\s*;'
    
    # 여러 줄에 걸친 내용에서 package 선언 찾기
    lines = content.split('\n')
    for line in lines:
        # 주석 제거 (// 스타일)
        if '//' in line:
            line = line[:line.index('//')]
        
        # 블록 주석 안의 내용은 일단 단순하게 처리
        # 더 정교한 처리가 필요하면 나중에 개선
        match = re.search(package_pattern, line, re.MULTILINE)
        if match:
            return match.group(1)
    
    return None


def extract_java_class_name(content: str, file_path: str = None) -> Optional[str]:
    """
    Java 파일에서 클래스명을 추출합니다.
    
    Args:
        content: Java 파일 내용
        file_path: 파일 경로 (없으면 content에서만 추출)
        
    Returns:
        클래스명 (없으면 None)
    """
    # 내용이 있으면 먼저 내용에서 클래스명 추출 시도
    if content:
        # public class, class, interface, enum 등을 찾는 정규식
        class_patterns = [
            r'public\s+class\s+([A-Za-z_$][A-Za-z0-9_$]*)',
            r'class\s+([A-Za-z_$][A-Za-z0-9_$]*)',
            r'public\s+interface\s+([A-Za-z_$][A-Za-z0-9_$]*)',
            r'interface\s+([A-Za-z_$][A-Za-z0-9_$]*)',
            r'public\s+enum\s+([A-Za-z_$][A-Za-z0-9_$]*)',
            r'enum\s+([A-Za-z_$][A-Za-z0-9_$]*)'
        ]
        
        lines = content.split('\n')
        for line in lines:
            # 주석 제거
            if '//' in line:
                line = line[:line.index('//')]
            
            for pattern in class_patterns:
                match = re.search(pattern, line)
                if match:
                    return match.group(1)
    
    # 내용에서 찾지 못했거나 내용이 없으면 파일 경로에서 클래스명 추출
    if file_path:
        import os
        filename = os.path.basename(file_path)
        if filename.endswith('.java'):
            return filename[:-5]  # .java 제거
    
    return None


def enhance_metadata_for_java(metadata: Dict[str, Any], content: str) -> Dict[str, Any]:
    """
    Java 파일의 메타데이터를 향상시킵니다.
    
    Args:
        metadata: 기존 메타데이터
        content: 파일 내용
        
    Returns:
        향상된 메타데이터
    """
    enhanced_metadata = metadata.copy()
    
    # type이 java인 경우에만 처리
    if metadata.get('type') == 'java' or metadata.get('language') == 'java':
        # 패키지명 추출
        package_name = extract_java_package_name(content)
        if package_name:
            enhanced_metadata['package'] = package_name
        
        # 클래스명 추출
        class_name = extract_java_class_name(content, metadata.get('file_path'))
        if class_name:
            enhanced_metadata['class_name'] = class_name
        
        # 전체 클래스 경로 (패키지 + 클래스명)
        if package_name and class_name:
            enhanced_metadata['full_class_name'] = f"{package_name}.{class_name}"
    
    return enhanced_metadata 