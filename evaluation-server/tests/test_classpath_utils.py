import pytest
from app.core.classpath_utils import ClasspathConverter, ClasspathMatcher, create_default_classpath_converter


class TestClasspathConverter:
    """클래스패스 변환기 테스트"""
    
    def setup_method(self):
        """테스트 메서드 실행 전 설정"""
        self.converter = ClasspathConverter(["src/main/java", "src/test/java"])
    
    def test_filepath_to_classpath_basic(self):
        """기본 파일패스를 클래스패스로 변환 테스트"""
        # Given
        filepath = "src/main/java/com/skax/library/controller/BookController.java"
        
        # When
        result = self.converter.filepath_to_classpath(filepath)
        
        # Then
        assert result == "com.skax.library.controller.BookController"
    
    def test_filepath_to_classpath_test_package(self):
        """테스트 패키지 파일패스 변환 테스트"""
        # Given
        filepath = "src/test/java/com/skax/library/controller/BookControllerTest.java"
        
        # When
        result = self.converter.filepath_to_classpath(filepath)
        
        # Then
        assert result == "com.skax.library.controller.BookControllerTest"
    
    def test_filepath_to_classpath_without_extension(self):
        """.java 확장자가 없는 경우 테스트"""
        # Given
        filepath = "src/main/java/com/skax/library/controller/BookController"
        
        # When
        result = self.converter.filepath_to_classpath(filepath)
        
        # Then
        assert result == "com.skax.library.controller.BookController"
    
    def test_filepath_to_classpath_fallback_package_detection(self):
        """소스 루트가 없을 때 패키지 자동 감지 테스트"""
        # Given
        filepath = "com/skax/library/model/Book.java"
        
        # When
        result = self.converter.filepath_to_classpath(filepath)
        
        # Then
        assert result == "com.skax.library.model.Book"
    
    def test_filepath_to_classpath_no_package(self):
        """패키지가 감지되지 않는 경우 테스트"""
        # Given
        filepath = "SomeClass.java"
        
        # When
        result = self.converter.filepath_to_classpath(filepath)
        
        # Then
        assert result == "SomeClass"
    
    def test_extract_class_from_classpath_with_method(self):
        """메서드가 포함된 클래스패스에서 클래스만 추출 테스트"""
        # Given
        classpath = "com.skax.library.service.impl.BookServiceImpl.createBook"
        
        # When
        result = self.converter.extract_class_from_classpath(classpath, ignore_method=True)
        
        # Then
        assert result == "com.skax.library.service.impl.BookServiceImpl"
    
    def test_extract_class_from_classpath_without_method(self):
        """메서드가 없는 클래스패스 테스트"""
        # Given
        classpath = "com.skax.library.controller.BookController"
        
        # When
        result = self.converter.extract_class_from_classpath(classpath, ignore_method=True)
        
        # Then
        assert result == "com.skax.library.controller.BookController"
    
    def test_extract_class_from_classpath_ignore_disabled(self):
        """메서드 무시 옵션이 비활성화된 경우 테스트"""
        # Given
        classpath = "com.skax.library.service.impl.BookServiceImpl.createBook"
        
        # When
        result = self.converter.extract_class_from_classpath(classpath, ignore_method=False)
        
        # Then
        assert result == "com.skax.library.service.impl.BookServiceImpl.createBook"
    
    def test_normalize_classpath_case_insensitive(self):
        """대소문자 구분하지 않는 정규화 테스트"""
        # Given
        classpath = "Com.Skax.Library.Controller.BookController"
        
        # When
        result = self.converter.normalize_classpath(classpath, case_sensitive=False)
        
        # Then
        assert result == "com.skax.library.controller.bookcontroller"
    
    def test_normalize_classpath_case_sensitive(self):
        """대소문자 구분하는 정규화 테스트"""
        # Given
        classpath = "Com.Skax.Library.Controller.BookController"
        
        # When
        result = self.converter.normalize_classpath(classpath, case_sensitive=True)
        
        # Then
        assert result == "Com.Skax.Library.Controller.BookController"


