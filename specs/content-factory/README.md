# Content Factory SaaS (ContentOS) — Spec-Driven Development

Операционная система для управления контентом: каждый канал — автономный ИИ-агент
со своей памятью, стилем, источниками, правилами и аналитикой. Спецификации ведутся
по методологии Spec-Driven Development: код пишется только под утверждённые
требования.

## Порядок чтения

1. **[constitution.md](constitution.md)** — принципы проекта (нерушимые правила).
2. **[00-overview.md](00-overview.md)** — видение, персоны, домены, скоуп релизов.
3. **requirements/** — функциональные требования в EARS-нотации (`REQ-<MODULE>-<NNN>`).
4. **design/** — техническое проектирование (архитектура, данные, Gateway, агенты).
5. **tasks/** — план реализации по фазам; каждая задача ссылается на REQ-ID.

## Рабочий цикл

```
Идея → requirements/ (EARS + acceptance criteria)
     → design/       (как реализуем, контракты, схемы)
     → tasks/        (задачи со ссылками на REQ-*)
     → implementation (PR ссылается на T-ID и REQ-ID)
     → verification  (AC покрыты тестами в CI)
```

## Карта документов

| Документ | Содержание |
|---|---|
| `requirements/01-workspace-channels.md` | Workspace, каналы, команда, роли, изоляция |
| `requirements/02-brand-style.md` | Brand, AI Personality, Style Learning/Embedding |
| `requirements/03-sources-ingestion.md` | Источники, ingestion, дедуп, RAG-база знаний |
| `requirements/04-content-pipeline.md` | 15-этапный конвейер, конфигурация этапов, batch, Workflow Builder |
| `requirements/05-ai-agents.md` | Agent Framework, память канала, Trend Finder, Copilot |
| `requirements/06-llm-gateway.md` | Провайдеры, модели, router/failover, промпты, cost control |
| `requirements/07-scheduling-publishing.md` | Календарь, режимы публикации, версии, publish-адаптеры |
| `requirements/08-analytics-feedback.md` | Метрики, дашборды, feedback loop, A/B |
| `requirements/09-quality-safety.md` | Quality Score, факты/цитирование, плагиат, политика, мультиязычность |
| `requirements/10-billing-subscriptions.md` | Тарифы, usage, лимиты, платежи |
| `requirements/11-platform-extensibility.md` | API, webhooks, Marketplace, Plugin SDK, изображения/видео |
| `design/architecture.md` | Modular monolith, границы модулей, Event Bus, безопасность |
| `design/data-model.md` | Схема PostgreSQL (+pgvector), инварианты |
| `design/llm-gateway.md` | Интерфейс Provider, адаптеры, router, quota, промпты |
| `design/agent-framework.md` | Runner, инструменты/allowlist, агенты, память |
| `design/pipeline.md` | Оркестрация, этапы, Quality Gate, публикация |
| `design/infrastructure.md` | Compose-топология, observability, CI/CD, NFR |
| `tasks/phase-1-mvp.md` | MVP: полный цикл до публикации в Telegram |
| `tasks/phase-2-growth.md` | Тренды, feedback loop, batch, Workflow Builder |
| `tasks/phase-3-platform.md` | Marketplace, Plugin SDK, Copilot, микросервисы |

## Соглашения

- **REQ-ID** неизменяемы; устаревшие требования помечаются `Deprecated`, не удаляются.
- Ключевые слова: `SHALL` — обязательно, `SHALL NOT` — запрещено, `MAY` — опционально.
- Каждый acceptance criterion автоматизируем; исключения помечены `[manual]`.
- Архитектурные решения — ADR в `design/adr/` (Context → Decision → Consequences).
