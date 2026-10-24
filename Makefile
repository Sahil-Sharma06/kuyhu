PY := $(CURDIR)/backend/.venv/bin/python
ifeq ($(OS),Windows_NT)
PY := $(CURDIR)/backend/.venv/Scripts/python
endif

.PHONY: all install fetch-data backend frontend test test-backend test-frontend coverage lint e2e lighthouse audit docker docker-test verify-clone sanity integration

## all: everything CI runs (lint, unit/API/data tests + coverage, frontend tests + build, e2e, docker)
all: lint test e2e docker-test

install:
	python -m venv backend/.venv
	$(PY) -m pip install -r backend/requirements-dev.txt
	npm ci --prefix frontend
	cd frontend && npx playwright install chromium

fetch-data:
	cd backend && $(PY) scripts/fetch_data.py

backend:
	cd backend && $(PY) -m uvicorn app.main:app --reload --port 8000

frontend:
	npm run dev --prefix frontend

test: test-backend test-frontend

test-backend: coverage

coverage:
	cd backend && $(PY) -m pytest --cov --cov-report=term
	cd backend && PATH="$(dir $(PY)):$$PATH" bash scripts/check_core_coverage.sh

test-frontend:
	npm test --prefix frontend
	npm run typecheck --prefix frontend
	npm run build --prefix frontend
	npm run size --prefix frontend

lint:
	cd backend && $(PY) -m ruff check . ../api && $(PY) -m ruff format --check . ../api
	npm run lint --prefix frontend

e2e:
	cd frontend && PYTHON="$(PY)" npx playwright test

lighthouse:
	npm run lhci --prefix frontend

audit:
	cd backend && $(PY) -m pip_audit -r requirements.txt
	npm audit --prefix frontend

integration:
	cd backend && $(PY) -m pytest -m integration

sanity:
	cd backend && $(PY) scripts/sanity_check.py

docker:
	docker compose up --build

docker-test:
	bash scripts/verify_clean_clone.sh

verify-clone: docker-test
