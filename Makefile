.PHONY: help install lint format typecheck test run migrate revision up down logs backup

help:
	@echo "install    - установить зависимости (editable + dev)"
	@echo "lint       - проверка ruff"
	@echo "format     - автоформатирование ruff + black"
	@echo "typecheck  - проверка mypy"
	@echo "test       - запустить pytest"
	@echo "run        - запустить бота локально"
	@echo "migrate    - применить миграции (alembic upgrade head)"
	@echo "revision   - создать автогенерируемую ревизию (m=\"...\")"
	@echo "up/down    - docker compose up -d / down"

install:
	pip install -e ".[dev]"

lint:
	ruff check .

format:
	ruff check . --fix
	black .

typecheck:
	mypy app

test:
	pytest

run:
	python -m app

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "$(m)"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f bot

backup:
	docker compose exec bot python -c "import asyncio; from app.config import get_settings; from app.services.backup import BackupService; asyncio.run(BackupService(get_settings()).create())"
