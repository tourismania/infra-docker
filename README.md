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
make deploy-bot
```

---

## Telegram Bot

Бот реализует опросник для подбора туров и отправляет заполненную анкету в Telegram-группу администраторов.

### Настройка перед запуском

1. Заполнить `services/telegram-bot/envs/.env`:
   ```env
   BOT_TOKEN=<токен от @BotFather>
   ADMIN_CHAT_ID=<chat_id группы/канала для получения анкет>
   ```

2. Положить фотографии стилей отелей в `services/telegram-bot/` (опционально):
   ```
   hotel_1.jpg  # Тропический
   hotel_2.jpg  # Бохо-шик
   hotel_3.jpg  # Минимализм
   hotel_4.jpg  # Средиземноморский
   hotel_5.jpg  # Эко-люкс
   hotel_6.jpg  # Колониальный
   hotel_7.jpg  # Классический
   hotel_8.jpg  # Восточный
   ```
   Без фото бот работает корректно — шаг с галереей просто пропускается.

3. Собрать и запустить:
   ```bash
   make deploy-bot
   # или
   docker compose build bot && docker compose up -d bot
   ```

---

## Development Process

### Workflow

```
Plan → Issue → Implement → Review → Merge → Docs
```

| Фаза | Описание |
|------|----------|
| **Plan** | Определить scope, зависимости и владение файлами. |
| **Issue** | Создать GitHub Issue с критериями приёмки и ограничениями. |
| **Implement** | Ветка от `main`. Следовать конвенциям. |
| **Review** | PR → ревью → все замечания разрешены. |
| **Merge** | Мёрж в `main` после апрува. |
| **Docs** | Обновить затронутую документацию. Закрыть issue. |

---

## Validation Gates

Перед мёржем PR:

- [ ] Конфиги валидны (`docker compose config` без ошибок)
- [ ] Стек поднимается локально (`make up` без ошибок)
- [ ] Nginx корректно маршрутизирует запросы в обоих режимах (local / production)
- [ ] Секреты не попали в коммит
- [ ] Документация обновлена (CLAUDE.md, README.md при необходимости)
- [ ] PR ограничен scope issue
- [ ] Ревью выполнено, все замечания разрешены

---
