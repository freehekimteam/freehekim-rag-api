PYTHON ?= python3
PIP ?= pip3
PORT ?= 8080

.PHONY: install dev-install lint format typecheck test run docker-build docker-up docker-down

install:
	$(PIP) install -r fastapi/requirements.txt

dev-install: install
	$(PIP) install -r requirements-dev.txt

lint:
	ruff check fastapi

format:
	ruff format fastapi

typecheck:
	mypy fastapi

test:
	OPENAI_API_KEY=sk-test $(PYTHON) -m pytest -v tests/

run:
	cd fastapi && $(PYTHON) -m uvicorn app:app --port $(PORT) --host 0.0.0.0 --reload

docker-build:
	docker build -f deployment/docker/Dockerfile.api -t freehekim-rag-api:dev .

docker-up:
	docker compose -f deployment/docker/docker-compose.server.yml up -d

docker-down:
	docker compose -f deployment/docker/docker-compose.server.yml down

.PHONY: wiki-publish
wiki-publish:
	bash tools/publish_wiki.sh
