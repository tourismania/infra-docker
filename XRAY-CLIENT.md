# X-Ray Client — Инструкция

Сервис `xray` запускает [Xray-core](https://github.com/XTLS/Xray-core) клиент внутри Docker-сети. Он создаёт локальный HTTP-прокси (`xray:3128`) и SOCKS5-прокси (`xray:1080`), которые туннелируют трафик через Xray-сервер по протоколу **VLESS + Reality**.

Telegram-бот использует HTTP-прокси для всех исходящих запросов к `api.telegram.org`.

---

## Настройка

### 1. Создать конфиг клиента

```bash
cp services/xray/config.json.example services/xray/config.json
```

Открыть `services/xray/config.json` и заполнить реальными данными сервера:

| Поле | Где взять |
|------|-----------|
| `address` | IP-адрес или домен Xray-сервера |
| `port` | Порт сервера (обычно 443) |
| `id` | UUID пользователя с сервера |
| `flow` | `xtls-rprx-vision` (стандарт для Reality) |
| `serverName` | SNI — домен-маскировка (например `www.microsoft.com`) |
| `publicKey` | Публичный ключ Reality с сервера |
| `shortId` | Short ID с сервера |

Эти данные выдаёт сервер при создании пользователя (например через `3x-ui` панель или CLI `xray`).

```plain
Если сервер настроен через панель 3x-ui (судя по XRAY-CLIENT.md, у вас так)

Самый простой путь — зайти в панель и взять готовую ссылку клиента:

1. Открыть панель 3x-ui в браузере (обычно http://<server-ip>:<panel-port>).
2. Найти ваш inbound (VLESS + Reality).
3. У нужного клиента нажать "QR-код" / "Export" / иконку ссылки — получите строку вида:
vless://UUID@SERVER_IP:443?security=reality&sni=www.microsoft.com&fp=chrome&pbk=PUBLIC_KEY&sid=SHORT_ID&type=tcp&flow=xtls-rprx-vision#имя
4. Разбираете по параметрам прямо в config.json:

- UUID → outbounds[0].settings.vnext[0].users[0].id
- pbk → realitySettings.publicKey
- sid → realitySettings.shortId
- sni → realitySettings.serverName
- SERVER_IP и порт → vnext[0].address / port
```

> `services/xray/config.json` добавлен в `.gitignore` — в репозиторий не попадёт.

### 2. Включить прокси в .env

```dotenv
XRAY_HTTP_PROXY=http://xray:3128
```

Оставь значение пустым (`XRAY_HTTP_PROXY=`), чтобы telegram-bot работал без прокси.

### 3. Запустить стек

```bash
make up
# или если уже запущен:
docker compose up -d xray telegram-bot
```

---

## Как это работает

```
telegram-bot (Python)
  │  HTTPS_PROXY=http://xray:3128
  ▼
xray-контейнер (порт 3128, HTTP inbound)
  │  VLESS + Reality
  ▼
Xray-сервер в Казахстане
  │
  ▼
api.telegram.org
```

`python-telegram-bot` использует `httpx` для всех запросов. `httpx` автоматически подхватывает стандартные переменные окружения `HTTP_PROXY` / `HTTPS_PROXY`, поэтому дополнительных изменений в коде бота не нужно.

---

## Проверка

```bash
# Статус контейнера
docker compose ps xray

# Логи xray (должно быть "started")
docker compose logs xray

# Проверить, что прокси доступен из контейнера telegram-bot
docker compose exec telegram-bot curl -s -o /dev/null -w "%{http_code}" \
  -x http://xray:3128 https://api.telegram.org

# Ожидаемый результат: 200 или 404 (но не ошибка соединения)
```

---

## Отладка

**Контейнер xray падает при старте**

Проверь синтаксис конфига:

```bash
docker compose run --rm xray xray -test -config /etc/xray/config.json
```

**Telegram-бот не достигает api.telegram.org через прокси**

Проверь логи xray на предмет ошибок соединения с сервером:

```bash
docker compose logs -f xray
```

Убедись, что `XRAY_HTTP_PROXY` выставлен и виден в контейнере:

```bash
docker compose exec telegram-bot env | grep -i proxy
```

**Отключить прокси без перестройки**

```dotenv
# .env
XRAY_HTTP_PROXY=
```

```bash
docker compose up -d telegram-bot
```

**Бот перестаёт отвечать через 15-20 минут работы (getUpdates замолкает без ошибок)**

Reality-туннель до сервера иногда обрывается "тихо" (без FIN/RST) — типично для DPI/NAT на пути через РФ/КЗ сети. Без активного TCP keepalive ни xray, ни клиент не замечают обрыв, и переподключение может зависнуть дольше собственных таймаутов `httpx`.

`services/xray/config.json.example` уже содержит `streamSettings.sockopt.tcpKeepAliveInterval: 15` на outbound `vless` — перенеси это же поле в свой `services/xray/config.json` на сервере (он не коммитится и не обновляется автоматически) и перезапусти `xray`:

```bash
docker compose up -d xray
```

Дополнительно `telegram-bot` теперь сам следит за живостью поллинга (watchdog на `job_queue`, см. `services/telegram-bot/telegram_bot.py`) и принудительно завершает процесс после нескольких неудачных проверок подряд, чтобы `restart: unless-stopped` его поднял заново.

---

## Альтернативная настройка прокси через код

Если нужен прокси на уровне кода (а не через env vars), в `telegram_bot.py`:

```python
from telegram.ext import ApplicationBuilder

PROXY_URL = os.getenv("XRAY_HTTP_PROXY")  # http://xray:3128

builder = ApplicationBuilder().token(BOT_TOKEN)
if PROXY_URL:
    builder = builder.proxy(PROXY_URL).get_updates_proxy(PROXY_URL)

app = builder.build()
```

Это даёт точечный контроль: прокси применяется только к запросам Telegram, а не ко всему контейнеру.
