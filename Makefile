PY := backend/.venv/bin/python
ifeq ($(OS),Windows_NT)
PY := backend/.venv/Scripts/python
endif

.PHONY: install fetch-data backend frontend test lint sanity docker

install:
	python -m venv backend/.venv
	$(PY) -m pip install -r backend/requirements-dev.txt
	npm ci --prefix frontend

fetch-data:
	cd backend && ../$(PY) scripts/fetch_data.py

backend:
	cd backend && ../$(PY) -m uvicorn app.main:app --reload --port 8000

frontend:
	npm run dev --prefix frontend

test:
	cd backend && ../$(PY) -m pytest
	npm test --prefix frontend

lint:
	cd backend && ../$(PY) -m ruff check . && ../$(PY) -m ruff format --check .
	npm run lint --prefix frontend

sanity:
	cd backend && ../$(PY) scripts/sanity_check.py

docker:
	docker compose up --build
