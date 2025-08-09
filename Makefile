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

deploy-web-tag:
	cd ${WEB_PATH} && git fetch --tags && git checkout v$(tag)
	make down
	docker compose build web
	make up
	make docker-clear
