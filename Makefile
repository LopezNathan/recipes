PYTHON  = venv/bin/python
PIP     = venv/bin/pip
PYTEST  = venv/bin/pytest
UVICORN = venv/bin/uvicorn

-include .env
export

.PHONY: venv install up down test test-v dev reset logs

venv:
	python3 -m venv venv

install: venv
	$(PIP) install -r requirements.txt

up:
	docker compose up -d
	docker compose exec db sh -c 'until pg_isready -U postgres; do sleep 1; done'

down:
	docker compose down

test: up
	$(PYTEST) tests/ -q

test-v: up
	$(PYTEST) tests/ -v

dev: up
	$(UVICORN) main:app --reload

reset:
	docker compose down -v
	docker compose up -d
	docker compose exec db sh -c 'until pg_isready -U postgres; do sleep 1; done'

logs:
	docker compose logs -f db
