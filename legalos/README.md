# Enterprise LegalOS

Экосистема AI-решений для автоматизации юридических, кадровых, бухгалтерских и управленческих процессов организаций Республики Узбекистан.

Платформа состоит из двух продуктов на едином AI Core:

| Продукт | Аудитория | Интерфейсы |
|---|---|---|
| **HR Assistant (Free / HR Pro)** | HR-специалисты | Web, Telegram Bot, MS Teams (план) |
| **Enterprise LegalOS** | Компании, банки, госорганизации, холдинги, университеты | Desktop Web, API |

Подробная архитектура: [`../docs/legalos/architecture.md`](../docs/legalos/architecture.md)

## Быстрый старт

```bash
cd legalos
cp .env.example .env          # заполните LEGALOS_OPENAI_API_KEY (или другого провайдера)
docker compose up -d          # postgres+pgvector, redis, minio, rabbitmq, backend, worker, frontend, nginx
```

| Сервис | Адрес |
|---|---|
| Веб-интерфейс | http://localhost |
| API (Swagger) | http://localhost/api/v1 → http://localhost:8000/docs внутри сети |
| Health check | http://localhost/health |
| MinIO Console | http://localhost:9001 |

Telegram-бот (нужен `LEGALOS_TELEGRAM_BOT_TOKEN` в `.env`):

```bash
docker compose --profile telegram up -d telegram-bot
```

Запуск backend локально без Docker:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload   # требует запущенный PostgreSQL с pgvector
pytest tests/                    # smoke-тесты без внешних сервисов
```

## Структура

```
legalos/
├── backend/                  # FastAPI
│   └── app/
│       ├── api/v1/           # auth, chat, documents, agents, search, legislation
│       ├── core/             # config, JWT/security
│       ├── db/, models/      # SQLAlchemy (multi-tenant), pgvector
│       ├── services/
│       │   ├── ai/           # Provider Pattern: OpenAI/DeepSeek/Gemini/Qwen/OpenAI-compatible
│       │   ├── rag/          # Hybrid Search: BM25 + pgvector + RRF + LLM-reranker (+KG-хук)
│       │   ├── agents/       # 7 агентов: HR, Legal, Accounting, Procurement, CEO, Compliance, Tax
│       │   ├── documents/    # Document Intelligence (IBM Docling)
│       │   ├── legislative/  # Legislative Intelligence (Lex.uz/Norma.uz, история редакций)
│       │   ├── billing/      # тарифы Free / HR Pro / Business / Enterprise / Government
│       │   └── security/     # prompt-injection protection, RAG security
│       └── workers/          # RabbitMQ consumers (индексация, мониторинг законодательства)
├── frontend/                 # Next.js: слева чат/агенты/история, справа источники и статьи
├── telegram-bot/             # HR Assistant Free (aiogram)
├── nginx/                    # reverse proxy
└── docker-compose.yml
```

## Ключевые принципы

- **Provider Pattern** — добавление новой LLM не требует изменений бизнес-логики (`services/ai/registry.py`).
- **Multi-Tenant** — каждая таблица несёт `tenant_id`; RAG-поиск видит только документы своего тенанта плюс общее законодательство.
- **Тарифная лестница** — Free → HR Pro → Business → Enterprise → Government; лимиты и доступ к агентам применяются на уровне API (`services/billing/plans.py`).
- **Безопасность** — JWT/OAuth2, RBAC (owner/admin/manager/member/viewer), append-only Audit Log, эвристический экран prompt-injection, изоляция извлечённого контекста.
- **Legislative Intelligence** — редакции законов неизменяемы (`legislative_revisions`), изменения детектируются по хэшу, автоматически переиндексируются.

## Связь с существующим GraphRAG

Каталог `../backend` (Neo4j llm-graph-builder для Трудового кодекса) остаётся самостоятельным компонентом Knowledge Graph. RAG-пайплайн LegalOS принимает `graph_expander`-хук (`services/rag/pipeline.py`), через который граф Neo4j подключается как четвёртый источник Hybrid Search.
