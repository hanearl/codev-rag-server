import json
import jsonlines
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import logging

from app.features.evaluation.schema import (
    EvaluationQuestion, 
    DatasetMetadata, 
    EvaluationOptions,
    DifficultyLevel
)

logger = logging.getLogger(__name__)


class DatasetLoader:
    """데이터셋 로더"""
    
    def __init__(self, datasets_root: str = "datasets"):
        """
        Args:
            datasets_root: 데이터셋 루트 디렉토리
        """
        self.datasets_root = Path(datasets_root)
    
    def load_dataset(self, dataset_name: str) -> tuple[List[EvaluationQuestion], DatasetMetadata]:
        """
        데이터셋 로드
        
        Args:
            dataset_name: 데이터셋 이름
            
        Returns:
            (질문 리스트, 메타데이터)
        """
        dataset_path = self.datasets_root / dataset_name
        
        if not dataset_path.exists():
            raise FileNotFoundError(f"데이터셋을 찾을 수 없습니다: {dataset_path}")
        
        # 메타데이터 로드
        metadata = self._load_metadata(dataset_path)
        
        # 질문 데이터 로드
        questions = self._load_questions(dataset_path, metadata)
        
        logger.info(f"데이터셋 로드 완료: {dataset_name}, 질문 수: {len(questions)}")
        
        return questions, metadata
    
    def _load_metadata(self, dataset_path: Path) -> DatasetMetadata:
        """메타데이터 로드"""
        metadata_file = dataset_path / "metadata.json"
        
        if not metadata_file.exists():
            raise FileNotFoundError(f"메타데이터 파일을 찾을 수 없습니다: {metadata_file}")
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata_dict = json.load(f)
        
        # 필드명 매핑
        mapped_metadata = {
            "name": metadata_dict.get("name", "Unknown Dataset"),
            "description": metadata_dict.get("description", ""),
            "format": metadata_dict.get("ground_truth_format", "inline"),
            "question_count": metadata_dict.get("query_count", 0),
            "created_at": metadata_dict.get("created_at", ""),
            "version": metadata_dict.get("version", "1.0")
        }
        
        # evaluation_options 처리
        if 'evaluation_options' in metadata_dict:
            eval_options = EvaluationOptions(**metadata_dict['evaluation_options'])
            mapped_metadata['evaluation_options'] = eval_options
        else:
            mapped_metadata['evaluation_options'] = EvaluationOptions()
        
        return DatasetMetadata(**mapped_metadata)
    
    def _load_questions(self, dataset_path: Path, metadata: DatasetMetadata) -> List[EvaluationQuestion]:
        """질문 데이터 로드"""
        ground_truth_format = getattr(metadata, 'ground_truth_format', 'inline')
        
        if ground_truth_format == 'inline':
            return self._load_inline_questions(dataset_path)
        elif ground_truth_format == 'binary':
            return self._load_binary_questions(dataset_path)
        else:
            raise ValueError(f"지원하지 않는 데이터셋 형식: {ground_truth_format}")
    
    def _load_inline_questions(self, dataset_path: Path) -> List[EvaluationQuestion]:
        """인라인 형식 질문 로드 (새로운 형식)"""
        questions = []
        
        # queries.jsonl 파일 우선 시도
        queries_file = dataset_path / "queries.jsonl"
        
        if queries_file.exists():
            questions.extend(self._load_jsonl_questions(queries_file))
        else:
            # 다른 파일들 시도
            json_files = [
                dataset_path / "questions.jsonl",
                dataset_path / "data.jsonl", 
                dataset_path / "dataset.jsonl"
            ]
            
            for file_path in json_files:
                if file_path.exists():
                    questions.extend(self._load_jsonl_questions(file_path))
                    break
            else:
                # JSON 파일들 시도
                json_files = [
                    dataset_path / "questions.json",
                    dataset_path / "data.json",
                    dataset_path / "dataset.json"
                ]
                
                for file_path in json_files:
                    if file_path.exists():
                        questions.extend(self._load_json_questions(file_path))
                        break
                else:
                    raise FileNotFoundError(f"질문 데이터 파일을 찾을 수 없습니다: {dataset_path}")
        
        return questions
    
    def _load_jsonl_questions(self, file_path: Path) -> List[EvaluationQuestion]:
        """JSONL 형식 질문 로드"""
        questions = []
        
        with jsonlines.open(file_path, 'r') as reader:
            for item in reader:
                question = self._parse_question_item(item)
                if question:
                    questions.append(question)
        
        return questions
    
    def _load_json_questions(self, file_path: Path) -> List[EvaluationQuestion]:
        """JSON 형식 질문 로드"""
        questions = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 리스트인지 확인
        if isinstance(data, list):
            for item in data:
                question = self._parse_question_item(item)
                if question:
                    questions.append(question)
        else:
            raise ValueError(f"JSON 파일은 리스트 형태여야 합니다: {file_path}")
        
        return questions
    
    def _parse_question_item(self, item: Dict[str, Any]) -> Optional[EvaluationQuestion]:
        """질문 아이템 파싱"""
        try:
            # 필수 필드 확인
            if 'question' not in item or 'answer' not in item:
                logger.warning(f"필수 필드가 누락된 질문 아이템: {item}")
                return None
            
            # 난이도 처리
            difficulty = item.get('difficulty', '하')
            if difficulty not in ['하', '중', '상']:
                logger.warning(f"올바르지 않은 난이도: {difficulty}, 기본값 '하'로 설정")
                difficulty = '하'
            
            # 정답 처리 - 문자열 또는 리스트
            answer = item['answer']
            if isinstance(answer, str):
                # 단일 문자열인 경우 그대로 사용
                pass
            elif isinstance(answer, list):
                # 리스트인 경우 그대로 사용
                pass
            else:
                logger.warning(f"올바르지 않은 answer 형식: {type(answer)}")
                return None
            
            return EvaluationQuestion(
                difficulty=DifficultyLevel(difficulty),
                question=item['question'],
                answer=answer
            )
            
        except Exception as e:
            logger.error(f"질문 아이템 파싱 오류: {e}, 아이템: {item}")
            return None
    
    def _load_binary_questions(self, dataset_path: Path) -> List[EvaluationQuestion]:
        """바이너리 형식 질문 로드 (기존 형식)"""
        # 기존 구현은 여기서 하지만, 새로운 형식을 우선 지원
        raise NotImplementedError("바이너리 형식은 아직 구현되지 않았습니다")
    
    def list_datasets(self) -> List[str]:
        """사용 가능한 데이터셋 목록 반환"""
        datasets = []
        
        if not self.datasets_root.exists():
            return datasets
        
        for item in self.datasets_root.iterdir():
            if item.is_dir() and (item / "metadata.json").exists():
                datasets.append(item.name)
        
        return datasets
    
    def get_dataset_info(self, dataset_name: str) -> Optional[DatasetMetadata]:
        """데이터셋 정보 조회"""
        try:
            dataset_path = self.datasets_root / dataset_name
            return self._load_metadata(dataset_path)
        except Exception as e:
            logger.error(f"데이터셋 정보 조회 오류: {e}")
            return None


def create_default_dataset_loader() -> DatasetLoader:
    """기본 데이터셋 로더 생성"""
    return DatasetLoader("datasets") 