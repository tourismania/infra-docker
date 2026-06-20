# Architecture — Tourismania / infra-docker

## Service Map

```
Internet
  │
  ▼
Host nginx (80/443, SSL termination)
  │  proxy_pass → 192.168.100.x:8082
  ▼
┌─────────────────────────────────────────────────────┐
│  tourismania_network  (192.168.100.0/24)            │
│                                                     │
│  nginx (:8082 prod / :80 local)  ←── static IP     │
│    ├── web:8080        (Vue/Vite)                   │
│    ├── api:8080        (Go)                         │
│    └── kafka-ui:8080   (AKHQ)                       │
│                                                     │
│  postgres:5432         (PostgreSQL 17)              │
│  kafka:9092/9093       (KRaft, no Zookeeper)        │
│                                                     │
│  telegram-bot          (Python 3.12, polling)       │
│    └── via HTTPS_PROXY ──► xray:3128               │
│                                                     │
│  xray                  (Xray-core VLESS+Reality)    │
│    ├── :1080  SOCKS5 inbound                        │
│    └── :3128  HTTP proxy inbound                    │
│         └── outbound ──► KZ Xray server             │
└─────────────────────────────────────────────────────┘
```

## Data Flows

### User → Telegram Bot → Admin
```
User sends /start
  → telegram-bot polls api.telegram.org (via xray if XRAY_HTTP_PROXY set)
  → ConversationHandler walks 32-step questionnaire
  → on completion: send_message(ADMIN_CHAT_ID, summary)
```

### Web request (production)
```
Browser → host nginx (SSL) → nginx container (8082) → web:8080 (Vue static)
Browser → host nginx (SSL) → nginx container (8082) → api:8080 (Go REST)
```

### Kafka
```
api → kafka:9092 (produce/consume)
kafka-ui → kafka:9092 (read-only UI)
```

## Key Contracts

| Contract | Value |
|----------|-------|
| nginx static IP | `$SUBNET_NGINX_IP` (must be set in `.env`) |
| Docker network subnet | `$SUBNET` (default `192.168.100.0/24`) |
| xray HTTP proxy | `xray:3128` (internal only) |
| telegram-bot proxy toggle | `XRAY_HTTP_PROXY` in `.env` (empty = disabled) |

## Non-obvious Constraints

- `xray/config.json` is gitignored — must be created manually on each server from `config.json.example` before `docker compose up`.
- `depends_on: xray` in telegram-bot uses the default `service_started` condition (not `service_healthy`) — there is a brief window at cold start where the proxy port may not yet be bound.
- `telegram-bot` env vars (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_ADMIN_CHAT_ID`) come from the root `.env`, not from a service-local `envs/` dir (unlike `api`).
- Hotel photos (`hotel_*.jpg`) must be placed manually in `services/telegram-bot/` on the server — they are not committed and not baked into the image on build (they are read at runtime from the mounted directory).
