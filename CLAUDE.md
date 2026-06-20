# Agent Context — Tourismania / infra-docker

---

## Project Purpose

Docker Compose–инфраструктура для проекта **Tourismania** — единая точка деплоя всех сервисов на одном сервере. Контейнер nginx получает статический IP-адрес, чтобы основной nginx на хост-машине мог проксировать запросы в него. Репозиторий управляет только инфраструктурой; исходный код сервисов хранится в отдельных репозиториях и монтируется через переменные окружения.

**Primary language:** YAML / Shell (Makefile)  
**Key dependencies:** Docker, Docker Compose, nginx, PostgreSQL 17, Kafka 4.1.0 (KRaft), Go (Air в dev), Vue/Vite, Python 3.12 (python-telegram-bot)

---

## Repository Structure

```
infra-docker/
├── compose.yaml              # Основной Compose-файл (production конфигурация)
├── compose.override.yaml     # Локальные переопределения (dev-режим, bind-mounts)
├── Makefile                  # Удобные команды для управления стеком
├── .env                      # Переменные окружения (не коммитится; копируй из .env.example)
├── services/
│   ├── nginx/
│   │   ├── conf.d/
│   │   │   ├── local/        # Nginx-конфиги для локальной разработки (*.localhost)
│   │   │   └── production/   # Nginx-конфиги для продакшена (tourismania.ru)
│   │   ├── logs/             # access.log / error.log (не коммитится)
│   │   └── ssl/              # SSL-сертификаты (не коммитится)
│   ├── api/
│   │   └── envs/.env         # Переменные для Go API (не коммитится)
│   ├── telegram-bot/
│   │   ├── telegram_bot.py        # Telegram-бот (опросник)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── hotel_*.jpg       # Фото стилей отелей (не коммитятся, добавить вручную)
│   └── xray/
│       ├── config.json.example    # Шаблон конфига VLESS+Reality клиента
│       └── .gitignore             # Игнорирует config.json (содержит ключи сервера)
├── XRAY-CLIENT.md            # Инструкция по настройке X-Ray прокси
├── CLAUDE.md                 # Этот файл
├── AGENTS.md                 # Описание архитектуры для агентов (AI)
├── STYLE.md                  # Гайд по стилю
└── README.md                 # Обзор проекта
```

---

## Services

| Сервис      | Образ / Источник                       | Порты (host)             | Примечания |
|-------------|----------------------------------------|--------------------------|------------|
| `nginx`     | `nginx:1.21.6-alpine`                  | `8082:8082` (prod), `80:80` (local) | Reverse proxy; получает статический IP |
| `web`       | build из `$WEB_PATH`                   | `5173`, `4173` (local only) | Vue/Vite frontend; в prod слушает `:8080` |
| `api`       | build из `$API_PATH`                   | `2345` (debug, local)    | Go API; target `runner` (prod) / `dev` с Air (local) |
| `postgres`  | `postgres:17`                          | `5432:5432`              | БД; named volume `postgresql_data` |
| `kafka`     | `apache/kafka:4.1.0`                   | —                        | KRaft-режим (без Zookeeper); порты 9092/9093 внутри сети |
| `kafka-ui`  | `tchiotludo/akhq:latest`               | —                        | Веб-интерфейс Kafka (AKHQ); базовая аутентификация |
| `telegram-bot`       | build из `./services/telegram-bot/`          | —                        | Telegram-бот (опросник для подбора туров); polling-режим |
| `xray`      | `ghcr.io/xtls/xray-core:latest`        | —                        | VLESS+Reality прокси-клиент; HTTP `:3128`, SOCKS5 `:1080` внутри сети; используется telegram-bot |

---

## Environment Selection

Переменная `ENV` в `.env` определяет, какие nginx-конфиги загружаются:

- `local` → `services/nginx/conf.d/local/` — маршрутизация по `.localhost`-хостнеймам
- `production` → `services/nginx/conf.d/production/` — маршрутизация по доменам (`tourismania.ru`)

### Nginx Routing — local

| Hostname                        | Upstream          |
|---------------------------------|-------------------|
| `tourismania-web.localhost`     | `web:5173`        |
| `tourismania-api.localhost`     | `api:8080`        |
| `kafka-ui.localhost`            | `kafka-ui:8080`   |

### Nginx Routing — production

Контейнер nginx слушает порт `8082`. Хостовый nginx завершает SSL на 80/443 и проксирует на статический IP контейнера.

| Server Name               | Upstream          |
|---------------------------|-------------------|
| `tourismania.ru`          | `web:8080`        |
| `api.tourismania.ru`      | `api:8080`        |
| `kafka-ui.tourismania.ru` | `kafka-ui:8080`   |

---

## Network

Все сервисы подключены к `tourismania_network` (bridge, подсеть задаётся переменной `$SUBNET`, по умолчанию `192.168.100.0/24`). Контейнер nginx получает фиксированный IP `$SUBNET_NGINX_IP`.

---

## Configuration Files (не коммитятся)

| Файл                            | Назначение |
|---------------------------------|------------|
| `.env`                          | Основные переменные окружения стека; копируй из `.env.example` |
| `services/api/envs/.env`        | Переменные Go API |
| `services/telegram-bot/hotel_*.jpg`   | Фотографии стилей отелей для бота (8 файлов, добавить вручную) |
| `services/xray/config.json`     | Конфиг Xray-клиента с реальными ключами сервера; скопировать из `config.json.example` |
| `services/nginx/ssl/`           | SSL-сертификаты |

---

## Adding a New Service

1. Добавить определение сервиса в `compose.yaml` с сетью `tourismania_network`.
2. При необходимости добавить переопределение в `compose.override.yaml` для локального режима.
3. Создать nginx-конфиги в `services/nginx/conf.d/local/` и `services/nginx/conf.d/production/`.
4. Если нужны переменные окружения — создать `services/<name>/envs/` и добавить `.gitignore`, исключающий `.env`.
5. Обновить таблицы Services и Nginx Routing в этом файле.

---

## Security

- Никогда не коммить секреты, пароли и ключи.
- Все чувствительные данные — через переменные окружения в `.env`-файлах.
- SSL-сертификаты хранятся только на сервере, в репозиторий не попадают.
- Валидировать и санировать любой внешний ввод на уровне сервисов.

---

## Documentation Maintenance

| Документ | Обновлять когда |
|----------|-----------------|
| `README.md` | Меняется назначение проекта или инструкции по установке |
| `CLAUDE.md` | Меняется архитектура, сервисы, конфиги или процесс разработки |
| `AGENTS.md` | Меняется архитектурная схема для AI-агентов |
