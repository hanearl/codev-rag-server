"""키워드 추출기

Java/Spring 코드에서 의미있는 키워드를 추출하는 기능을 제공합니다.
"""

import re
from typing import List, Set


class KeywordExtractor:
    """키워드 추출기
    
    Java 클래스명, 메소드명, 주석, 어노테이션에서 의미있는 키워드를 추출합니다.
    """
    
    def __init__(self, max_keywords: int = 20):
        """키워드 추출기 초기화
        
        Args:
            max_keywords: 최대 키워드 개수
        """
        self.max_keywords = max_keywords
        self.stop_words = {
            # 영어 불용어
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can',
            'this', 'that', 'these', 'those', 'me', 'him', 'her', 'us', 'them',
            # Java 키워드
            'public', 'private', 'protected', 'static', 'final', 'abstract',
            'class', 'interface', 'enum', 'extends', 'implements', 'package',
            'import', 'return', 'void', 'null', 'true', 'false', 'new',
            'try', 'catch', 'finally', 'throw', 'throws', 'synchronized',
            'volatile', 'transient', 'native', 'strictfp', 'super', 'this',
            'if', 'else', 'while', 'for', 'do', 'switch', 'case', 'default',
            'break', 'continue', 'instanceof', 'assert',
            # Java 기본 타입
            'int', 'long', 'short', 'byte', 'char', 'float', 'double', 'boolean',
            'string', 'object', 'list', 'map', 'set', 'array'
        }
        
        # Spring 관련 중요 키워드 (불용어에서 제외)
        self.spring_keywords = {
            'controller', 'service', 'repository', 'component', 'autowired',
            'bean', 'configuration', 'entity', 'rest', 'api', 'mapping',
            'request', 'response', 'path', 'param', 'body', 'transaction',
            'validation', 'security', 'jpa', 'hibernate', 'database'
        }
    
    def extract_from_name(self, name: str) -> List[str]:
        """Java 클래스명/메소드명에서 키워드 추출
        
        Args:
            name: Java 클래스 또는 메소드명
            
        Returns:
            추출된 키워드 리스트
        """
        keywords = set()
        
        # camelCase 분리: getUserProfile -> get, user, profile
        camel_parts = re.findall(r'[A-Z][a-z]*|[a-z]+', name)
        keywords.update([part.lower() for part in camel_parts if len(part) > 2])
        
        # PascalCase 분리: UserController -> user, controller
        pascal_parts = re.findall(r'[A-Z][a-z]*', name)
        keywords.update([part.lower() for part in pascal_parts if len(part) > 2])
        
        # Spring 키워드는 보존
        filtered_keywords = [
            keyword for keyword in keywords 
            if keyword not in self.stop_words or keyword in self.spring_keywords
        ]
        
        return sorted(filtered_keywords)[:self.max_keywords]
    
    def extract_from_annotations(self, annotations: List[str]) -> List[str]:
        """Java/Spring 어노테이션에서 키워드 추출
        
        Args:
            annotations: 어노테이션 리스트 (예: ["@Controller", "@RequestMapping"])
            
        Returns:
            추출된 키워드 리스트
        """
        keywords = set()
        
        for annotation in annotations:
            # @ 제거
            clean_annotation = annotation.lstrip('@')
            
            # camelCase 분리
            parts = re.findall(r'[A-Z][a-z]*|[a-z]+', clean_annotation)
            keywords.update([part.lower() for part in parts if len(part) > 2])
            
            # Spring 특별 매핑
            spring_mappings = {
                'restcontroller': ['rest', 'controller', 'api'],
                'requestmapping': ['request', 'mapping', 'endpoint'],
                'getmapping': ['get', 'mapping', 'endpoint'],
                'postmapping': ['post', 'mapping', 'endpoint'],
                'putmapping': ['put', 'mapping', 'endpoint'],
                'deletemapping': ['delete', 'mapping', 'endpoint'],
                'pathvariable': ['path', 'variable', 'parameter'],
                'requestparam': ['request', 'parameter'],
                'requestbody': ['request', 'body'],
                'responsebody': ['response', 'body'],
                'autowired': ['dependency', 'injection'],
                'transactional': ['transaction', 'database']
            }
            
            clean_lower = clean_annotation.lower()
            if clean_lower in spring_mappings:
                keywords.update(spring_mappings[clean_lower])
        
        return sorted(list(keywords))[:self.max_keywords]
    
    def extract_from_javadoc(self, javadoc: str) -> List[str]:
        """Javadoc에서 키워드 추출
        
        Args:
            javadoc: Javadoc 주석 내용
            
        Returns:
            추출된 키워드 리스트
        """
        keywords = set()
        
        # @param 태그에서 파라미터명 추출
        param_matches = re.findall(r'@param\s+(\w+)', javadoc)
        for param in param_matches:
            # camelCase 분리하여 키워드 추출
            name_keywords = self.extract_from_name(param)
            keywords.update(name_keywords)
        
        # Javadoc 특수 태그 제거 (@param, @return 등)
        clean_text = re.sub(r'@\w+\s+\w*', '', javadoc)
        
        # HTML 태그 제거
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        
        # 주석 마커 제거 (/** */ //)
        clean_text = re.sub(r'/\*\*|\*/|//|\*', '', clean_text)
        
        # 한글과 영어 단어 추출
        words = re.findall(r'[가-힣]+|[a-zA-Z]{3,}', clean_text)
        
        for word in words:
            if word.isalpha():
                # 한글인 경우 그대로 추가
                if re.match(r'[가-힣]+', word):
                    keywords.add(word)
                else:
                    # 영어인 경우 소문자로 변환 후 불용어 체크
                    word_lower = word.lower()
                    if word_lower not in self.stop_words or word_lower in self.spring_keywords:
                        keywords.add(word_lower)
        
        return sorted(list(keywords))[:self.max_keywords]
    
    def extract_from_code(self, code: str) -> List[str]:
        """Java 코드 내용에서 키워드 추출
        
        Args:
            code: Java 코드 내용
            
        Returns:
            추출된 키워드 리스트
        """
        keywords = set()
        
        # 주석 제거
        code_no_comments = re.sub(r'//.*?$|/\*.*?\*/', '', code, flags=re.MULTILINE | re.DOTALL)
        
        # 문자열 리터럴에서 키워드 추출 (큰따옴표 안의 내용)
        string_matches = re.findall(r'"([^"]*)"', code_no_comments)
        for string_content in string_matches:
            words = re.findall(r'\b[a-zA-Z]{3,}\b', string_content)
            keywords.update([word.lower() for word in words])
        
        # camelCase/PascalCase 식별자 추출
        identifiers = re.findall(r'\b[a-zA-Z][a-zA-Z0-9]*\b', code_no_comments)
        for identifier in identifiers:
            # camelCase 분리
            parts = re.findall(r'[A-Z][a-z]*|[a-z]+', identifier)
            keywords.update([part.lower() for part in parts if len(part) > 2])
        
        # Spring/JPA 관련 키워드 특별 처리
        spring_patterns = [
            r'@Entity.*?class\s+(\w+)',
            r'@Table\s*\(\s*name\s*=\s*"([^"]+)"',
            r'@Column\s*\(\s*name\s*=\s*"([^"]+)"',
            r'@Query\s*\(\s*"([^"]+)"',
            r'findBy(\w+)',
            r'deleteBy(\w+)',
            r'countBy(\w+)'
        ]
        
        for pattern in spring_patterns:
            matches = re.findall(pattern, code_no_comments, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    for m in match:
                        keywords.update(self.extract_from_name(m))
                else:
                    keywords.update(self.extract_from_name(match))
        
        # 불용어 제거
        filtered_keywords = [
            keyword for keyword in keywords 
            if keyword not in self.stop_words or keyword in self.spring_keywords
        ]
        
        return sorted(filtered_keywords)[:self.max_keywords] 