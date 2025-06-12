import pytest
from app.features.generation.validator import CodeValidator
from app.features.generation.schema import ValidationResult

def test_python_validator_should_validate_syntax():
    """Python 검증기가 구문을 검증해야 함"""
    # Given
    validator = CodeValidator()
    
    valid_code = "def test_func():\n    return 'hello'"
    invalid_code = "def test_func(\n    return 'hello'"
    
    # When
    valid_result = validator.validate_python_code(valid_code)
    invalid_result = validator.validate_python_code(invalid_code)
    
    # Then
    assert valid_result.is_valid == True
    assert len(valid_result.syntax_errors) == 0
    
    assert invalid_result.is_valid == False
    assert len(invalid_result.syntax_errors) > 0

def test_python_validator_should_check_best_practices():
    """Python 검증기가 베스트 프랙티스를 확인해야 함"""
    # Given
    validator = CodeValidator()
    
    # 타입 힌트가 없는 코드
    code_without_hints = "def add(a, b):\n    return a + b"
    
    # 독스트링이 없는 코드
    code_without_docstring = "def complex_function(data):\n    return data.process()"
    
    # When
    result1 = validator.validate_python_code(code_without_hints)
    result2 = validator.validate_python_code(code_without_docstring)
    
    # Then
    assert result1.is_valid == True
    assert any("타입 힌트" in warning for warning in result1.warnings)
    
    assert result2.is_valid == True
    assert any("독스트링" in warning for warning in result2.warnings)

def test_javascript_validator_should_validate_basic_syntax():
    """JavaScript 검증기가 기본 구문을 검증해야 함"""
    # Given
    validator = CodeValidator()
    
    valid_code = "function test() { return 'hello'; }"
    invalid_code = "function test() { return 'hello'; "  # 중괄호 불일치
    
    # When
    valid_result = validator.validate_javascript_code(valid_code)
    invalid_result = validator.validate_javascript_code(invalid_code)
    
    # Then
    assert valid_result.is_valid == True
    assert len(valid_result.syntax_errors) == 0
    
    assert invalid_result.is_valid == False
    assert len(invalid_result.syntax_errors) > 0

def test_validator_should_handle_empty_code():
    """검증기가 빈 코드를 처리해야 함"""
    # Given
    validator = CodeValidator()
    
    # When
    result = validator.validate_python_code("")
    
    # Then
    assert result.is_valid == True  # 빈 코드는 구문적으로 유효
    assert len(result.syntax_errors) == 0 

class TestCodeValidator:
    def test_validate_python_code_success(self):
        """유효한 Python 코드 검증 성공"""
        validator = CodeValidator()
        code = """
def hello_world():
    return "Hello, World!"
"""
        
        result = validator.validate_python_code(code)
        
        assert result.is_valid
        assert len(result.syntax_errors) == 0
    
    def test_validate_python_code_syntax_error(self):
        """Python 구문 오류 검증"""
        validator = CodeValidator()
        code = """
def hello_world(
    return "Hello, World!"
"""
        
        result = validator.validate_python_code(code)
        
        assert not result.is_valid
        assert len(result.syntax_errors) > 0
    
    def test_validate_javascript_code_success(self):
        """유효한 JavaScript 코드 검증 성공"""
        validator = CodeValidator()
        code = """
function helloWorld() {
    return "Hello, World!";
}
"""
        
        result = validator.validate_javascript_code(code)
        
        assert result.is_valid
        assert len(result.syntax_errors) == 0
    
    def test_validate_javascript_code_bracket_mismatch(self):
        """JavaScript 중괄호 불일치 검증"""
        validator = CodeValidator()
        code = """
function helloWorld() {
    return "Hello, World!";
"""
        
        result = validator.validate_javascript_code(code)
        
        assert not result.is_valid
        assert "중괄호 개수가 맞지 않습니다" in result.syntax_errors
    
    def test_validate_java_code_success(self):
        """유효한 Java 코드 검증 성공"""
        validator = CodeValidator()
        code = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
"""
        
        result = validator.validate_java_code(code)
        
        assert result.is_valid
        assert len(result.syntax_errors) == 0
    
    def test_validate_java_code_spring_boot_controller(self):
        """Spring Boot 컨트롤러 코드 검증 및 제안"""
        validator = CodeValidator()
        code = """
public class UserController {
    @RequestMapping("/users")
    public List<User> getUsers() {
        return userService.findAll();
    }
}
"""
        
        result = validator.validate_java_code(code)
        
        assert result.is_valid
        # Spring Boot 관련 제안이 있어야 함
        assert any("@RestController" in suggestion for suggestion in result.suggestions)
        assert any("@GetMapping" in suggestion for suggestion in result.suggestions)
    
    def test_validate_java_code_spring_service(self):
        """Spring Boot 서비스 클래스 검증"""
        validator = CodeValidator()
        code = """
public class UserService {
    @Autowired
    private UserRepository userRepository;
    
    public List<User> findAll() {
        return userRepository.findAll();
    }
}
"""
        
        result = validator.validate_java_code(code)
        
        assert result.is_valid
        # Spring Boot 관련 제안이 있어야 함
        assert any("@Service" in suggestion for suggestion in result.suggestions)
        assert any("생성자 주입" in suggestion for suggestion in result.suggestions)
    
    def test_validate_java_code_bracket_mismatch(self):
        """Java 중괄호 불일치 검증"""
        validator = CodeValidator()
        code = """
public class Test {
    public void method() {
        System.out.println("test");
    // 중괄호 누락
"""
        
        result = validator.validate_java_code(code)
        
        assert not result.is_valid
        assert "중괄호 개수가 맞지 않습니다" in result.syntax_errors
    
    def test_validate_java_code_best_practices(self):
        """Java 베스트 프랙티스 검증"""
        validator = CodeValidator()
        code = """
public class Calculator {
    public int add(int a, int b) {
        return a + b + 100;  // 매직 넘버
    }
}
"""
        
        result = validator.validate_java_code(code)
        
        assert result.is_valid
        # 베스트 프랙티스 경고
        assert any("Javadoc" in warning for warning in result.warnings)
        assert any("매직 넘버" in warning for warning in result.warnings)
    
    def test_validate_java_code_logging_suggestion(self):
        """Java 로깅 관련 제안"""
        validator = CodeValidator()
        code = """
public class UserService {
    public void processUser() {
        System.out.println("Processing user");
    }
}
"""
        
        result = validator.validate_java_code(code)
        
        assert result.is_valid
        assert any("SLF4J Logger" in suggestion for suggestion in result.suggestions)
    
    def test_validate_empty_code(self):
        """빈 코드 검증"""
        validator = CodeValidator()
        
        # Python
        result = validator.validate_python_code("")
        assert result.is_valid
        
        # JavaScript
        result = validator.validate_javascript_code("")
        assert result.is_valid
        
        # Java
        result = validator.validate_java_code("")
        assert result.is_valid 