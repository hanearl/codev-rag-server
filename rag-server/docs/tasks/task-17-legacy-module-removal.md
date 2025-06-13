# Task 17: 기존 모듈 제거 및 마이그레이션

## 📋 작업 개요
하이브리드 아키텍처 전환이 완료된 후, 기존의 분산된 features 모듈들을 제거하고 새로운 통합 시스템으로 완전히 마이그레이션합니다.

## 🎯 작업 목표
- 기존 features 모듈들의 안전한 제거
- 의존성 및 참조 코드 정리
- 데이터 마이그레이션 완료
- 시스템 안정성 검증

## 🔗 의존성
- **선행 Task**: Task 16 (통합 API 엔드포인트 구현)
- **제거할 대상**: `app/features/generation`, `app/features/indexing`, `app/features/search`, `app/features/prompts`

## 🔧 구현 사항

### 1. 마이그레이션 계획 및 검증

```python
# scripts/migration_validator.py
import os
import ast
import logging
from typing import List, Dict, Set, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class MigrationValidator:
    """마이그레이션 유효성 검증"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.legacy_modules = [
            "app.features.generation",
            "app.features.indexing", 
            "app.features.search",
            "app.features.prompts"
        ]
        self.legacy_paths = [
            "app/features/generation",
            "app/features/indexing",
            "app/features/search", 
            "app/features/prompts"
        ]
    
    def validate_migration_readiness(self) -> Dict[str, Any]:
        """마이그레이션 준비 상태 검증"""
        validation_result = {
            "ready_for_migration": True,
            "issues": [],
            "warnings": [],
            "dependencies": {},
            "file_references": {}
        }
        
        # 1. 의존성 분석
        dependencies = self._analyze_dependencies()
        validation_result["dependencies"] = dependencies
        
        # 2. 파일 참조 분석
        file_refs = self._analyze_file_references()
        validation_result["file_references"] = file_refs
        
        # 3. API 호출 분석
        api_calls = self._analyze_api_calls()
        validation_result["api_calls"] = api_calls
        
        # 4. 데이터베이스 참조 분석
        db_refs = self._analyze_database_references()
        validation_result["database_references"] = db_refs
        
        # 5. 테스트 분석
        test_refs = self._analyze_test_references()
        validation_result["test_references"] = test_refs
        
        # 6. 중요 이슈 식별
        issues = []
        if dependencies["external_dependencies"]:
            issues.append(f"외부 의존성 발견: {dependencies['external_dependencies']}")
        
        if api_calls["active_endpoints"]:
            issues.append(f"활성 API 엔드포인트: {api_calls['active_endpoints']}")
        
        if test_refs["failing_tests"]:
            issues.append(f"실패하는 테스트: {test_refs['failing_tests']}")
        
        validation_result["issues"] = issues
        validation_result["ready_for_migration"] = len(issues) == 0
        
        return validation_result
    
    def _analyze_dependencies(self) -> Dict[str, Any]:
        """코드 의존성 분석"""
        dependencies = {
            "internal_dependencies": [],
            "external_dependencies": [],
            "import_statements": []
        }
        
        # Python 파일들을 순회하면서 import 문 분석
        for py_file in self.project_root.rglob("*.py"):
            if any(legacy_path in str(py_file) for legacy_path in self.legacy_paths):
                continue  # 레거시 모듈 자체는 건너뛰기
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if any(legacy_mod in alias.name for legacy_mod in self.legacy_modules):
                                dependencies["external_dependencies"].append({
                                    "file": str(py_file),
                                    "import": alias.name,
                                    "line": node.lineno
                                })
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and any(legacy_mod in node.module for legacy_mod in self.legacy_modules):
                            dependencies["external_dependencies"].append({
                                "file": str(py_file),
                                "from": node.module,
                                "import": [alias.name for alias in node.names],
                                "line": node.lineno
                            })
            
            except Exception as e:
                logger.warning(f"파일 분석 실패 {py_file}: {e}")
        
        return dependencies
    
    def _analyze_file_references(self) -> Dict[str, Any]:
        """파일 참조 분석"""
        file_refs = {
            "hardcoded_paths": [],
            "config_references": [],
            "string_references": []
        }
        
        # 문자열에서 경로 참조 찾기
        for py_file in self.project_root.rglob("*.py"):
            if any(legacy_path in str(py_file) for legacy_path in self.legacy_paths):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    for legacy_path in self.legacy_paths:
                        if legacy_path in line and not line.strip().startswith('#'):
                            file_refs["string_references"].append({
                                "file": str(py_file),
                                "line": i + 1,
                                "content": line.strip(),
                                "reference": legacy_path
                            })
            
            except Exception as e:
                logger.warning(f"파일 내용 분석 실패 {py_file}: {e}")
        
        return file_refs
    
    def _analyze_api_calls(self) -> Dict[str, Any]:
        """API 호출 분석"""
        api_calls = {
            "active_endpoints": [],
            "router_references": []
        }
        
        # main.py에서 라우터 등록 확인
        main_file = self.project_root / "app" / "main.py"
        if main_file.exists():
            try:
                with open(main_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for legacy_path in self.legacy_paths:
                    if f"{legacy_path}/router" in content or f"{legacy_path}.router" in content:
                        api_calls["router_references"].append(legacy_path)
            
            except Exception as e:
                logger.warning(f"main.py 분석 실패: {e}")
        
        return api_calls
    
    def _analyze_database_references(self) -> Dict[str, Any]:
        """데이터베이스 참조 분석"""
        db_refs = {
            "model_references": [],
            "migration_files": [],
            "data_dependencies": []
        }
        
        # 데이터베이스 모델 파일 확인
        for model_file in self.project_root.rglob("models.py"):
            if any(legacy_path in str(model_file) for legacy_path in self.legacy_paths):
                db_refs["model_references"].append(str(model_file))
        
        # migration 폴더 확인
        for migration_dir in self.project_root.rglob("migrations"):
            if any(legacy_path in str(migration_dir) for legacy_path in self.legacy_paths):
                db_refs["migration_files"].extend([
                    str(f) for f in migration_dir.rglob("*.py")
                ])
        
        return db_refs
    
    def _analyze_test_references(self) -> Dict[str, Any]:
        """테스트 참조 분석"""
        test_refs = {
            "test_files": [],
            "failing_tests": [],
            "test_imports": []
        }
        
        # 테스트 파일들 분석
        for test_file in self.project_root.rglob("test_*.py"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for legacy_mod in self.legacy_modules:
                    if legacy_mod in content:
                        test_refs["test_files"].append(str(test_file))
                        test_refs["test_imports"].append({
                            "file": str(test_file),
                            "module": legacy_mod
                        })
            
            except Exception as e:
                logger.warning(f"테스트 파일 분석 실패 {test_file}: {e}")
        
        return test_refs
    
    def generate_migration_plan(self) -> Dict[str, Any]:
        """마이그레이션 계획 생성"""
        validation = self.validate_migration_readiness()
        
        plan = {
            "migration_steps": [],
            "risk_assessment": "LOW",
            "estimated_time": "2-4 hours",
            "rollback_plan": [],
            "validation_checks": []
        }
        
        # 마이그레이션 단계 정의
        steps = [
            {
                "step": 1,
                "description": "의존성 제거 및 import 문 수정",
                "files_affected": len(validation["dependencies"]["external_dependencies"]),
                "estimated_time": "30-60분"
            },
            {
                "step": 2, 
                "description": "라우터 등록 해제 및 API 엔드포인트 비활성화",
                "files_affected": ["app/main.py"],
                "estimated_time": "15분"
            },
            {
                "step": 3,
                "description": "레거시 모듈 디렉토리 제거",
                "files_affected": len(self.legacy_paths),
                "estimated_time": "5분"
            },
            {
                "step": 4,
                "description": "테스트 파일 정리 및 업데이트",
                "files_affected": len(validation["test_references"]["test_files"]),
                "estimated_time": "30-45분"
            },
            {
                "step": 5,
                "description": "문서 및 설정 파일 업데이트",
                "files_affected": ["README.md", "requirements.txt", "pyproject.toml"],
                "estimated_time": "15분"
            }
        ]
        
        plan["migration_steps"] = steps
        
        # 위험도 평가
        issue_count = len(validation["issues"])
        if issue_count == 0:
            plan["risk_assessment"] = "LOW"
        elif issue_count <= 2:
            plan["risk_assessment"] = "MEDIUM"
        else:
            plan["risk_assessment"] = "HIGH"
        
        # 롤백 계획
        plan["rollback_plan"] = [
            "Git을 사용한 이전 커밋으로 롤백",
            "백업된 디렉토리에서 레거시 모듈 복원",
            "라우터 등록 재활성화",
            "의존성 import 문 복원"
        ]
        
        return plan

class LegacyModuleRemover:
    """레거시 모듈 제거기"""
    
    def __init__(self, project_root: str, dry_run: bool = True):
        self.project_root = Path(project_root)
        self.dry_run = dry_run
        self.backup_dir = self.project_root / "backup" / "legacy_modules"
        self.removed_files = []
        self.modified_files = []
    
    def remove_legacy_modules(self) -> Dict[str, Any]:
        """레거시 모듈 제거 실행"""
        removal_result = {
            "success": True,
            "removed_directories": [],
            "removed_files": [],
            "modified_files": [],
            "backup_location": str(self.backup_dir),
            "errors": []
        }
        
        try:
            # 1. 백업 디렉토리 생성
            if not self.dry_run:
                self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 2. 의존성 제거
            self._remove_dependencies()
            
            # 3. 라우터 등록 해제
            self._remove_router_registrations()
            
            # 4. 레거시 디렉토리 백업 및 제거
            legacy_paths = [
                "app/features/generation",
                "app/features/indexing", 
                "app/features/search",
                "app/features/prompts"
            ]
            
            for legacy_path in legacy_paths:
                full_path = self.project_root / legacy_path
                if full_path.exists():
                    self._backup_and_remove_directory(full_path)
                    removal_result["removed_directories"].append(legacy_path)
            
            # 5. 테스트 파일 정리
            self._cleanup_test_files()
            
            # 6. 설정 파일 업데이트
            self._update_config_files()
            
            removal_result["removed_files"] = self.removed_files
            removal_result["modified_files"] = self.modified_files
            
        except Exception as e:
            removal_result["success"] = False
            removal_result["errors"].append(str(e))
            logger.error(f"레거시 모듈 제거 실패: {e}")
        
        return removal_result
    
    def _remove_dependencies(self):
        """의존성 제거"""
        legacy_modules = [
            "app.features.generation",
            "app.features.indexing", 
            "app.features.search",
            "app.features.prompts"
        ]
        
        # Python 파일들에서 import 문 제거
        for py_file in self.project_root.rglob("*.py"):
            if any(legacy_path in str(py_file) for legacy_path in ["app/features/generation", "app/features/indexing", "app/features/search", "app/features/prompts"]):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                lines = content.split('\n')
                modified_lines = []
                
                for line in lines:
                    should_remove = False
                    for legacy_mod in legacy_modules:
                        if (f"from {legacy_mod}" in line or 
                            f"import {legacy_mod}" in line):
                            should_remove = True
                            break
                    
                    if not should_remove:
                        modified_lines.append(line)
                    else:
                        logger.info(f"제거된 import: {line.strip()} in {py_file}")
                
                new_content = '\n'.join(modified_lines)
                
                if new_content != original_content:
                    if not self.dry_run:
                        with open(py_file, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                    
                    self.modified_files.append(str(py_file))
                    logger.info(f"의존성 제거됨: {py_file}")
            
            except Exception as e:
                logger.warning(f"파일 처리 실패 {py_file}: {e}")
    
    def _remove_router_registrations(self):
        """라우터 등록 해제"""
        main_file = self.project_root / "app" / "main.py"
        
        if main_file.exists():
            try:
                with open(main_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                lines = content.split('\n')
                modified_lines = []
                
                legacy_router_patterns = [
                    "generation.router",
                    "indexing.router", 
                    "search.router",
                    "prompts.router"
                ]
                
                for line in lines:
                    should_remove = False
                    for pattern in legacy_router_patterns:
                        if pattern in line and ("include_router" in line or "mount" in line):
                            should_remove = True
                            break
                    
                    if not should_remove:
                        modified_lines.append(line)
                    else:
                        logger.info(f"제거된 라우터 등록: {line.strip()}")
                
                new_content = '\n'.join(modified_lines)
                
                if new_content != original_content:
                    if not self.dry_run:
                        with open(main_file, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                    
                    self.modified_files.append(str(main_file))
                    logger.info("main.py에서 라우터 등록 제거됨")
            
            except Exception as e:
                logger.error(f"main.py 수정 실패: {e}")
    
    def _backup_and_remove_directory(self, directory_path: Path):
        """디렉토리 백업 및 제거"""
        import shutil
        
        backup_path = self.backup_dir / directory_path.name
        
        if not self.dry_run:
            # 백업
            if directory_path.exists():
                shutil.copytree(directory_path, backup_path, dirs_exist_ok=True)
                logger.info(f"백업 완료: {directory_path} -> {backup_path}")
                
                # 제거
                shutil.rmtree(directory_path)
                logger.info(f"디렉토리 제거됨: {directory_path}")
                
                self.removed_files.extend([
                    str(f) for f in backup_path.rglob("*") if f.is_file()
                ])
        else:
            logger.info(f"[DRY RUN] 백업 예정: {directory_path} -> {backup_path}")
            logger.info(f"[DRY RUN] 제거 예정: {directory_path}")
    
    def _cleanup_test_files(self):
        """테스트 파일 정리"""
        legacy_test_patterns = [
            "test_generation",
            "test_indexing", 
            "test_search",
            "test_prompts"
        ]
        
        # 레거시 테스트 파일 제거
        for test_file in self.project_root.rglob("test_*.py"):
            file_name = test_file.name
            if any(pattern in file_name for pattern in legacy_test_patterns):
                if not self.dry_run:
                    # 백업 후 제거
                    backup_file = self.backup_dir / "tests" / file_name
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    import shutil
                    shutil.copy2(test_file, backup_file)
                    test_file.unlink()
                    
                    logger.info(f"테스트 파일 제거됨: {test_file}")
                    self.removed_files.append(str(test_file))
                else:
                    logger.info(f"[DRY RUN] 테스트 파일 제거 예정: {test_file}")
    
    def _update_config_files(self):
        """설정 파일 업데이트"""
        # requirements.txt에서 불필요한 의존성 제거 (있다면)
        # pyproject.toml 업데이트 (있다면)
        # 기타 설정 파일들 정리
        
        config_files = [
            "requirements.txt",
            "pyproject.toml",
            "setup.py"
        ]
        
        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                logger.info(f"설정 파일 확인: {config_file}")
                # 필요시 특정 의존성 제거 로직 추가
```

