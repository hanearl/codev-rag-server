import pytest
import os
import tempfile
import json
import jsonlines
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from app.features.datasets.validator import DatasetValidator, ValidationReport


class TestDatasetValidator:
    """데이터셋 검증기 테스트"""
    
    @pytest.fixture
    def dataset_validator(self):
        """데이터셋 검증기 인스턴스"""
        return DatasetValidator()
    
    @pytest.fixture
    def temp_dataset_dir(self):
        """임시 데이터셋 디렉토리"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_validate_dataset_should_return_valid_report_when_all_files_exist(
        self, dataset_validator, temp_dataset_dir
    ):
        """모든 필수 파일이 존재할 때 유효한 보고서를 반환해야 함"""
        # Given
        # 필수 파일 생성
        metadata = {
            "name": "test-dataset",
            "description": "Test dataset",
            "format": "jsonl",
            "question_count": 2,
            "version": "1.0"
        }
        
        with open(Path(temp_dataset_dir) / "metadata.json", "w") as f:
            json.dump(metadata, f)
        
        # 데이터 파일 생성
        questions = [
            {"question": "What is Python?", "answer": "Programming language", "difficulty": "easy"},
            {"question": "What is FastAPI?", "answer": "Web framework", "difficulty": "medium"}
        ]
        
        with open(Path(temp_dataset_dir) / "questions.json", "w") as f:
            json.dump(questions, f)
        
        # When
        result = dataset_validator.validate_dataset(temp_dataset_dir)
        
        # Then
        assert isinstance(result, ValidationReport)
        assert result.is_valid == True
        assert result.file_checks["metadata.json"] == True
        assert result.file_checks["data_file"] == True
        assert len(result.format_errors) == 0
        assert len(result.consistency_errors) == 0
        assert result.statistics["question_count"] == 2

    def test_validate_dataset_should_return_invalid_report_when_metadata_missing(
        self, dataset_validator, temp_dataset_dir
    ):
        """메타데이터 파일이 없을 때 무효한 보고서를 반환해야 함"""
        # Given
        # 데이터 파일만 생성
        questions = [{"question": "test", "answer": "test", "difficulty": "easy"}]
        with open(Path(temp_dataset_dir) / "questions.json", "w") as f:
            json.dump(questions, f)
        
        # When
        result = dataset_validator.validate_dataset(temp_dataset_dir)
        
        # Then
        assert result.is_valid == False
        assert result.file_checks["metadata.json"] == False
        assert result.file_checks["data_file"] == True

    def test_validate_dataset_should_return_invalid_report_when_no_data_files(
        self, dataset_validator, temp_dataset_dir
    ):
        """데이터 파일이 없을 때 무효한 보고서를 반환해야 함"""
        # Given
        # 메타데이터만 생성
        metadata = {"name": "test", "version": "1.0"}
        with open(Path(temp_dataset_dir) / "metadata.json", "w") as f:
            json.dump(metadata, f)
        
        # When
        result = dataset_validator.validate_dataset(temp_dataset_dir)
        
        # Then
        assert result.is_valid == False
        assert result.file_checks["metadata.json"] == True
        assert result.file_checks["data_file"] == False

    def test_validate_dataset_should_detect_json_format_errors(
        self, dataset_validator, temp_dataset_dir
    ):
        """JSON 형식 오류를 감지해야 함"""
        # Given
        # 유효하지 않은 JSON 파일 생성
        with open(Path(temp_dataset_dir) / "metadata.json", "w") as f:
            f.write('{"invalid": json}')  # 잘못된 JSON
        
        with open(Path(temp_dataset_dir) / "questions.json", "w") as f:
            f.write('[{"question": "test"}]')  # 유효한 JSON
        
        # When
        result = dataset_validator.validate_dataset(temp_dataset_dir)
        
        # Then
        assert result.is_valid == False
        assert len(result.format_errors) > 0
        assert any("metadata.json" in error for error in result.format_errors)

    def test_validate_dataset_should_detect_missing_required_fields(
        self, dataset_validator, temp_dataset_dir
    ):
        """필수 필드 누락을 감지해야 함"""
        # Given
        # 필수 필드가 누락된 메타데이터
        metadata = {"name": "test"}  # description, format 등 누락
        with open(Path(temp_dataset_dir) / "metadata.json", "w") as f:
            json.dump(metadata, f)
        
        # 필수 필드가 누락된 질문 데이터
        questions = [{"question": "test"}]  # answer, difficulty 누락
        with open(Path(temp_dataset_dir) / "questions.json", "w") as f:
            json.dump(questions, f)
        
        # When
        result = dataset_validator.validate_dataset(temp_dataset_dir)
        
        # Then
        assert result.is_valid == False
        assert len(result.consistency_errors) > 0

    def test_validate_dataset_should_handle_jsonl_format(
        self, dataset_validator, temp_dataset_dir
    ):
        """JSONL 형식을 올바르게 처리해야 함"""
        # Given
        metadata = {
            "name": "test-dataset",
            "format": "jsonl",
            "question_count": 2
        }
        with open(Path(temp_dataset_dir) / "metadata.json", "w") as f:
            json.dump(metadata, f)
        
        # JSONL 파일 생성
        jsonl_file = Path(temp_dataset_dir) / "queries.jsonl"
        with jsonlines.open(jsonl_file, "w") as writer:
            writer.write({"question": "What is Python?", "answer": "Language", "difficulty": "easy"})
            writer.write({"question": "What is FastAPI?", "answer": "Framework", "difficulty": "medium"})
        
        # When
        result = dataset_validator.validate_dataset(temp_dataset_dir)
        
        # Then
        assert result.is_valid == True
        assert result.file_checks["data_file"] == True
        assert result.statistics["question_count"] == 2

    def test_validate_dataset_should_detect_count_mismatch(
        self, dataset_validator, temp_dataset_dir
    ):
        """메타데이터의 질문 수와 실제 질문 수 불일치를 감지해야 함"""
        # Given
        metadata = {
            "name": "test-dataset",
            "question_count": 5,  # 실제와 다른 수
            "format": "json"
        }
        with open(Path(temp_dataset_dir) / "metadata.json", "w") as f:
            json.dump(metadata, f)
        
        questions = [
            {"question": "test1", "answer": "answer1", "difficulty": "easy"},
            {"question": "test2", "answer": "answer2", "difficulty": "medium"}
        ]  # 실제로는 2개
        with open(Path(temp_dataset_dir) / "questions.json", "w") as f:
            json.dump(questions, f)
        
        # When
        result = dataset_validator.validate_dataset(temp_dataset_dir)
        
        # Then
        assert result.is_valid == False
        assert len(result.consistency_errors) > 0
        assert any("count mismatch" in error.lower() for error in result.consistency_errors)

    def test_collect_statistics_should_return_correct_stats_when_valid_data(
        self, dataset_validator, temp_dataset_dir
    ):
        """유효한 데이터로 통계 수집 시 올바른 통계를 반환해야 함"""
        # Given
        questions = [
            {"question": "easy1", "answer": "answer1", "difficulty": "easy"},
            {"question": "easy2", "answer": "answer2", "difficulty": "easy"},
            {"question": "medium1", "answer": "answer3", "difficulty": "medium"},
            {"question": "hard1", "answer": "answer4", "difficulty": "hard"}
        ]
        with open(Path(temp_dataset_dir) / "questions.json", "w") as f:
            json.dump(questions, f)
        
        # When
        stats = dataset_validator._collect_statistics(temp_dataset_dir)
        
        # Then
        assert stats["question_count"] == 4
        assert stats["difficulty_distribution"]["easy"] == 2
        assert stats["difficulty_distribution"]["medium"] == 1
        assert stats["difficulty_distribution"]["hard"] == 1
        assert stats["average_question_length"] > 0
        assert stats["average_answer_length"] > 0

    def test_check_data_consistency_should_detect_duplicate_questions(
        self, dataset_validator, temp_dataset_dir
    ):
        """중복된 질문을 감지해야 함"""
        # Given
        questions = [
            {"question": "What is Python?", "answer": "Language", "difficulty": "easy"},
            {"question": "What is Python?", "answer": "Different answer", "difficulty": "medium"},  # 중복
            {"question": "What is Java?", "answer": "Language", "difficulty": "easy"}
        ]
        with open(Path(temp_dataset_dir) / "questions.json", "w") as f:
            json.dump(questions, f)
        
        # When
        errors = dataset_validator._check_data_consistency(temp_dataset_dir)
        
        # Then
        assert len(errors) > 0
        assert any("duplicate" in error.lower() for error in errors) 