class TestClasspathMatcher:
    """클래스패스 매처 테스트"""
    
    def setup_method(self):
        """테스트 메서드 실행 전 설정"""
        converter = ClasspathConverter(["src/main/java", "src/test/java"])
        self.matcher = ClasspathMatcher(converter)
    
    def test_match_classpaths_exact_match(self):
        """정확히 일치하는 클래스패스 매칭 테스트"""
        # Given
        expected = ["com.skax.library.controller.BookController"]
        filepaths = ["src/main/java/com/skax/library/controller/BookController.java"]
        
        # When
        matches = self.matcher.match_classpaths(expected, filepaths)
        
        # Then
        assert matches == [True]
    
    def test_match_classpaths_with_method_ignore(self):
        """메서드명 무시하여 매칭 테스트"""
        # Given
        expected = ["com.skax.library.service.impl.BookServiceImpl.createBook"]
        filepaths = ["src/main/java/com/skax/library/service/impl/BookServiceImpl.java"]
        
        # When
        matches = self.matcher.match_classpaths(
            expected, filepaths, ignore_method_names=True
        )
        
        # Then
        assert matches == [True]
    
    def test_match_classpaths_case_insensitive(self):
        """대소문자 구분하지 않는 매칭 테스트"""
        # Given
        expected = ["com.skax.library.controller.BookController"]
        filepaths = ["src/main/java/Com/Skax/Library/Controller/BookController.java"]
        
        # When
        matches = self.matcher.match_classpaths(
            expected, filepaths, case_sensitive=False
        )
        
        # Then
        assert matches == [True]
    
    def test_match_classpaths_multiple_expected(self):
        """여러 기대값과 매칭 테스트"""
        # Given
        expected = [
            "com.skax.library.controller.BookController",
            "com.skax.library.service.impl.BookServiceImpl"
        ]
        filepaths = [
            "src/main/java/com/skax/library/controller/BookController.java",
            "src/main/java/com/skax/library/model/Book.java",
            "src/main/java/com/skax/library/service/impl/BookServiceImpl.java"
        ]
        
        # When
        matches = self.matcher.match_classpaths(expected, filepaths)
        
        # Then
        assert matches == [True, False, True]
    
    def test_calculate_metrics_at_k(self):
        """k값별 메트릭 계산 테스트"""
        # Given
        expected = ["com.skax.library.controller.BookController"]
        filepaths = [
            "src/main/java/com/skax/library/model/Book.java",
            "src/main/java/com/skax/library/controller/BookController.java",
            "src/main/java/com/skax/library/service/BookService.java"
        ]
        k_values = [1, 2, 3]
        
        # When
        result = self.matcher.calculate_metrics_at_k(expected, filepaths, k_values)
        
        # Then
        assert result["matches"] == [False, True, False]
        assert result["hit_at_k"][1] == 0.0  # 첫 번째 결과에 정답 없음
        assert result["hit_at_k"][2] == 1.0  # 두 번째까지에 정답 있음
        assert result["hit_at_k"][3] == 1.0  # 세 번째까지에 정답 있음
        assert result["reciprocal_rank"] == 0.5  # 2번째 위치 = 1/2
    
    def test_calculate_metrics_no_match(self):
        """매칭되는 결과가 없는 경우 테스트"""
        # Given
        expected = ["com.skax.library.controller.BookController"]
        filepaths = [
            "src/main/java/com/skax/library/model/Book.java",
            "src/main/java/com/skax/library/service/BookService.java"
        ]
        k_values = [1, 2]
        
        # When
        result = self.matcher.calculate_metrics_at_k(expected, filepaths, k_values)
        
        # Then
        assert result["matches"] == [False, False]
        assert result["hit_at_k"][1] == 0.0
        assert result["hit_at_k"][2] == 0.0
        assert result["reciprocal_rank"] == 0.0


def test_create_default_classpath_converter():
    """기본 클래스패스 변환기 생성 테스트"""
    # When
    converter = create_default_classpath_converter()
    
    # Then
    assert isinstance(converter, ClasspathConverter)
    assert "src/main/java" in converter.source_roots
    assert "src/test/java" in converter.source_roots 