.PHONY: up down build test logs clean init-db

# 개발 환경 시작
up:
	docker-compose -f docker-compose.dev.yml up -d

# 프로덕션 환경 시작
up-prod:
	docker-compose up -d

# 서비스 중지
down:
	docker-compose -f docker-compose.dev.yml down

# 프로덕션 서비스 중지
down-prod:
	docker-compose down

# 이미지 빌드
build:
	docker-compose -f docker-compose.dev.yml build

# 프로덕션 이미지 빌드
build-prod:
	docker-compose build

# 통합 테스트 실행
test-integration:
	pytest tests/integration/ -v

# 모든 테스트 실행
test:
	pytest tests/ -v

# 로그 확인
logs:
	docker-compose -f docker-compose.dev.yml logs -f

# 특정 서비스 로그
logs-embedding:
	docker-compose -f docker-compose.dev.yml logs -f embedding-server

logs-llm:
	docker-compose -f docker-compose.dev.yml logs -f llm-server

logs-vector:
	docker-compose -f docker-compose.dev.yml logs -f vector-db

logs-rag:
	docker-compose -f docker-compose.dev.yml logs -f rag-server

# 데이터베이스 초기화
init-db:
	cd vector-db && python scripts/init_collections.py

# 환경 정리
clean:
	docker-compose -f docker-compose.dev.yml down -v
	docker system prune -f

# 전체 재시작
restart: down up

# 헬스체크
health:
	@echo "🔍 서비스 헬스체크..."
	@curl -f http://localhost:6333/health && echo "✅ Vector DB 정상" || echo "❌ Vector DB 오류"
	@curl -f http://localhost:8001/health && echo "✅ Embedding Server 정상" || echo "❌ Embedding Server 오류"
	@curl -f http://localhost:8002/health && echo "✅ LLM Server 정상" || echo "❌ LLM Server 오류"
	@curl -f http://localhost:8000/health && echo "✅ RAG Server 정상" || echo "❌ RAG Server 오류"

# 개발 환경 설정
setup-dev:
	@echo "🚀 개발 환경 설정 시작..."
	@if [ ! -f .env ]; then echo "❌ .env 파일이 없습니다. env.example을 참고하여 생성해주세요."; exit 1; fi
	@docker-compose -f docker-compose.dev.yml config > /dev/null && echo "✅ Docker Compose 설정 검증 완료"
	@make up
	@echo "⏳ 서비스 시작 대기 중..."
	@sleep 30
	@make health
	@echo "✅ 개발 환경 설정 완료!"

# 백업
backup:
	cd vector-db && python scripts/backup.py

# 도움말
help:
	@echo "사용 가능한 명령어:"
	@echo "  up              - 개발 환경 시작"
	@echo "  up-prod         - 프로덕션 환경 시작"
	@echo "  down            - 개발 환경 중지"
	@echo "  down-prod       - 프로덕션 환경 중지"
	@echo "  build           - 개발 이미지 빌드"
	@echo "  build-prod      - 프로덕션 이미지 빌드"
	@echo "  test            - 모든 테스트 실행"
	@echo "  test-integration - 통합 테스트 실행"
	@echo "  logs            - 모든 서비스 로그"
	@echo "  logs-[service]  - 특정 서비스 로그"
	@echo "  init-db         - 데이터베이스 초기화"
	@echo "  clean           - 환경 정리"
	@echo "  restart         - 전체 재시작"
	@echo "  health          - 헬스체크"
	@echo "  setup-dev       - 개발 환경 설정"
	@echo "  backup          - 데이터 백업"
	@echo "  help            - 도움말" 