import os
import json
import jsonlines
from typing import Dict, List, Any, Set
from pathlib import Path
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ValidationReport(BaseModel):
    """검증 보고서"""
    dataset_name: str
    is_valid: bool
    file_checks: Dict[str, bool]
    format_errors: List[str]
    consistency_errors: List[str]
    statistics: Dict[str, Any]


class DatasetValidator:
    """데이터셋 검증기"""
    
    def __init__(self):
        self.required_files = ['metadata.json']
        self.optional_data_files = ['queries.jsonl', 'questions.json', 'data.json']
        self.required_metadata_fields = ['name', 'format']
        self.required_question_fields = ['question', 'answer', 'difficulty']
    
    def validate_dataset(self, dataset_path: str) -> ValidationReport:
        """
        데이터셋 전체 검증
        
        Args:
            dataset_path: 데이터셋 디렉토리 경로
            
        Returns:
            검증 보고서
        """
        dataset_name = Path(dataset_path).name
        
        try:
            # 파일 존재 확인
            file_checks = self._check_required_files(dataset_path)
            
            # 데이터 형식 검증
            format_errors = self._check_data_format(dataset_path)
            
            # 데이터 일관성 검증
            consistency_errors = self._check_data_consistency(dataset_path)
            
            # 통계 정보 수집
            statistics = self._collect_statistics(dataset_path)
            
            is_valid = (
                all(file_checks.values()) and 
                len(format_errors) == 0 and 
                len(consistency_errors) == 0
            )
            
            return ValidationReport(
                dataset_name=dataset_name,
                is_valid=is_valid,
                file_checks=file_checks,
                format_errors=format_errors,
                consistency_errors=consistency_errors,
                statistics=statistics
            )
            
        except Exception as e:
            logger.error(f"데이터셋 검증 중 오류: {str(e)}")
            return ValidationReport(
                dataset_name=dataset_name,
                is_valid=False,
                file_checks={},
                format_errors=[f"검증 중 오류 발생: {str(e)}"],
                consistency_errors=[],
                statistics={}
            )
    
    def _check_required_files(self, dataset_path: str) -> Dict[str, bool]:
        """필수 파일 존재 확인"""
        checks = {}
        
        # 필수 파일 확인
        for file in self.required_files:
            checks[file] = os.path.exists(os.path.join(dataset_path, file))
        
        # 데이터 파일 중 하나 이상 있는지 확인
        data_files_exist = any(
            os.path.exists(os.path.join(dataset_path, file)) 
            for file in self.optional_data_files
        )
        checks['data_file'] = data_files_exist
        
        return checks
    
    def _check_data_format(self, dataset_path: str) -> List[str]:
        """데이터 형식 검증"""
        errors = []
        
        # metadata.json 형식 확인
        metadata_path = os.path.join(dataset_path, "metadata.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                errors.append(f"metadata.json format error: {str(e)}")
            except Exception as e:
                errors.append(f"metadata.json read error: {str(e)}")
        
        # 데이터 파일들 형식 확인
        for data_file in self.optional_data_files:
            file_path = os.path.join(dataset_path, data_file)
            if os.path.exists(file_path):
                try:
                    if data_file.endswith('.json'):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            json.load(f)
                    elif data_file.endswith('.jsonl'):
                        with jsonlines.open(file_path, 'r') as reader:
                            # 첫 번째 줄만 읽어서 형식 확인
                            for line in reader:
                                break
                except json.JSONDecodeError as e:
                    errors.append(f"{data_file} format error: {str(e)}")
                except Exception as e:
                    errors.append(f"{data_file} read error: {str(e)}")
        
        return errors
    
    def _check_data_consistency(self, dataset_path: str) -> List[str]:
        """데이터 일관성 검증"""
        errors = []
        
        try:
            # 메타데이터 로딩
            metadata_path = os.path.join(dataset_path, "metadata.json")
            metadata = None
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except:
                    return errors  # 형식 오류는 이미 _check_data_format에서 처리됨
            
            # 메타데이터 필수 필드 확인
            if metadata:
                for field in self.required_metadata_fields:
                    if field not in metadata:
                        errors.append(f"Missing required metadata field: {field}")
            
            # 데이터 파일 로딩 및 검증
            questions_data = self._load_questions_data(dataset_path)
            
            if questions_data:
                # 필수 필드 확인
                for idx, question in enumerate(questions_data):
                    for field in self.required_question_fields:
                        if field not in question:
                            errors.append(f"Question {idx}: missing required field '{field}'")
                
                # 중복 질문 확인
                questions_set: Set[str] = set()
                for idx, question in enumerate(questions_data):
                    if 'question' in question:
                        q_text = question['question'].strip().lower()
                        if q_text in questions_set:
                            errors.append(f"Duplicate question found at index {idx}: '{question['question']}'")
                        questions_set.add(q_text)
                
                # 메타데이터와 실제 데이터 수 비교
                if metadata and 'question_count' in metadata:
                    expected_count = metadata['question_count']
                    actual_count = len(questions_data)
                    if expected_count != actual_count:
                        errors.append(
                            f"Question count mismatch: metadata says {expected_count}, "
                            f"but found {actual_count} questions"
                        )
        
        except Exception as e:
            errors.append(f"Consistency check error: {str(e)}")
        
        return errors
    
    def _collect_statistics(self, dataset_path: str) -> Dict[str, Any]:
        """통계 정보 수집"""
        stats = {
            'question_count': 0,
            'difficulty_distribution': {},
            'average_question_length': 0,
            'average_answer_length': 0,
            'file_sizes': {}
        }
        
        try:
            # 파일 크기 정보
            for file in self.required_files + self.optional_data_files:
                file_path = os.path.join(dataset_path, file)
                if os.path.exists(file_path):
                    stats['file_sizes'][file] = os.path.getsize(file_path)
            
            # 질문 데이터 통계
            questions_data = self._load_questions_data(dataset_path)
            
            if questions_data:
                stats['question_count'] = len(questions_data)
                
                # 난이도 분포
                difficulty_count = {}
                question_lengths = []
                answer_lengths = []
                
                for question in questions_data:
                    # 난이도 분포
                    if 'difficulty' in question:
                        difficulty = question['difficulty']
                        difficulty_count[difficulty] = difficulty_count.get(difficulty, 0) + 1
                    
                    # 질문 길이
                    if 'question' in question:
                        question_lengths.append(len(question['question']))
                    
                    # 답변 길이
                    if 'answer' in question:
                        if isinstance(question['answer'], list):
                            # 답변이 리스트인 경우 첫 번째 답변 길이
                            answer_lengths.append(len(str(question['answer'][0])) if question['answer'] else 0)
                        else:
                            answer_lengths.append(len(str(question['answer'])))
                
                stats['difficulty_distribution'] = difficulty_count
                
                if question_lengths:
                    stats['average_question_length'] = sum(question_lengths) / len(question_lengths)
                
                if answer_lengths:
                    stats['average_answer_length'] = sum(answer_lengths) / len(answer_lengths)
        
        except Exception as e:
            logger.warning(f"통계 수집 중 오류: {str(e)}")
        
        return stats
    
    def _load_questions_data(self, dataset_path: str) -> List[Dict[str, Any]]:
        """질문 데이터 로딩"""
        questions_data = []
        
        # JSON 파일 확인
        for data_file in ['questions.json', 'data.json']:
            file_path = os.path.join(dataset_path, data_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            questions_data.extend(data)
                        elif isinstance(data, dict) and 'questions' in data:
                            questions_data.extend(data['questions'])
                        else:
                            questions_data.append(data)
                except Exception as e:
                    logger.warning(f"{data_file} 로딩 실패: {str(e)}")
        
        # JSONL 파일 확인
        for data_file in ['queries.jsonl']:
            file_path = os.path.join(dataset_path, data_file)
            if os.path.exists(file_path):
                try:
                    with jsonlines.open(file_path, 'r') as reader:
                        for line in reader:
                            questions_data.append(line)
                except Exception as e:
                    logger.warning(f"{data_file} 로딩 실패: {str(e)}")
        
        return questions_data 