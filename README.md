# Infrastructure Docker

Docker Compose–инфраструктура для проекта **Tourismania** — единая точка деплоя всех сервисов на одном сервере. Контейнер nginx получает статический IP-адрес, чтобы основной nginx на хост-машине мог проксировать запросы в него. Репозиторий управляет только инфраструктурой; исходный код сервисов хранится в отдельных репозиториях и монтируется через переменные окружения.

**Primary language:** YAML / Shell (Makefile)  
**Key dependencies:** Docker, Docker Compose, nginx, PostgreSQL 17, Kafka 4.1.0 (KRaft), Go (Air в dev), Vue/Vite, Python 3.12 (python-telegram-bot)

## Пользователи и группы системы

`пользователь_разработчик` - для прямого подключения по ssh

`пользователь_гитхаб` - для реализации CD

`группа_для_работы_с_приложением_tourismania` - для возможности обновления файлов на сервере в папке приложения. Состоит из: `пользователь_разработчик`,
`пользователь_гитхаб`

---

## Build and Run

```bash
# Поднять все сервисы
make up
# или
docker compose up -d

# Поднять конкретный сервис
docker compose up -d nginx postgres

# Остановить всё
make down

# Пересобрать образы и перезапустить
make build   # down → build
make restart # down → up

# Посмотреть логи
docker compose logs -f [service]

# Полная очистка (включая volumes — деструктивно!)
make docker-down-clear

# Очистить неиспользуемые образы/контейнеры
make docker-clear
```

---

## Deployment

```bash
# Переключить инфраструктуру на тег
make deploy-infra TAG=v2.0.2

# Обновить frontend (web) до тега
make deploy-web-tag TAG=v1.5.0

# Обновить Go API до тега
make deploy-api-tag TAG=v3.1.0

# Пересобрать и перезапустить Telegram-бота
make deploy-telegram-bot
```

---

## Telegram Bot

Бот реализует опросник для подбора туров и отправляет заполненную анкету в Telegram-группу администраторов.

### Настройка перед запуском

1. Указать токен и chat_id администратора в `.env`:

   ```env
   TELEGRAM_BOT_TOKEN=<токен от @BotFather>
   TELEGRAM_BOT_ADMIN_CHAT_ID=<chat_id группы/канала для получения анкет>
   ```

2. Собрать и запустить:

   ```bash
   make deploy-bot
   # или
   docker compose build telegram-bot && docker compose up -d telegram-bot
   ```

---

## X-Ray Proxy

Сервис `xray` запускает Xray-core клиент (VLESS+Reality), который создаёт HTTP-прокси внутри Docker-сети. Telegram-бот использует его для обхода ограничений при обращении к `api.telegram.org`.

Включается через переменную в `.env`:

```env
XRAY_HTTP_PROXY=http://xray:3128   # включить
XRAY_HTTP_PROXY=                   # отключить
```

Полная инструкция по настройке, конфигу сервера и отладке — в [`XRAY-CLIENT.md`](XRAY-CLIENT.md).

---

## Validation Gates

- [ ] Конфиги валидны (`docker compose config` без ошибок)
- [ ] Стек поднимается локально (`make up` без ошибок)
- [ ] Nginx корректно маршрутизирует запросы в обоих режимах (local / production)
- [ ] Секреты не попали в коммит
- [ ] Документация обновлена (CLAUDE.md, README.md при необходимости)

---
