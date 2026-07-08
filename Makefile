PYTHON  = venv/bin/python
PIP     = venv/bin/pip
PYTEST  = venv/bin/pytest
UVICORN = venv/bin/uvicorn
RUFF    = venv/bin/ruff

DEPLOY_HOST ?= ubuntu@$(SERVER_IP)
DEPLOY_DIR   = /opt/recipes
DEPLOY_KEY  ?= ~/.ssh/id_ed25519

-include .env
export

BUMP ?= patch

.PHONY: venv install up down test test-v lint format dev reset logs deploy release

venv:
	python3 -m venv venv

install: venv
	$(PIP) install -r requirements.txt -r requirements-dev.txt

up:
	docker compose -f docker-compose.local.yml up -d
	docker compose -f docker-compose.local.yml exec db sh -c 'until pg_isready -U postgres; do sleep 1; done'

down:
	docker compose -f docker-compose.local.yml down

test: up
	$(PYTEST) tests/ -q

test-v: up
	$(PYTEST) tests/ -v

lint:
	$(RUFF) check .
	$(RUFF) format --check .

format:
	$(RUFF) check --fix .
	$(RUFF) format .

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

release:
	@LATEST=$$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "0.0.0"); \
	NEW=$$(python3 -c "v='$$LATEST'.split('.'); m,n,p=int(v[0]),int(v[1]),int(v[2]); b='$(BUMP)'; print(f'{m+1}.0.0' if b=='major' else f'{m}.{n+1}.0' if b=='minor' else f'{m}.{n}.{p+1}')"); \
	echo "Releasing v$$NEW"; \
	git tag "v$$NEW" && git push origin "v$$NEW"
