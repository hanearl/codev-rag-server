import pytest
import json
import jsonlines
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from app.features.evaluation.dataset_loader import DatasetLoader
from app.features.evaluation.schema import EvaluationQuestion, DatasetMetadata, DifficultyLevel


class TestDatasetLoader:
    """데이터셋 로더 테스트"""
    
    def setup_method(self):
        """테스트 메서드 실행 전 설정"""
        self.loader = DatasetLoader("test_datasets")
    
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_metadata_success(self, mock_file, mock_exists):
        """메타데이터 로드 성공 테스트"""
        # Given
        mock_exists.return_value = True
        metadata_content = {
            "name": "Test Dataset",
            "description": "테스트용 데이터셋",
            "version": "1.0.0",
            "language": "ko",
            "domain": "java_development",
            "query_count": 10,
            "ground_truth_format": "inline",
            "evaluation_options": {
                "convert_filepath_to_classpath": True,
                "ignore_method_names": True,
                "case_sensitive": False
            },
            "difficulty_levels": ["하", "중", "상"],
            "created_at": "2024-01-15T00:00:00Z"
        }
        mock_file.return_value.read.return_value = json.dumps(metadata_content)
        
        # When
        dataset_path = Path("test_datasets/sample-dataset")
        result = self.loader._load_metadata(dataset_path)
        
        # Then
        assert isinstance(result, DatasetMetadata)
        assert result.name == "Test Dataset"
        assert result.version == "1.0.0"
        assert result.evaluation_options.convert_filepath_to_classpath is True
        assert result.evaluation_options.ignore_method_names is True
    
    def test_parse_question_item_single_answer(self):
        """단일 정답 질문 아이템 파싱 테스트"""
        # Given
        item = {
            "difficulty": "하",
            "question": "도서 관리를 담당하는 컨트롤러 클래스는 무엇인가요?",
            "answer": "com.skax.library.controller.BookController"
        }
        
        # When
        result = self.loader._parse_question_item(item)
        
        # Then
        assert isinstance(result, EvaluationQuestion)
        assert result.difficulty == DifficultyLevel.EASY
        assert result.question == item["question"]
        assert result.answer == item["answer"]
    
    def test_parse_question_item_multiple_answers(self):
        """다중 정답 질문 아이템 파싱 테스트"""
        # Given
        item = {
            "difficulty": "중",
            "question": "도서 대출 처리 시 호출되는 클래스들은 무엇인가요?",
            "answer": [
                "com.skax.library.controller.LoanController",
                "com.skax.library.service.impl.LoanServiceImpl.checkoutBook",
                "com.skax.library.repository.LoanRepository"
            ]
        }
        
        # When
        result = self.loader._parse_question_item(item)
        
        # Then
        assert isinstance(result, EvaluationQuestion)
        assert result.difficulty == DifficultyLevel.MEDIUM
        assert isinstance(result.answer, list)
        assert len(result.answer) == 3
        assert result.answer[0] == "com.skax.library.controller.LoanController"
    
    def test_parse_question_item_missing_fields(self):
        """필수 필드가 누락된 경우 테스트"""
        # Given
        item = {
            "difficulty": "하",
            "question": "질문만 있는 경우"
            # answer 필드 누락
        }
        
        # When
        result = self.loader._parse_question_item(item)
        
        # Then
        assert result is None
    
    def test_parse_question_item_invalid_difficulty(self):
        """올바르지 않은 난이도가 입력된 경우 테스트"""
        # Given
        item = {
            "difficulty": "매우어려움",  # 올바르지 않은 난이도
            "question": "테스트 질문",
            "answer": "테스트 정답"
        }
        
        # When
        result = self.loader._parse_question_item(item)
        
        # Then
        assert result is not None
        assert result.difficulty == DifficultyLevel.EASY  # 기본값으로 설정됨
    
    @patch('pathlib.Path.exists')
    @patch('jsonlines.open')
    def test_load_jsonl_questions(self, mock_jsonlines, mock_exists):
        """JSONL 형식 질문 로드 테스트"""
        # Given
        mock_exists.return_value = True
        questions_data = [
            {
                "difficulty": "하",
                "question": "질문 1",
                "answer": "정답 1"
            },
            {
                "difficulty": "중",
                "question": "질문 2", 
                "answer": ["정답 2-1", "정답 2-2"]
            }
        ]
        mock_jsonlines.return_value.__enter__.return_value = questions_data
        
        # When
        file_path = Path("test_datasets/sample/queries.jsonl")
        result = self.loader._load_jsonl_questions(file_path)
        
        # Then
        assert len(result) == 2
        assert isinstance(result[0], EvaluationQuestion)
        assert result[0].question == "질문 1"
        assert isinstance(result[1].answer, list)
    
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_json_questions(self, mock_file, mock_exists):
        """JSON 형식 질문 로드 테스트"""
        # Given
        mock_exists.return_value = True
        questions_data = [
            {
                "difficulty": "하",
                "question": "JSON 질문 1",
                "answer": "JSON 정답 1"
            },
            {
                "difficulty": "상",
                "question": "JSON 질문 2",
                "answer": ["정답 2-1", "정답 2-2"]
            }
        ]
        mock_file.return_value.read.return_value = json.dumps(questions_data)
        
        # When
        file_path = Path("test_datasets/sample/questions.json")
        result = self.loader._load_json_questions(file_path)
        
        # Then
        assert len(result) == 2
        assert result[0].question == "JSON 질문 1"
        assert result[1].difficulty == DifficultyLevel.HARD
    
    @patch('pathlib.Path.iterdir')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    def test_list_datasets(self, mock_is_dir, mock_exists, mock_iterdir):
        """데이터셋 목록 조회 테스트"""
        # Given
        mock_dataset1 = MagicMock()
        mock_dataset1.name = "dataset1"
        mock_dataset1.is_dir.return_value = True
        
        mock_dataset2 = MagicMock()
        mock_dataset2.name = "dataset2"
        mock_dataset2.is_dir.return_value = True
        
        mock_file = MagicMock()
        mock_file.name = "some_file.txt"
        mock_file.is_dir.return_value = False
        
        mock_iterdir.return_value = [mock_dataset1, mock_dataset2, mock_file]
        mock_exists.return_value = True  # metadata.json 파일이 존재한다고 가정
        
        # When
        result = self.loader.list_datasets()
        
        # Then
        assert len(result) == 2
        assert "dataset1" in result
        assert "dataset2" in result
    
    @patch('pathlib.Path.exists')
    def test_list_datasets_empty_directory(self, mock_exists):
        """빈 디렉토리인 경우 데이터셋 목록 조회 테스트"""
        # Given
        mock_exists.return_value = False  # 디렉토리가 존재하지 않음
        
        # When
        result = self.loader.list_datasets()
        
        # Then
        assert result == []


