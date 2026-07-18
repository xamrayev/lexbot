# 00 — Overview: Content Factory SaaS (ContentOS)

**Статус:** Draft · **Версия:** 1.0.0 · **Дата:** 2026-07-18

---

## 1. Проблема

Создание качественного контента для каналов (Telegram, блоги, соцсети) требует ежедневной
рутины: мониторинг источников, отбор тем, написание, редактура, SEO, публикация, анализ
метрик. Существующие SaaS-генераторы решают только шаг «написать текст» и не образуют
замкнутый цикл «исследование → создание → публикация → обучение на обратной связи».

## 2. Решение

ContentOS — платформа, где каждый канал представлен отдельным ИИ-агентом со своей памятью,
стилем, источниками, правилами и аналитикой. Ежедневно ИИ:

1. собирает новую информацию из подключённых источников;
2. анализирует её и определяет, что интересно аудитории;
3. пишет материалы в стиле автора;
4. планирует и публикует контент;
5. анализирует эффективность публикаций;
6. улучшает последующие материалы (feedback loop).

## 3. Персоны

| Персона | Роль | Ключевой сценарий |
|---|---|---|
| **Owner / Главред** | Владелец workspace | Настраивает каналы, утверждает публикации, смотрит ROI |
| **Автор** | Член команды | Совместное редактирование, черновики |
| **Редактор** | Член команды | Approval-очередь, правки, возвраты на доработку |
| **SEO-специалист** | Член команды | SEO-настройки, ключевые слова, анализ CTR |
| **Администратор платформы** | Оператор SaaS | Провайдеры, модели, тарифы, лимиты, пайплайны |
| **Наблюдатель** | Read-only член команды | Просмотр календаря и аналитики |
| **Разработчик-интегратор** | Внешний | API, webhooks, Plugin SDK, Marketplace |

## 4. Доменная модель (верхний уровень)

```
Workspace
    ├── Channel 1..N
    │      ├── Brand            (тональность, аудитория, ограничения, оформление)
    │      ├── AI Personality   (пресет или кастомный стиль агента)
    │      ├── Style Profile    (Style Embedding + структурные метрики)
    │      ├── Sources          (Telegram, RSS, Web, YouTube, PDF, RAG …)
    │      ├── Schedule         (контент-календарь, планировщик)
    │      ├── Analytics        (метрики публикаций, feedback loop)
    │      ├── Memory           (что публиковалось, что зашло, что запрещено)
    │      └── AI Agent         (research → plan → write → seo → review → publish)
    └── Team                    (роли, approval, история изменений)
```

## 5. Карта модулей и спецификаций

| # | Модуль | Requirements | Design |
|---|---|---|---|
| 01 | Workspace, Channels, Team | `requirements/01-workspace-channels.md` | `design/architecture.md`, `design/data-model.md` |
| 02 | Brand, AI Personality, Style Learning | `requirements/02-brand-style.md` | `design/data-model.md` |
| 03 | Sources & Ingestion | `requirements/03-sources-ingestion.md` | `design/pipeline.md` |
| 04 | Content Pipeline (15 этапов) | `requirements/04-content-pipeline.md` | `design/pipeline.md` |
| 05 | AI Agent Framework | `requirements/05-ai-agents.md` | `design/agent-framework.md` |
| 06 | LLM Gateway & Providers | `requirements/06-llm-gateway.md` | `design/llm-gateway.md` |
| 07 | Планирование и публикация | `requirements/07-scheduling-publishing.md` | `design/pipeline.md` |
| 08 | Analytics & Feedback Loop | `requirements/08-analytics-feedback.md` | `design/data-model.md` |
| 09 | Качество, факты, плагиат, право | `requirements/09-quality-safety.md` | `design/pipeline.md` |
| 10 | Подписки, биллинг, cost control | `requirements/10-billing-subscriptions.md` | `design/llm-gateway.md` |
| 11 | API, Webhooks, Marketplace, Plugin SDK | `requirements/11-platform-extensibility.md` | `design/architecture.md` |
| 12 | Инфраструктура и observability | — (NFR в 09/10) | `design/infrastructure.md` |

## 6. Скоуп релизов

### MVP (Phase 1)
- Workspace + 1..N каналов, роли Owner/Editor/Viewer;
- Источники: Telegram, RSS, Web (crawler), файлы (PDF/DOCX);
- Style Learning из Telegram-канала и архива статей;
- Pipeline: сбор → дедуп → суммаризация → идеи → статья → саморедактура → Quality Score → approval → публикация в Telegram;
- LLM Gateway: OpenAI-совместимые провайдеры (OpenAI, OpenRouter, Ollama, vLLM, DeepSeek, Groq) + адаптеры Anthropic/Gemini;
- Тарифы Free/Starter/Pro, учёт токенов и стоимости;
- Контент-календарь, версионирование материалов;
- Asynq-очереди, Docker Compose, Prometheus/Grafana.

### Growth (Phase 2)
- YouTube/Twitter/Reddit/Notion/Google Drive источники;
- AI Trend Finder, AI Researcher, Content Planner;
- Feedback Loop по метрикам публикаций, A/B эксперименты;
- Массовая генерация, Workflow Builder (визуальный);
- Генерация изображений (обложки, баннеры), мультиязычность;
- Temporal вместо Asynq, Meilisearch/OpenSearch.

### Platform (Phase 3)
- Marketplace (стили, workflow, промпты, агенты, источники, плагины);
- Public API + Plugin SDK, webhooks (Slack/Discord/Zapier/n8n/Make);
- Видео-производные (Shorts/TikTok/Reels), AI Copilot в редакторе;
- Enterprise-тариф, выделение микросервисов (AI, Scheduler, Analytics, Billing).

## 7. Вне скоупа (Non-Goals)

- Хостинг сайтов/блогов (публикуем во внешние платформы, не хостим);
- Собственная обученная LLM (используем провайдеров через Gateway);
- Модерация пользовательского контента соцсетей (только собственные материалы);
- Накрутка метрик и генерация фейковых взаимодействий — запрещено конституцией (ст. VIII).

## 8. Ключевые метрики продукта

| Метрика | Цель MVP |
|---|---|
| Time-to-first-post (регистрация → первая публикация) | < 30 минут |
| Доля материалов, одобренных без правок | > 60% |
| Средняя стоимость одного материала (LLM cost) | < $0.10 |
| Uptime pipeline-запусков (успешные/все) | > 99% |
| Style match score (самооценка Reviewer-агента) | > 80/100 |
