"""
검색 유틸리티 함수들에 대한 테스트
"""
import pytest
from app.features.search.utils import (
    extract_java_package_name,
    extract_java_class_name,
    enhance_metadata_for_java
)


class TestExtractJavaPackageName:
    """Java 패키지명 추출 함수 테스트"""
    
    def test_extract_package_name_success(self):
        """패키지 선언이 있는 Java 파일에서 패키지명을 추출해야 함"""
        java_content = """
package com.example.service;

import java.util.List;

public class UserService {
    // 클래스 내용
}
"""
        result = extract_java_package_name(java_content)
        assert result == "com.example.service"
    
    def test_extract_package_name_with_comments(self):
        """주석이 포함된 파일에서도 올바르게 패키지명을 추출해야 함"""
        java_content = """
// 이것은 주석입니다
// package com.fake.package; 이것은 주석 안의 package
package com.real.package;

public class TestClass {
}
"""
        result = extract_java_package_name(java_content)
        assert result == "com.real.package"
    
    def test_extract_package_name_no_package(self):
        """패키지 선언이 없는 파일에서는 None을 반환해야 함"""
        java_content = """
import java.util.List;

public class TestClass {
    // 패키지 선언 없음
}
"""
        result = extract_java_package_name(java_content)
        assert result is None
    
    def test_extract_package_name_empty_content(self):
        """빈 내용에서는 None을 반환해야 함"""
        result = extract_java_package_name("")
        assert result is None
        
        result = extract_java_package_name(None)
        assert result is None
    
    def test_extract_package_name_complex_package(self):
        """복잡한 패키지명도 올바르게 추출해야 함"""
        java_content = """
package org.springframework.boot.autoconfigure.web.servlet;

@Configuration
public class WebMvcAutoConfiguration {
}
"""
        result = extract_java_package_name(java_content)
        assert result == "org.springframework.boot.autoconfigure.web.servlet"


class TestExtractJavaClassName:
    """Java 클래스명 추출 함수 테스트"""
    
    def test_extract_class_name_public_class(self):
        """public class에서 클래스명을 추출해야 함"""
        java_content = """
package com.example;

public class UserService {
    // 클래스 내용
}
"""
        result = extract_java_class_name(java_content)
        assert result == "UserService"
    
    def test_extract_class_name_simple_class(self):
        """일반 class에서 클래스명을 추출해야 함"""
        java_content = """
class SimpleClass {
    // 클래스 내용
}
"""
        result = extract_java_class_name(java_content)
        assert result == "SimpleClass"
    
    def test_extract_class_name_interface(self):
        """interface에서 인터페이스명을 추출해야 함"""
        java_content = """
public interface UserRepository {
    // 인터페이스 내용
}
"""
        result = extract_java_class_name(java_content)
        assert result == "UserRepository"
    
    def test_extract_class_name_enum(self):
        """enum에서 enum명을 추출해야 함"""
        java_content = """
public enum Status {
    ACTIVE, INACTIVE
}
"""
        result = extract_java_class_name(java_content)
        assert result == "Status"
    
    def test_extract_class_name_from_file_path(self):
        """파일 경로에서 클래스명을 추출할 수 있어야 함"""
        java_content = ""  # 내용이 없는 경우
        file_path = "/path/to/MyClass.java"
        
        result = extract_java_class_name(java_content, file_path)
        assert result == "MyClass"
    
    def test_extract_class_name_no_class(self):
        """클래스가 없는 파일에서는 None을 반환해야 함"""
        java_content = """
package com.example;
// 주석만 있는 파일
"""
        result = extract_java_class_name(java_content)
        assert result is None


class TestEnhanceMetadataForJava:
    """Java 메타데이터 향상 함수 테스트"""
    
    def test_enhance_metadata_for_java_file(self):
        """Java 파일의 메타데이터를 향상시켜야 함"""
        metadata = {
            "type": "java",
            "file_path": "/src/main/java/com/example/UserService.java"
        }
        
        java_content = """
package com.example.service;

public class UserService {
    // 서비스 로직
}
"""
        
        result = enhance_metadata_for_java(metadata, java_content)
        
        assert result["type"] == "java"
        assert result["package"] == "com.example.service"
        assert result["class_name"] == "UserService"
        assert result["full_class_name"] == "com.example.service.UserService"
    
    def test_enhance_metadata_for_non_java_file(self):
        """Java가 아닌 파일의 메타데이터는 변경하지 않아야 함"""
        metadata = {
            "type": "python",
            "file_path": "/src/main.py"
        }
        
        content = """
def main():
    print("Hello World")
"""
        
        result = enhance_metadata_for_java(metadata, content)
        
        # 원본 메타데이터와 동일해야 함
        assert result == metadata
        assert "package" not in result
        assert "class_name" not in result
    
    def test_enhance_metadata_with_language_field(self):
        """language 필드가 java인 경우에도 향상되어야 함"""
        metadata = {
            "language": "java",
            "file_path": "/UserService.java"
        }
        
        java_content = """
package com.test;

public class UserService {
}
"""
        
        result = enhance_metadata_for_java(metadata, java_content)
        
        assert result["package"] == "com.test"
        assert result["class_name"] == "UserService"
        assert result["full_class_name"] == "com.test.UserService"
    
    def test_enhance_metadata_partial_info(self):
        """패키지나 클래스명 중 일부만 있는 경우"""
        metadata = {"type": "java"}
        
        # 패키지는 없고 클래스만 있는 경우
        java_content = """
public class SimpleClass {
}
"""
        
        result = enhance_metadata_for_java(metadata, java_content)
        
        assert "package" not in result  # 패키지가 없으므로 추가되지 않음
        assert result["class_name"] == "SimpleClass"
        assert "full_class_name" not in result  # 패키지가 없으므로 full_class_name도 없음
    
    def test_enhance_metadata_preserves_existing_fields(self):
        """기존 메타데이터 필드들이 보존되어야 함"""
        metadata = {
            "type": "java",
            "file_path": "/test.java",
            "size": 1024,
            "author": "test"
        }
        
        java_content = """
package com.test;
public class Test {}
"""
        
        result = enhance_metadata_for_java(metadata, java_content)
        
        # 기존 필드들이 보존되어야 함
        assert result["file_path"] == "/test.java"
        assert result["size"] == 1024
        assert result["author"] == "test"
        
        # 새로운 필드들이 추가되어야 함
        assert result["package"] == "com.test"
        assert result["class_name"] == "Test" 