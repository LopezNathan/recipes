PYTHON  = venv/bin/python
PIP     = venv/bin/pip
PYTEST  = venv/bin/pytest
UVICORN = venv/bin/uvicorn

DEPLOY_HOST ?= ubuntu@$(SERVER_IP)
DEPLOY_DIR   = /opt/recipes
DEPLOY_KEY  ?= ~/.ssh/id_ed25519

-include .env
export

.PHONY: venv install up down test test-v dev reset logs deploy

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

deploy:
	rsync -az -e "ssh -i $(DEPLOY_KEY)" --exclude='.git' --exclude='venv' --exclude='__pycache__' \
		--exclude='*.pyc' --exclude='.env' --exclude='infra' --exclude='tests' \
		. $(DEPLOY_HOST):$(DEPLOY_DIR)
	ssh -i $(DEPLOY_KEY) $(DEPLOY_HOST) 'cd $(DEPLOY_DIR) && sudo docker compose -f docker-compose.prod.yml up -d --build --remove-orphans'
