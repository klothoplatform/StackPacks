PHONY: run test-backend black start clean-local test-frontend reset-backend

engineCliPath := $(shell command -v engine)
ifdef engineCliPath
export ENGINE_PATH ?= $(engineCliPath)
else
endif

iacCliPath := $(shell command -v iac)
ifdef iacCliPath
export IAC_PATH ?= $(iacCliPath)
else
endif

run:
	@echo "ENGINE_PATH: $(ENGINE_PATH)"
	@echo "IAC_PATH: $(IAC_PATH)"
	PYTHONPATH=. \
	DYNAMODB_HOST=http://localhost:8000 \
	SES_ENDPOINT=http://localhost:8005 \
	AUTH0_DOMAIN="klotho-dev.us.auth0.com" \
	AUTH0_AUDIENCE="A0sIE3wvh8LpG8mtJEjWPnBqZgBs5cNM" \
	pipenv run gunicorn -k uvicorn.workers.UvicornWorker -b 0.0.0.0:3000 --log-level debug src.main:app 

test-backend:
	PYTHONPATH=. pipenv run coverage run --source=src -m unittest discover
	PYTHONPATH=. pipenv run coverage report -m --fail-under 70

test-frontend:
	cd frontend && npm run test:unit

black:
	pipenv run black .

black-check:
	pipenv run black --check .

reset-backend:
	docker compose down --volumes --remove-orphans;\
	rm -rf ./docker/dynamodb;\
	mkdir -p ./docker/dynamodb;\
	docker compose up -d

clean-local:
	rm -rf tmp/*
	rm -rf deployments/*/

frontend/node_modules: frontend/package.json frontend/package-lock.json
	npm --prefix frontend ci

start: frontend/node_modules
	npm --prefix frontend run start

build-frontend-dev:
	npm --prefix frontend run build-dev

build-frontend-prod:
	npm --prefix frontend run build-prod

generate-dev-infra:
	PYTHONPATH=. pipenv run python scripts/cli.py iac \
		generate-iac \
		--file ./deploy/stacksnap.yaml \
		--project-name stacksnap-dev --output-dir deploy/output
	npx prettier --write deploy/output/index.ts
	cp deploy/output/index.ts ./deploy
	cp deploy/output/package.json ./deploy
