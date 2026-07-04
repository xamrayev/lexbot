# Enterprise LegalOS — Архитектура

## 1. Обзор экосистемы

```
                        ┌─────────────────────────────────────────┐
   Пользователи         │              Interfaces                 │
   HR / юристы /        │  Web (Next.js) · Telegram Bot · Teams*  │
   бухгалтеры / CEO ───▶│              Nginx (:80)                │
                        └───────────────────┬─────────────────────┘
                                            │ REST /api/v1 (JWT)
                        ┌───────────────────▼─────────────────────┐
                        │           FastAPI Backend               │
                        │  Auth · RBAC · Plans · Audit · Chat     │
                        ├──────────┬──────────┬───────────────────┤
                        │ AI Core  │ Agents   │  Enterprise RAG   │
                        │ Provider │ HR Legal │  BM25 + pgvector  │
                        │ Pattern  │ Acc Proc │  + RRF + Reranker │
                        │          │ CEO Comp │  + KG-hook(Neo4j) │
                        │          │ Tax      │                   │
                        ├──────────┴──────────┴───────────────────┤
                        │ Document Intelligence │ Legislative     │
                        │ (IBM Docling)         │ Intelligence    │
                        └──────┬───────┬────────┴───────┬─────────┘
                               │       │                │
                     ┌─────────▼─┐ ┌───▼────┐ ┌─────────▼────────┐
                     │ PostgreSQL│ │ MinIO  │ │    RabbitMQ      │
                     │ +pgvector │ │(файлы) │ │ (indexing, sync) │
                     └───────────┘ └────────┘ └──────────────────┘
                            │                        │
                        ┌───▼───┐              ┌─────▼──────┐
                        │ Redis │              │  Workers   │
                        └───────┘              └────────────┘
        * Teams — в roadmap
```

## 2. AI Platform — Provider Pattern

Интерфейс `AIProvider` (`services/ai/base.py`): `complete()`, `stream()`, `embed()`.

Все требуемые вендоры (OpenAI, DeepSeek, Gemini, Qwen, Gemma/self-hosted) говорят по OpenAI-совместимому протоколу, поэтому реализация одна — `OpenAICompatibleProvider`, параметризованная `base_url`/`api_key`/`model`. Регистрация — в `services/ai/registry.py`; **добавление модели не меняет бизнес-логику** (агенты и RAG зависят только от интерфейса).

## 3. Enterprise RAG

Пайплайн (`services/rag/pipeline.py`):

1. **BM25** — PostgreSQL full-text (`ts_rank_cd`);
2. **Vector** — pgvector, cosine (`<=>`);
3. **Fusion** — Reciprocal Rank Fusion (устойчив к разным шкалам скоров);
4. **Knowledge Graph** — hook `graph_expander`, куда подключается существующий Neo4j GraphRAG (корень репозитория, `backend/`);
5. **Reranker** — listwise LLM-reranker с фолбэком на порядок fusion;
6. Ответ агента сопровождается **цитатами** (`sources`), которые фронтенд подсвечивает в правой панели.

RAG Security: SQL-фильтр `tenant_id IN (свой, LEGISLATION_TENANT)` — корпоративные документы одного тенанта никогда не попадают в выдачу другого; извлечённый текст оборачивается в data-envelope и объявляется моделью «данными, а не инструкциями».

## 4. Multi-Tenancy и безопасность

| Механизм | Реализация |
|---|---|
| Multi-Tenant | `tenant_id` на каждой бизнес-таблице; изоляция в query-слое; RLS PostgreSQL — опция для Government Edition |
| AuthN | OAuth2 password flow → JWT access (60 мин) + refresh (30 дней) |
| RBAC | роли owner > admin > manager > member > viewer, guard `require_role()` |
| Audit Log | append-only `audit_logs`: auth.*, chat.message, document.upload, IP |
| Prompt Injection | эвристический экран (ru/uz/en паттерны) + изоляция RAG-контекста |
| Encryption | TLS на Nginx; MinIO SSE и шифрование дисков — на уровне развертывания |
| Secret Management | только env-переменные (`pydantic-settings`), секретов в коде нет |

## 5. Тарифы и enforcement

`services/billing/plans.py` — единая точка правды:

| | Free | HR Pro | Business | Enterprise | Government |
|---|---|---|---|---|---|
| Сообщений/день | 20 | 200 | 1000 | ∞ | ∞ |
| Загрузка документов | — | ✔ | ✔ | ✔ | ✔ |
| Корп. база знаний | — | — | ✔ | ✔ | ✔ |
| Агенты | HR | HR | +Legal, Acc, Proc, CEO, Tax | +Compliance | все |
| Пользователей | 1 | 1 | 50 | ∞ | ∞ |

Лимиты считаются per-user per-day (`usage_counters`); превышение → HTTP 429, недоступный агент → HTTP 402. Истёкшая подписка автоматически деградирует до Free.

## 6. Document Intelligence

`services/documents/ingest.py`: MinIO → конвертация (IBM Docling: PDF/DOCX/XLSX/HTML/MD/Email + OCR + таблицы; фолбэк — plain-text) → LLM-классификация (приказ/договор/регламент/…) → чанкинг с overlap → эмбеддинги → pgvector. Большие партии обрабатывает RabbitMQ-worker (`workers/consumer.py`, очередь `legalos.index`).

## 7. Legislative Intelligence

`services/legislative/monitor.py`: для каждого отслеживаемого акта (Lex.uz, Norma.uz, сайты министерств) периодически (worker, очередь `legalos.legislation`) скачивается текущий текст → SHA-256 → при изменении хэша создаётся **неизменяемая ревизия** (`legislative_revisions`), контент переиндексируется в общий legislation-тенант, публикуется событие `legislation.changed` (уведомления пользователей + обновление Knowledge Graph).

История редакций доступна через `GET /api/v1/legislation/acts/{id}/revisions` и отображается в правой панели интерфейса.

## 8. Интерфейс (Desktop Web)

Трёхколоночный workspace (`frontend/app/page.tsx`):

- **слева** — чат, список агентов (недоступные по тарифу помечены 🔒), история диалогов, проекты;
- **центр** — диалог с агентом;
- **справа** — источники ответа: фрагменты документов и статьи законов с подсветкой, ссылки на Lex.uz/Norma.uz, история редакций.

## 9. Roadmap

- [ ] Alembic-миграции вместо dev-`create_all`
- [ ] SSO (SAML/OIDC) для Enterprise; интеграция ERP/CRM/HRM
- [ ] Microsoft Teams бот; интеграции MyGov/Soliq (deep links → API)
- [ ] Генерация кадровых документов по шаблонам (экспорт DOCX/PDF)
- [ ] Neo4j `graph_expander` в проде; Compliance Center; продвинутый reranker (cross-encoder)
- [ ] Стриминговые ответы (SSE) через `AIProvider.stream()`
