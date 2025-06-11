"""Java 코드 파서 테스트

Java 코드 파싱 기능을 테스트합니다.
"""

import pytest
from app.features.indexing.parsers.java_parser import JavaParser
from app.features.indexing.schemas import CodeChunk


class TestJavaParser:
    """Java 코드 파서 테스트 클래스"""
    
    def setup_method(self):
        """테스트 메소드 실행 전 설정"""
        self.parser = JavaParser()
    
    def test_empty_code_returns_empty_chunks(self):
        """빈 코드 입력 시 빈 청크 리스트 반환"""
        result = self.parser.parse_code("", "test.java")
        assert result.chunks == []
    
    def test_parse_simple_java_class(self):
        """단순한 Java 클래스 파싱 테스트"""
        java_code = """
package com.example.demo;

public class UserService {
    public String getName() {
        return "test";
    }
}
"""
        result = self.parser.parse_code(java_code, "UserService.java")
        chunks = result.chunks
        
        # 클래스와 메소드 2개 청크 생성 확인
        assert len(chunks) == 2
        
        # 클래스 청크 확인
        class_chunk = next((chunk for chunk in chunks if chunk.code_type.value == "class"), None)
        assert class_chunk is not None
        assert class_chunk.name == "UserService"
        assert class_chunk.language_specific.get("package_name") == "com.example.demo"
        assert "user" in class_chunk.keywords
        assert "service" in class_chunk.keywords
        
        # 메소드 청크 확인
        method_chunk = next((chunk for chunk in chunks if chunk.code_type.value == "method"), None)
        assert method_chunk is not None
        assert method_chunk.name == "UserService.getName"
        assert method_chunk.language_specific.get("class_name") == "UserService"
        assert "get" in method_chunk.keywords
        assert "name" in method_chunk.keywords
    
    def test_parse_spring_controller(self):
        """Spring Controller 파싱 테스트"""
        java_code = """
package com.example.demo.controller;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/users")
public class UserController {
    
    @GetMapping("/{id}")
    public User getUserById(@PathVariable Long id) {
        return userService.findById(id);
    }
    
    @PostMapping
    public User createUser(@RequestBody User user) {
        return userService.save(user);
    }
}
"""
        result = self.parser.parse_code(java_code, "UserController.java")
        chunks = result.chunks
        
        # 클래스 1개 + 메소드 2개 = 3개 청크
        assert len(chunks) == 3
        
        # 클래스 청크 확인
        class_chunk = next((chunk for chunk in chunks if chunk.code_type.value == "class"), None)
        assert class_chunk is not None
        assert class_chunk.name == "UserController"
        assert "@RestController" in class_chunk.language_specific.get("annotations", [])
        assert "@RequestMapping" in class_chunk.language_specific.get("annotations", [])
        assert "rest" in class_chunk.keywords
        assert "controller" in class_chunk.keywords
        assert "api" in class_chunk.keywords
        
        # GET 메소드 확인
        get_method = next((chunk for chunk in chunks if "getUserById" in chunk.name), None)
        assert get_method is not None
        assert "@GetMapping" in get_method.language_specific.get("annotations", [])
        assert "get" in get_method.keywords
        assert "user" in get_method.keywords
        assert get_method.language_specific.get("return_type") == "User"
        
        # POST 메소드 확인
        post_method = next((chunk for chunk in chunks if "createUser" in chunk.name), None)
        assert post_method is not None
        assert "@PostMapping" in post_method.language_specific.get("annotations", [])
        assert "post" in post_method.keywords
    
    def test_parse_jpa_entity(self):
        """JPA Entity 파싱 테스트"""
        java_code = """
package com.example.demo.entity;

import javax.persistence.*;

@Entity
@Table(name = "users")
public class User {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "username")
    private String username;
    
    public Long getId() {
        return id;
    }
    
    public void setId(Long id) {
        this.id = id;
    }
}
"""
        result = self.parser.parse_code(java_code, "User.java")
        chunks = result.chunks
        
        # 클래스 1개 + 메소드 2개 = 3개 청크
        assert len(chunks) == 3
        
        # Entity 클래스 확인
        class_chunk = next((chunk for chunk in chunks if chunk.code_type.value == "class"), None)
        assert class_chunk is not None
        assert class_chunk.name == "User"
        assert "@Entity" in class_chunk.language_specific.get("annotations", [])
        assert "@Table" in class_chunk.language_specific.get("annotations", [])
        assert "entity" in class_chunk.keywords
        assert "user" in class_chunk.keywords
    
    def test_parse_interface(self):
        """인터페이스 파싱 테스트"""
        java_code = """
package com.example.demo.repository;

import org.springframework.data.jpa.repository.JpaRepository;

public interface UserRepository extends JpaRepository<User, Long> {
    
    User findByUsername(String username);
    
    void deleteByUsername(String username);
}
"""
        result = self.parser.parse_code(java_code, "UserRepository.java")
        chunks = result.chunks
        
        # 인터페이스 1개 + 메소드 2개 = 3개 청크
        assert len(chunks) == 3
        
        # 인터페이스 청크 확인
        interface_chunk = next((chunk for chunk in chunks if chunk.code_type.value == "interface"), None)
        assert interface_chunk is not None
        assert interface_chunk.name == "UserRepository"
        assert "user" in interface_chunk.keywords
        assert "repository" in interface_chunk.keywords
    
    def test_parse_enum(self):
        """Enum 파싱 테스트"""
        java_code = """
package com.example.demo.enums;

public enum UserStatus {
    ACTIVE,
    INACTIVE,
    PENDING,
    DELETED
}
"""
        result = self.parser.parse_code(java_code, "UserStatus.java")
        chunks = result.chunks
        
        # Enum 1개 청크
        assert len(chunks) == 1
        
        enum_chunk = chunks[0]
        assert enum_chunk.code_type.value == "enum"
        assert enum_chunk.name == "UserStatus"
        assert "user" in enum_chunk.keywords
        assert "status" in enum_chunk.keywords
    
    def test_parse_package_name(self):
        """패키지명 추출 테스트"""
        java_code = """
package com.example.demo.service.impl;

public class UserServiceImpl {
}
"""
        result = self.parser.parse_code(java_code, "UserServiceImpl.java")
        chunks = result.chunks
        
        assert len(chunks) == 1
        class_chunk = chunks[0]
        assert class_chunk.language_specific.get("package_name") == "com.example.demo.service.impl"
    
    def test_parse_annotations_and_modifiers(self):
        """어노테이션과 수정자 파싱 테스트"""
        java_code = """
@Service
@Transactional
public final class UserService {
    
    @Autowired
    private static final UserRepository userRepository;
    
    @Override
    public abstract User findUser(Long id);
}
"""
        result = self.parser.parse_code(java_code, "UserService.java")
        chunks = result.chunks
        
        # 클래스와 메소드 청크 확인
        class_chunk = next((chunk for chunk in chunks if chunk.code_type.value == "class"), None)
        assert class_chunk is not None
        
        # 어노테이션 확인
        annotations = class_chunk.language_specific.get("annotations", [])
        assert "@Service" in annotations
        assert "@Transactional" in annotations
        
        # 수정자 확인
        modifiers = class_chunk.language_specific.get("modifiers", [])
        assert "public" in modifiers
        assert "final" in modifiers
    
    def test_line_numbers_extraction(self):
        """라인 번호 추출 테스트"""
        java_code = """package com.example;

public class TestClass {
    
    public void method1() {
        System.out.println("test");
    }
    
    public void method2() {
        return;
    }
}
"""
        result = self.parser.parse_code(java_code, "TestClass.java")
        chunks = result.chunks
        
        # 각 청크의 라인 번호가 정확한지 확인
        for chunk in chunks:
            assert chunk.line_start > 0
            assert chunk.line_end >= chunk.line_start
            assert chunk.line_end <= len(java_code.split('\n'))
    
    def test_syntax_error_handling(self):
        """구문 오류 처리 테스트"""
        # 잘못된 Java 코드
        invalid_java_code = """
public class InvalidClass {
    public void method( {  // 구문 오류
        System.out.println("test");
    }
}
"""
        
        # 예외가 발생하지 않고 빈 결과를 반환하는지 확인
        result = self.parser.parse_code(invalid_java_code, "InvalidClass.java")
        # 구문 오류가 있어도 파서가 실패하지 않아야 함
        assert isinstance(result.chunks, list) 