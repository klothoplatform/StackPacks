PHONY: run test-backend black start clean-local test-frontend reset-backend dockergen-local dockergen-dev dockergen-prod dockergen-whatif

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
	AWS_ACCOUNT=338991950301 \
	pipenv run gunicorn --timeout 0 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:3000 --log-level debug src.main:app

test-backend:
	PYTHONPATH=. pipenv run coverage run --source=src -m unittest discover
	PYTHONPATH=. pipenv run coverage report -m --fail-under 60

test-frontend:
	cd frontend && npm run test:unit

black:
	pipenv run black .

black-check:
	pipenv run black --check .

reset-backend: clean-local
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

generate-personal-infra:
	PYTHONPATH=. pipenv run python scripts/cli.py iac \
		generate-iac \
		--file ./personal/stacksnap.yaml \
		--project-name stacksnap-personal --output-dir personal/output
	npx prettier --write personal/output/index.ts
	cp personal/output/Pulumi* ./personal
	cp personal/output/index.ts ./personal
	cp personal/output/package.json ./personal
	cp deploy/container_start.sh personal
	cp deploy/Dockerfile personal
	
deploy-personal-infra:
	if [ -z "$(REGION)" ]; then echo "REGION is not set"; exit 1; fi
	if [ -z "$(PULUMI_ACCESS_TOKEN)" ]; then echo "PULUMI_ACCESS_TOKEN is not set"; exit 1; fi
	if [ -z "$(STACK_NAME)" ]; then echo "STACK_NAME is not set"; exit 1; fi
	if [ -z "$(KLOTHO_DIR)" ]; then echo "KLOTHO_DIR is not set"; exit 1; fi
	
	pipenv requirements > requirements.txt

	cd personal && \
	npm i && \
	pulumi config set aws:region $(REGION) -s $(STACK_NAME)  && \
	pulumi up --yes  -s $(STACK_NAME)


	make frontend/node_modules
	make build-frontend-dev
	aws s3 sync frontend/dist/ s3://$(shell cd personal && pulumi stack output stacksnap_ui_BucketName -s $(STACK_NAME)) --region $(REGION)

    
	cd $(KLOTHO_DIR) && CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o binaries/engine -ldflags="-s -w" ./cmd/engine
	cd $(KLOTHO_DIR) && CGO_ENABLED=1 GOOS=linux GOARCH=amd64 CC="zig cc -target x86_64-linux-musl" CXX="zig c++ -target x86_64-linux-musl" go build --tags extended -o binaries/iac -ldflags="-s -w" ./cmd/iac
	cd $(KLOTHO_DIR) && aws s3 sync binaries/ s3://$(shell cd personal && pulumi stack output stacksnap_binaries_BucketName -s $(STACK_NAME)) --region $(REGION)

	aws secretsmanager put-secret-value --secret-id stacksnap-pulumi-access-token --secret-string "$(PULUMI_ACCESS_TOKEN)" --region $(REGION)

	cd personal && \
	pulumi up --yes -s $(STACK_NAME)

dockergen-local:
	PYTHONPATH=. pipenv run python scripts/cli.py docker-images generate \
		--repo-suffix="-$(whoami)" \
		--output-dir="./docker_images/local"

dockergen-dev:
	PYTHONPATH=. pipenv run python scripts/cli.py docker-images generate \
		--output-dir="./docker_images/dev"

dockergen-prod:
	PYTHONPATH=. pipenv run python scripts/cli.py docker-images generate \
		--output-dir="./docker_images/prod"

dockergen-whatif:
	PYTHONPATH=. pipenv run python scripts/cli.py docker-images generate \
		--output-dir="./docker_images/whatif" \
		--whatif