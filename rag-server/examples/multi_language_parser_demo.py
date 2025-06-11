#!/usr/bin/env python3
"""다중 언어 코드 파서 데모

이 스크립트는 새로운 다중 언어 지원 코드 파서의 사용법을 보여줍니다.
Python, Java, JavaScript 코드를 파싱하여 함수, 클래스, 메소드 단위로 분할하고
키워드를 추출하는 기능을 시연합니다.
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.features.indexing import (
    CodeParserFactory, 
    LanguageType, 
    CodeType,
    KeywordExtractor
)


def demo_python_parsing():
    """Python 코드 파싱 데모"""
    print("=" * 60)
    print("🐍 Python 코드 파싱 데모")
    print("=" * 60)
    
    python_code = '''
class DataProcessor:
    """데이터 처리를 위한 클래스"""
    
    def __init__(self, config):
        self.config = config
        self.processed_count = 0
    
    async def process_data(self, data_list):
        """비동기 데이터 처리 메소드"""
        results = []
        for item in data_list:
            processed = await self._process_single_item(item)
            results.append(processed)
            self.processed_count += 1
        return results
    
    def _process_single_item(self, item):
        """단일 아이템 처리"""
        return item.upper()

def utility_function(text):
    """유틸리티 함수"""
    return text.strip().lower()
'''
    
    # 키워드 추출기와 함께 파서 생성
    keyword_extractor = KeywordExtractor()
    parser = CodeParserFactory.create_parser(LanguageType.PYTHON, keyword_extractor)
    
    # 코드 파싱
    chunks = parser.parse_code(python_code, "demo.py")
    
    print(f"📊 파싱 결과: {len(chunks)}개 청크 발견")
    print()
    
    for i, chunk in enumerate(chunks, 1):
        print(f"[{i}] {chunk.code_type.value.upper()}: {chunk.name}")
        print(f"    📍 라인: {chunk.line_start}-{chunk.line_end}")
        print(f"    🏷️  키워드: {', '.join(chunk.keywords[:5])}")
        if chunk.parent_class:
            print(f"    🏠 부모 클래스: {chunk.parent_class}")
        if chunk.parameters:
            print(f"    📝 파라미터: {', '.join(chunk.parameters)}")
        if chunk.language_specific:
            special = []
            if chunk.language_specific.get('is_async'):
                special.append('async')
            if special:
                print(f"    ⚡ 특성: {', '.join(special)}")
        print()


def demo_java_parsing():
    """Java 코드 파싱 데모"""
    print("=" * 60)
    print("☕ Java 코드 파싱 데모")
    print("=" * 60)
    
    java_code = '''
package com.example.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

@Service
public class UserService {
    
    @Autowired
    private UserRepository userRepository;
    
    public UserService() {
        // 기본 생성자
    }
    
    @Transactional
    public User createUser(String name, String email) {
        User user = new User(name, email);
        return userRepository.save(user);
    }
    
    public List<User> findAllUsers() {
        return userRepository.findAll();
    }
    
    @Override
    public String toString() {
        return "UserService";
    }
}
'''
    
    # Java 파서 생성
    keyword_extractor = KeywordExtractor()
    parser = CodeParserFactory.create_parser(LanguageType.JAVA, keyword_extractor)
    
    # 코드 파싱
    chunks = parser.parse_code(java_code, "UserService.java")
    
    print(f"📊 파싱 결과: {len(chunks)}개 청크 발견")
    print()
    
    for i, chunk in enumerate(chunks, 1):
        print(f"[{i}] {chunk.code_type.value.upper()}: {chunk.name}")
        print(f"    📍 라인: {chunk.line_start}-{chunk.line_end}")
        print(f"    📦 패키지: {chunk.namespace}")
        print(f"    🏷️  키워드: {', '.join(chunk.keywords[:5])}")
        if chunk.parent_class:
            print(f"    🏠 부모 클래스: {chunk.parent_class}")
        if chunk.annotations:
            print(f"    📌 어노테이션: {', '.join(chunk.annotations)}")
        if chunk.modifiers:
            print(f"    🔧 수정자: {', '.join(chunk.modifiers)}")
        if chunk.parameters:
            print(f"    📝 파라미터: {', '.join(chunk.parameters)}")
        print()


def demo_javascript_parsing():
    """JavaScript 코드 파싱 데모"""
    print("=" * 60)
    print("🟨 JavaScript 코드 파싱 데모")
    print("=" * 60)
    
    javascript_code = '''
class ApiClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.timeout = 5000;
    }
    
    async fetchData(endpoint) {
        const url = `${this.baseUrl}/${endpoint}`;
        try {
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('Fetch error:', error);
            throw error;
        }
    }
    
    static createDefault() {
        return new ApiClient('https://api.example.com');
    }
}

function processResponse(data) {
    return data.map(item => ({
        id: item.id,
        name: item.name.toUpperCase(),
        processed: true
    }));
}

const validateInput = (input) => {
    return input && typeof input === 'string' && input.length > 0;
};
'''
    
    # JavaScript 파서 생성
    keyword_extractor = KeywordExtractor()
    parser = CodeParserFactory.create_parser(LanguageType.JAVASCRIPT, keyword_extractor)
    
    # 코드 파싱
    chunks = parser.parse_code(javascript_code, "api-client.js")
    
    print(f"📊 파싱 결과: {len(chunks)}개 청크 발견")
    print()
    
    for i, chunk in enumerate(chunks, 1):
        print(f"[{i}] {chunk.code_type.value.upper()}: {chunk.name}")
        print(f"    📍 라인: {chunk.line_start}-{chunk.line_end}")
        print(f"    🏷️  키워드: {', '.join(chunk.keywords[:5])}")
        if chunk.parent_class:
            print(f"    🏠 부모 클래스: {chunk.parent_class}")
        if chunk.parameters:
            print(f"    📝 파라미터: {', '.join(chunk.parameters)}")
        if chunk.language_specific:
            special = []
            if chunk.language_specific.get('is_async'):
                special.append('async')
            if chunk.language_specific.get('is_static'):
                special.append('static')
            if chunk.language_specific.get('is_variable_function'):
                special.append('variable function')
            if special:
                print(f"    ⚡ 특성: {', '.join(special)}")
        print()


def demo_factory_features():
    """팩토리 기능 데모"""
    print("=" * 60)
    print("🏭 파서 팩토리 기능 데모")
    print("=" * 60)
    
    # 지원하는 언어 목록
    languages = CodeParserFactory.get_supported_languages()
    print(f"🌍 지원하는 언어: {[lang.value for lang in languages]}")
    
    # 지원하는 확장자 목록
    extensions = CodeParserFactory.get_supported_extensions()
    print(f"📁 지원하는 확장자: {extensions}")
    print()
    
    # 파일별 언어 감지
    test_files = [
        "main.py", "App.java", "script.js", "component.jsx", 
        "module.mjs", "test.cpp", "README.md"
    ]
    
    print("🔍 파일별 언어 감지:")
    for file_path in test_files:
        language = CodeParserFactory.detect_language(file_path)
        supported = CodeParserFactory.is_supported_file(file_path)
        status = "✅ 지원됨" if supported else "❌ 지원안됨"
        lang_name = language.value if language else "알 수 없음"
        print(f"  {file_path:<15} → {lang_name:<12} {status}")
    print()
    
    # 파서 정보
    print("📋 파서별 상세 정보:")
    for language in languages:
        parser = CodeParserFactory.create_parser(language)
        info = parser.get_parser_info()
        print(f"  {info['language']:<12}: {info['parser_class']}")
        print(f"    확장자: {', '.join(info['supported_extensions'])}")
        print(f"    키워드 추출기: {'있음' if info['has_keyword_extractor'] else '없음'}")
        print()


def demo_file_parsing():
    """실제 파일 파싱 데모"""
    print("=" * 60)
    print("📄 실제 파일 파싱 데모")
    print("=" * 60)
    
    # 임시 파일 생성 및 파싱
    import tempfile
    
    sample_code = '''
def fibonacci(n):
    """피보나치 수열 계산"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class MathUtils:
    @staticmethod
    def factorial(n):
        if n <= 1:
            return 1
        return n * MathUtils.factorial(n-1)
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(sample_code)
        temp_file = f.name
    
    try:
        # 파일로부터 파서 생성
        keyword_extractor = KeywordExtractor()
        parser = CodeParserFactory.create_parser_for_file(temp_file, keyword_extractor)
        
        if parser:
            # 파일 파싱
            result = parser.parse_file(temp_file)
            
            print(f"📁 파일: {temp_file}")
            print(f"🌍 언어: {result.language.value}")
            print(f"📊 총 라인 수: {result.total_lines}")
            print(f"⏱️  파싱 시간: {result.parse_time:.4f}초")
            print(f"🔍 발견된 청크: {len(result.chunks)}개")
            
            if result.errors:
                print(f"❌ 오류: {result.errors}")
            else:
                print("✅ 파싱 성공!")
            
            print("\n📋 청크 목록:")
            for chunk in result.chunks:
                print(f"  - {chunk.code_type.value}: {chunk.name} (라인 {chunk.line_start}-{chunk.line_end})")
        else:
            print("❌ 지원하지 않는 파일 형식입니다.")
            
    finally:
        # 임시 파일 정리
        os.unlink(temp_file)


def main():
    """메인 데모 함수"""
    print("🚀 다중 언어 코드 파서 데모")
    print("=" * 60)
    print("이 데모는 Python, Java, JavaScript 코드를 파싱하여")
    print("함수, 클래스, 메소드 단위로 분할하고 키워드를 추출하는")
    print("다중 언어 지원 코드 파서의 기능을 보여줍니다.")
    print()
    
    try:
        # 각 언어별 파싱 데모
        demo_python_parsing()
        demo_java_parsing() 
        demo_javascript_parsing()
        
        # 팩토리 기능 데모
        demo_factory_features()
        
        # 파일 파싱 데모
        demo_file_parsing()
        
        print("=" * 60)
        print("✅ 모든 데모가 성공적으로 완료되었습니다!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 데모 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 