### 2. 마이그레이션 실행 스크립트

```python
# scripts/migrate_to_hybrid.py
#!/usr/bin/env python3
"""
레거시 모듈을 하이브리드 아키텍처로 마이그레이션하는 스크립트
"""

import sys
import argparse
import logging
from pathlib import Path
from migration_validator import MigrationValidator, LegacyModuleRemover

def setup_logging(verbose: bool = False):
    """로깅 설정"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('migration.log'),
            logging.StreamHandler()
        ]
    )

def main():
    parser = argparse.ArgumentParser(description="RAG 서버 하이브리드 아키텍처 마이그레이션")
    parser.add_argument("--project-root", default=".", help="프로젝트 루트 디렉토리")
    parser.add_argument("--dry-run", action="store_true", help="실제 변경 없이 시뮬레이션만 실행")
    parser.add_argument("--force", action="store_true", help="경고 무시하고 강제 실행")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그 출력")
    parser.add_argument("--validate-only", action="store_true", help="검증만 실행")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    project_root = Path(args.project_root).resolve()
    
    logger.info(f"프로젝트 루트: {project_root}")
    logger.info(f"DRY RUN 모드: {args.dry_run}")
    
    # 1. 마이그레이션 준비 상태 검증
    logger.info("=== 마이그레이션 검증 시작 ===")
    validator = MigrationValidator(str(project_root))
    validation_result = validator.validate_migration_readiness()
    
    print("\n📋 마이그레이션 검증 결과:")
    print(f"준비 상태: {'✅ 준비됨' if validation_result['ready_for_migration'] else '❌ 준비 안됨'}")
    
    if validation_result["issues"]:
        print("\n⚠️ 발견된 이슈:")
        for issue in validation_result["issues"]:
            print(f"  - {issue}")
    
    if validation_result["dependencies"]["external_dependencies"]:
        print(f"\n🔗 외부 의존성: {len(validation_result['dependencies']['external_dependencies'])}개")
        for dep in validation_result["dependencies"]["external_dependencies"][:5]:  # 처음 5개만 표시
            print(f"  - {dep['file']}:{dep['line']} -> {dep.get('import', dep.get('from'))}")
    
    if validation_result["test_references"]["test_files"]:
        print(f"\n🧪 영향받는 테스트: {len(validation_result['test_references']['test_files'])}개")
    
    # 마이그레이션 계획 생성
    migration_plan = validator.generate_migration_plan()
    print(f"\n📅 예상 소요 시간: {migration_plan['estimated_time']}")
    print(f"📊 위험도: {migration_plan['risk_assessment']}")
    
    if args.validate_only:
        print("\n검증만 완료했습니다.")
        return 0
    
    # 2. 사용자 확인
    if not validation_result['ready_for_migration'] and not args.force:
        print("\n❌ 마이그레이션 준비가 완료되지 않았습니다.")
        print("문제를 해결한 후 다시 시도하거나 --force 옵션을 사용하세요.")
        return 1
    
    if not args.dry_run and not args.force:
        print("\n⚠️  이 작업은 기존 코드를 영구적으로 변경합니다.")
        response = input("계속하시겠습니까? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("마이그레이션이 취소되었습니다.")
            return 0
    
    # 3. 마이그레이션 실행
    logger.info("=== 마이그레이션 실행 시작 ===")
    remover = LegacyModuleRemover(str(project_root), dry_run=args.dry_run)
    removal_result = remover.remove_legacy_modules()
    
    if removal_result["success"]:
        print("\n✅ 마이그레이션이 성공적으로 완료되었습니다!")
        print(f"제거된 디렉토리: {len(removal_result['removed_directories'])}개")
        print(f"수정된 파일: {len(removal_result['modified_files'])}개")
        print(f"백업 위치: {removal_result['backup_location']}")
        
        if args.dry_run:
            print("\n📝 DRY RUN 모드였습니다. 실제 변경사항은 없습니다.")
        else:
            print("\n📋 다음 단계:")
            print("1. 애플리케이션 테스트 실행")
            print("2. 새로운 API 엔드포인트 확인")
            print("3. 통합 테스트 수행")
    else:
        print("\n❌ 마이그레이션 중 오류가 발생했습니다:")
        for error in removal_result["errors"]:
            print(f"  - {error}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 3. 마이그레이션 후 검증 테스트

```python
# tests/integration/test_migration_verification.py
import pytest
import requests
import asyncio
from pathlib import Path

