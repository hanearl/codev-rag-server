import ast
import re
from typing import List
from .schema import ValidationResult

class CodeValidator:
    def validate_python_code(self, code: str) -> ValidationResult:
        """Python 코드 검증"""
        errors = []
        warnings = []
        suggestions = []
        
        # 빈 코드 처리
        if not code.strip():
            return ValidationResult(
                is_valid=True,
                syntax_errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
        
        try:
            # 구문 검사
            ast.parse(code)
            
            # 베스트 프랙티스 검사
            warnings.extend(self._check_python_best_practices(code))
            
            # 개선 제안
            suggestions.extend(self._get_python_suggestions(code))
            
            return ValidationResult(
                is_valid=True,
                syntax_errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
            
        except SyntaxError as e:
            errors.append(f"구문 오류 (라인 {e.lineno}): {e.msg}")
            return ValidationResult(
                is_valid=False,
                syntax_errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
    
    def _check_python_best_practices(self, code: str) -> List[str]:
        """Python 베스트 프랙티스 검사"""
        warnings = []
        
        # 타입 힌트 확인
        if re.search(r'def\s+\w+\([^)]*\)\s*:', code) and '->' not in code:
            if ':' not in code.split('def')[1].split(')')[0]:
                warnings.append("타입 힌트 사용을 권장합니다")
        
        # 독스트링 확인
        if 'def ' in code and '"""' not in code and "'''" not in code:
            warnings.append("함수에 독스트링 추가를 권장합니다")
        
        return warnings
    
    def _get_python_suggestions(self, code: str) -> List[str]:
        """Python 코드 개선 제안"""
        suggestions = []
        
        # 에러 핸들링 제안
        if 'try:' not in code and ('open(' in code or 'requests.' in code):
            suggestions.append("파일 또는 네트워크 작업에 예외 처리를 추가하세요")
        
        return suggestions
    
    def validate_javascript_code(self, code: str) -> ValidationResult:
        """JavaScript 코드 기본 검증"""
        errors = []
        warnings = []
        suggestions = []
        
        # 빈 코드 처리
        if not code.strip():
            return ValidationResult(
                is_valid=True,
                syntax_errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
        
        # 기본 구문 오류 검사
        if code.count('{') != code.count('}'):
            errors.append("중괄호 개수가 맞지 않습니다")
        
        if code.count('(') != code.count(')'):
            errors.append("소괄호 개수가 맞지 않습니다")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            syntax_errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def validate_java_code(self, code: str) -> ValidationResult:
        """Java 코드 검증 (Spring Boot 포함)"""
        errors = []
        warnings = []
        suggestions = []
        
        # 빈 코드 처리
        if not code.strip():
            return ValidationResult(
                is_valid=True,
                syntax_errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
        
        # 기본 구문 검사
        syntax_errors = self._check_java_syntax(code)
        errors.extend(syntax_errors)
        
        # Java 베스트 프랙티스 검사
        warnings.extend(self._check_java_best_practices(code))
        
        # Spring Boot 관련 제안
        suggestions.extend(self._get_java_spring_suggestions(code))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            syntax_errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _check_java_syntax(self, code: str) -> List[str]:
        """Java 기본 구문 검사"""
        errors = []
        
        # 중괄호 매칭 검사
        if code.count('{') != code.count('}'):
            errors.append("중괄호 개수가 맞지 않습니다")
        
        # 소괄호 매칭 검사
        if code.count('(') != code.count(')'):
            errors.append("소괄호 개수가 맞지 않습니다")
        
        # 세미콜론 체크 (메서드 내부 라인)
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('//') and not line.startswith('/*'):
                # 클래스, 메서드 선언이 아닌 실행문인 경우
                if (not any(keyword in line for keyword in ['class', 'interface', 'enum', 'public', 'private', 'protected']) 
                    and not line.endswith('{') and not line.endswith('}') 
                    and not line.startswith('@') and line != '' 
                    and not line.endswith(';') and '=' in line):
                    errors.append(f"라인 {i}: 세미콜론이 누락된 것 같습니다")
        
        return errors
    
    def _check_java_best_practices(self, code: str) -> List[str]:
        """Java 베스트 프랙티스 검사"""
        warnings = []
        
        # Javadoc 체크
        if 'public class' in code or 'public interface' in code:
            if '/**' not in code:
                warnings.append("클래스/인터페이스에 Javadoc 주석을 추가하는 것을 권장합니다")
        
        # 변수명 컨벤션 체크 (camelCase)
        variable_pattern = r'\b[a-z]+[A-Z]\w*\s*='
        if re.search(r'\b[A-Z][a-z]+\w*\s*=', code) and not re.search(variable_pattern, code):
            warnings.append("변수명은 camelCase를 사용하는 것을 권장합니다")
        
        # 매직 넘버 체크
        magic_numbers = re.findall(r'\b\d{2,}\b', code)
        if magic_numbers:
            warnings.append("매직 넘버 대신 상수(final static)를 사용하는 것을 권장합니다")
        
        # Exception 처리 체크
        if 'throw new' in code and 'try' not in code:
            warnings.append("예외를 던지는 코드가 있다면 호출하는 곳에서 try-catch 처리를 고려하세요")
        
        return warnings
    
    def _get_java_spring_suggestions(self, code: str) -> List[str]:
        """Spring Boot 관련 제안"""
        suggestions = []
        
        # Spring Boot 어노테이션 제안
        if 'public class' in code and 'Controller' in code and '@RestController' not in code and '@Controller' not in code:
            suggestions.append("컨트롤러 클래스에는 @RestController 또는 @Controller 어노테이션을 추가하세요")
        
        if 'public class' in code and 'Service' in code and '@Service' not in code:
            suggestions.append("서비스 클래스에는 @Service 어노테이션을 추가하세요")
        
        if 'public class' in code and 'Repository' in code and '@Repository' not in code:
            suggestions.append("리포지토리 클래스에는 @Repository 어노테이션을 추가하세요")
        
        # 의존성 주입 제안
        if '@Autowired' in code:
            suggestions.append("@Autowired 보다는 생성자 주입(Constructor Injection)을 권장합니다")
        
        # REST API 제안
        if '@RequestMapping' in code:
            suggestions.append("@RequestMapping 보다는 @GetMapping, @PostMapping 등 구체적인 어노테이션을 사용하세요")
        
        # 로깅 제안
        if 'System.out.println' in code:
            suggestions.append("System.out.println 대신 SLF4J Logger를 사용하는 것을 권장합니다")
        
        # 설정 클래스 제안
        if '@Configuration' in code and '@Bean' not in code:
            suggestions.append("@Configuration 클래스에는 @Bean 메서드를 정의하는 것이 일반적입니다")
        
        return suggestions 