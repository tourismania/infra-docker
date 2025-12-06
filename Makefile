include .env

docker-pull:
	docker compose pull

docker-up:
	docker compose up -d

docker-down:
	docker compose down --remove-orphans

docker-build:
	docker compose build

docker-down-clear:
	docker compose down -v --remove-orphans

docker-clear:
	docker system prune -af

up: docker-up
down: docker-down
restart: down up
build: docker-down docker-build

# example: make deploy-infra TAG=v2.0.2
deploy-infra:
	git fetch --tags
	git checkout $(TAG)

deploy-web-tag:
	cd ${WEB_PATH} && git fetch --tags && git checkout $(tag)
	make down
	docker compose build web
	make up
	make docker-clear

deploy-api-tag:
	cd ${API_PATH} && git fetch --tags && git checkout $(TAG)
	cp ${API_PATH}/.env.production.local ./services/api/envs/.env
	docker compose build api
	docker compose up -d api
	make docker-clear

cd