@pytest.fixture
def sample_dataset_structure(tmp_path):
    """임시 데이터셋 구조 생성 fixture"""
    dataset_dir = tmp_path / "sample-dataset"
    dataset_dir.mkdir()
    
    # 메타데이터 파일 생성
    metadata = {
        "name": "Sample Dataset",
        "description": "테스트용 샘플 데이터셋",
        "version": "1.0.0",
        "language": "ko",
        "domain": "java_development",
        "query_count": 2,
        "ground_truth_format": "inline",
        "evaluation_options": {
            "convert_filepath_to_classpath": True,
            "ignore_method_names": True,
            "case_sensitive": False
        },
        "difficulty_levels": ["하", "중", "상"],
        "created_at": "2024-01-15T00:00:00Z"
    }
    
    with open(dataset_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # 질문 데이터 파일 생성 (JSONL)
    questions = [
        {
            "difficulty": "하",
            "question": "테스트 질문 1",
            "answer": "com.test.Class1"
        },
        {
            "difficulty": "중",
            "question": "테스트 질문 2",
            "answer": ["com.test.Class2", "com.test.Class3"]
        }
    ]
    
    with jsonlines.open(dataset_dir / "queries.jsonl", "w") as writer:
        for question in questions:
            writer.write(question)
    
    return tmp_path


def test_load_dataset_integration(sample_dataset_structure):
    """데이터셋 로드 통합 테스트"""
    # Given
    loader = DatasetLoader(str(sample_dataset_structure))
    
    # When
    questions, metadata = loader.load_dataset("sample-dataset")
    
    # Then
    assert len(questions) == 2
    assert metadata.name == "Sample Dataset"
    assert metadata.evaluation_options.convert_filepath_to_classpath is True
    
    # 첫 번째 질문 확인
    assert questions[0].difficulty == DifficultyLevel.EASY
    assert questions[0].question == "테스트 질문 1"
    assert questions[0].answer == "com.test.Class1"
    
    # 두 번째 질문 확인 (다중 정답)
    assert questions[1].difficulty == DifficultyLevel.MEDIUM
    assert isinstance(questions[1].answer, list)
    assert len(questions[1].answer) == 2 