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
	docker compose -f docker-compose.local.yml up -d
	docker compose -f docker-compose.local.yml exec db sh -c 'until pg_isready -U postgres; do sleep 1; done'

down:
	docker compose -f docker-compose.local.yml down

test: up
	$(PYTEST) tests/ -q

test-v: up
	$(PYTEST) tests/ -v

dev: up
	$(UVICORN) main:app --reload

reset:
	docker compose -f docker-compose.local.yml down -v
	docker compose -f docker-compose.local.yml up -d
	docker compose -f docker-compose.local.yml exec db sh -c 'until pg_isready -U postgres; do sleep 1; done'

logs:
	docker compose -f docker-compose.local.yml logs -f db

deploy:
	rsync -az -e "ssh -i $(DEPLOY_KEY)" --exclude='.git' --exclude='venv' --exclude='__pycache__' \
		--exclude='*.pyc' --exclude='.env' --exclude='infra' --exclude='tests' \
		. $(DEPLOY_HOST):$(DEPLOY_DIR)
	ssh -i $(DEPLOY_KEY) $(DEPLOY_HOST) 'cd $(DEPLOY_DIR) && sudo docker compose pull && sudo docker compose up -d --remove-orphans'
