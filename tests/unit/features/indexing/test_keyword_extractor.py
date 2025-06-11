"""Java 키워드 추출기 테스트

Java/Spring 코드에서 키워드 추출 기능을 테스트합니다.
"""

import pytest
from app.features.indexing.keyword_extractor import KeywordExtractor


class TestKeywordExtractor:
    """Java 키워드 추출기 테스트 클래스"""
    
    def setup_method(self):
        """테스트 메소드 실행 전 설정"""
        self.extractor = KeywordExtractor()
    
    def test_extract_from_camel_case_java_method_name(self):
        """camelCase Java 메소드명에서 키워드 추출"""
        # Given
        method_name = "getUserProfile"
        
        # When
        keywords = self.extractor.extract_from_name(method_name)
        
        # Then
        assert "get" in keywords
        assert "user" in keywords
        assert "profile" in keywords
    
    def test_extract_from_pascal_case_java_class_name(self):
        """PascalCase Java 클래스명에서 키워드 추출"""
        # Given
        class_name = "UserServiceImpl"
        
        # When
        keywords = self.extractor.extract_from_name(class_name)
        
        # Then
        assert "user" in keywords
        assert "service" in keywords
        assert "impl" in keywords
    
    def test_spring_keywords_preserved(self):
        """Spring 관련 키워드는 불용어에서 제외"""
        # Given
        class_name = "UserController"
        
        # When
        keywords = self.extractor.extract_from_name(class_name)
        
        # Then
        assert "user" in keywords
        assert "controller" in keywords  # Spring 키워드이므로 보존
    
    def test_java_stop_words_filtered(self):
        """Java 불용어 필터링"""
        # Given
        method_name = "publicStaticVoidMain"
        
        # When
        keywords = self.extractor.extract_from_name(method_name)
        
        # Then
        assert "public" not in keywords  # Java 키워드이므로 제외
        assert "static" not in keywords  # Java 키워드이므로 제외
        assert "void" not in keywords    # Java 키워드이므로 제외
        assert "main" in keywords        # 의미있는 키워드이므로 포함
    
    def test_extract_from_spring_annotations(self):
        """Spring 어노테이션에서 키워드 추출"""
        # Given
        annotations = ["@RestController", "@RequestMapping", "@GetMapping"]
        
        # When
        keywords = self.extractor.extract_from_annotations(annotations)
        
        # Then
        assert "rest" in keywords
        assert "controller" in keywords
        assert "api" in keywords
        assert "request" in keywords
        assert "mapping" in keywords
        assert "endpoint" in keywords
        assert "get" in keywords
    
    def test_extract_from_jpa_annotations(self):
        """JPA 어노테이션에서 키워드 추출"""
        # Given
        annotations = ["@Entity", "@Table", "@Column", "@Autowired"]
        
        # When
        keywords = self.extractor.extract_from_annotations(annotations)
        
        # Then
        assert "entity" in keywords
        assert "table" in keywords
        assert "column" in keywords
        assert "dependency" in keywords
        assert "injection" in keywords
    
    def test_extract_from_java_code_content(self):
        """Java 코드 내용에서 키워드 추출"""
        # Given
        java_code = '''
        @Service
        public class UserService {
            
            @Autowired
            private UserRepository userRepository;
            
            public User findByUsername(String username) {
                return userRepository.findByUsername(username);
            }
        }
        '''
        
        # When
        keywords = self.extractor.extract_from_code(java_code)
        
        # Then
        assert "service" in keywords
        assert "user" in keywords
        assert "repository" in keywords
        assert "username" in keywords
        assert "find" in keywords
    
    def test_extract_from_spring_query_methods(self):
        """Spring Data JPA 쿼리 메소드에서 키워드 추출"""
        # Given
        java_code = '''
        public interface UserRepository extends JpaRepository<User, Long> {
            User findByUsername(String username);
            List<User> findByAgeGreaterThan(Integer age);
            void deleteByUsername(String username);
            long countByStatus(UserStatus status);
        }
        '''
        
        # When
        keywords = self.extractor.extract_from_code(java_code)
        
        # Then
        assert "find" in keywords
        assert "user" in keywords
        assert "username" in keywords
        assert "age" in keywords
        assert "greater" in keywords
        assert "delete" in keywords
        assert "count" in keywords
        assert "status" in keywords
    
    def test_extract_from_string_literals(self):
        """문자열 리터럴에서 키워드 추출"""
        # Given
        java_code = '''
        @RequestMapping("/api/user/profile")
        public String getUserProfile() {
            return "user profile page";
        }
        '''
        
        # When
        keywords = self.extractor.extract_from_code(java_code)
        
        # Then
        assert "api" in keywords
        assert "user" in keywords
        assert "profile" in keywords
        assert "page" in keywords
    
    def test_keyword_count_limit(self):
        """키워드 개수 제한 (최대 20개)"""
        # Given
        extractor = KeywordExtractor(max_keywords=5)
        long_class_name = "VeryLongComplexBusinessServiceImplementationHelperUtilityManager"
        
        # When
        keywords = extractor.extract_from_name(long_class_name)
        
        # Then
        assert len(keywords) <= 5
    
    def test_javadoc_keyword_extraction(self):
        """Javadoc에서 키워드 추출"""
        # Given
        javadoc = '''
        /**
         * 사용자 프로필을 조회하는 메소드
         * @param userId 사용자 ID
         * @return 사용자 프로필 정보
         */
        '''
        
        # When
        keywords = self.extractor.extract_from_javadoc(javadoc)
        
        # Then
        assert "user" in keywords
        assert "프로필" in keywords  # 한국어 키워드
        # @param, @return 등 Javadoc 태그는 제거되어야 함
    
    def test_spring_entity_annotations(self):
        """Spring Entity 어노테이션 특별 처리"""
        # Given
        java_code = '''
        @Entity
        @Table(name = "user_profiles")
        @Query("SELECT u FROM User u WHERE u.username = :username")
        public class UserProfile {
            @Column(name = "first_name")
            private String firstName;
        }
        '''
        
        # When
        keywords = self.extractor.extract_from_code(java_code)
        
        # Then
        assert "entity" in keywords
        assert "user" in keywords
        assert "profile" in keywords
        assert "first" in keywords
        assert "name" in keywords 