class TestMigrationVerification:
    """마이그레이션 완료 후 검증 테스트"""
    
    @pytest.fixture
    def base_url(self):
        return "http://localhost:8000"
    
    def test_legacy_endpoints_removed(self, base_url):
        """레거시 엔드포인트가 제거되었는지 확인"""
        legacy_endpoints = [
            "/api/v1/generation",
            "/api/v1/indexing", 
            "/api/v1/search",
            "/api/v1/prompts"
        ]
        
        for endpoint in legacy_endpoints:
            response = requests.get(f"{base_url}{endpoint}/health")
            assert response.status_code == 404, f"레거시 엔드포인트가 여전히 활성화됨: {endpoint}"
    
    def test_new_hybrid_endpoints_active(self, base_url):
        """새로운 하이브리드 엔드포인트가 활성화되었는지 확인"""
        response = requests.get(f"{base_url}/api/v1/rag/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] in ["healthy", "degraded"]
    
    def test_hybrid_query_functionality(self, base_url):
        """하이브리드 쿼리 기능 테스트"""
        query_data = {
            "query": "JWT 인증 구현 방법",
            "language": "java",
            "task_type": "general_qa"
        }
        
        response = requests.post(f"{base_url}/api/v1/rag/query", json=query_data)
        assert response.status_code == 200
        
        result = response.json()
        assert "answer" in result
        assert "sources" in result
        assert len(result["sources"]) >= 0
    
    def test_no_legacy_imports_in_codebase(self):
        """코드베이스에 레거시 import가 없는지 확인"""
        project_root = Path(".")
        legacy_modules = [
            "app.features.generation",
            "app.features.indexing", 
            "app.features.search",
            "app.features.prompts"
        ]
        
        for py_file in project_root.rglob("*.py"):
            # 백업 디렉토리는 제외
            if "backup" in str(py_file):
                continue
                
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for legacy_mod in legacy_modules:
                assert legacy_mod not in content, f"레거시 모듈 참조 발견: {legacy_mod} in {py_file}"
    
    def test_legacy_directories_removed(self):
        """레거시 디렉토리가 제거되었는지 확인"""
        project_root = Path(".")
        legacy_paths = [
            "app/features/generation",
            "app/features/indexing", 
            "app/features/search",
            "app/features/prompts"
        ]
        
        for legacy_path in legacy_paths:
            full_path = project_root / legacy_path
            assert not full_path.exists(), f"레거시 디렉토리가 여전히 존재함: {legacy_path}"
    
    def test_backup_created(self):
        """백업이 올바르게 생성되었는지 확인"""
        backup_dir = Path("backup/legacy_modules")
        assert backup_dir.exists(), "백업 디렉토리가 생성되지 않음"
        
        # 백업된 모듈들이 있는지 확인
        expected_backups = ["generation", "indexing", "search", "prompts"]
        for module_name in expected_backups:
            module_backup = backup_dir / module_name
            assert module_backup.exists(), f"모듈 백업이 없음: {module_name}"
```

## ✅ 완료 조건

1. **안전한 제거**: 모든 레거시 모듈이 백업과 함께 안전하게 제거됨
2. **의존성 정리**: 모든 import 문과 참조가 제거됨
3. **API 정리**: 레거시 API 엔드포인트가 완전히 비활성화됨
4. **테스트 정리**: 관련 테스트 파일들이 정리됨
5. **백업 생성**: 롤백 가능한 백업이 생성됨
6. **검증 완료**: 마이그레이션 후 시스템이 정상 동작함
7. **문서 업데이트**: 관련 문서들이 업데이트됨

## 📋 다음 Task와의 연관관계

- **Task 18**: 최종 통합 테스트 및 마이그레이션 완료 검증

## 🧪 테스트 계획

```bash
# 마이그레이션 검증 실행
python scripts/migrate_to_hybrid.py --validate-only --verbose

# DRY RUN 실행
python scripts/migrate_to_hybrid.py --dry-run --verbose

# 실제 마이그레이션 실행
python scripts/migrate_to_hybrid.py --verbose

# 마이그레이션 후 검증
pytest tests/integration/test_migration_verification.py -v
```

이 Task는 하이브리드 아키텍처 전환의 마지막 단계로, 기존 시스템을 안전하게 제거하고 새로운 통합 시스템으로 완전히 전환합니다. 