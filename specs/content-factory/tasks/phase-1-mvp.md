# Tasks — Phase 1: MVP

**Цель:** Time-to-first-post < 30 минут; полный цикл «источники → материал →
approval → публикация в Telegram» на Multi-Model Pipeline с учётом стоимости.

Формат: `- [ ] T<phase>.<n> Название — реализует: REQ-…` Задача считается
выполненной только вместе с тестами её acceptance criteria.

---

## M0 — Foundation (недели 1–2)

- [ ] T1.01 Скелет modular monolith: cmd/{server,worker,migrate}, internal/{contract,platform,...}, arch-тест границ модулей — реализует: DES-ARCH §3
- [ ] T1.02 Platform: PG(+pgvector)+sqlc, Redis, MinIO, NATS-клиент, миграции, telemetry (slog+OTel+Prometheus) — DES-INFRA
- [ ] T1.03 Docker Compose (все сервисы) + CI (lint, arch, unit, testcontainers, e2e-заглушка) — DES-INFRA §5
- [ ] T1.04 Auth (регистрация/логин, JWT), users — REQ-WS-001
- [ ] T1.05 Workspaces, members, роли, tenancy middleware (404-семантика), audit log — REQ-WS-001..004, 020..025 · AC-WS-1,3,5
- [ ] T1.06 Приглашения по email (7 дней) — REQ-WS-021
- [ ] T1.07 Event Bus: publisher/subscriber поверх NATS JetStream, реестр схем, idempotent consumers — DES-ARCH §5

## M1 — LLM Gateway (недели 2–4)

- [ ] T1.10 Интерфейс Provider + registry + фейковый провайдер для тестов — REQ-LLM-002, DES-LLM §9
- [ ] T1.11 Адаптер openai_compatible (OpenAI, OpenRouter, Ollama, vLLM, DeepSeek, Groq, …) — REQ-LLM-003..004 · AC-LLM-2
- [ ] T1.12 Адаптеры anthropic, gemini — REQ-LLM-003
- [ ] T1.13 Админка платформы: providers, ai_models (все типы), цены, enable/disable — REQ-LLM-020..022
- [ ] T1.14 Secrets Manager (envelope AES-256-GCM), маскирование в логах/API — REQ-LLM-023
- [ ] T1.15 Router: tier→model по тарифу; circuit breaker; rate limiter; failover-цепочки — REQ-LLM-021, 030..033 · AC-LLM-3
- [ ] T1.16 Quota Guard (Redis Lua, атомарно, до вызова) — REQ-LLM-051, REQ-BILL-021 · AC-LLM-4, AC-BILL-2
- [ ] T1.17 llm_calls + стоимость + usage_counters в одной транзакции; метрики/трейсы — REQ-LLM-005, 050 · AC-LLM-5
- [ ] T1.18 Prompt Library: CRUD, версии, активная версия, рендер с валидацией переменных, кэш — REQ-LLM-040..042 · AC-LLM-6
- [ ] T1.19 Arch-тест: SDK провайдеров только в internal/llm — REQ-LLM-001 · AC-LLM-1

## M2 — Channels, Brand, Style (недели 4–6)

- [ ] T1.20 Channels CRUD: init Brand/Style/Memory, publish_mode, quality_threshold, soft-delete 30 дней, лимиты тарифа — REQ-WS-010..014 · AC-WS-2,4
- [ ] T1.21 Brand Profile: все поля, горячее применение — REQ-STYLE-001..002
- [ ] T1.22 AI Personality: пресеты + кастомные — REQ-STYLE-010..012
- [ ] T1.23 Style Learning ingest: telegram-канал, архив, web, PDF, DOCX — REQ-STYLE-020
- [ ] T1.24 Style Profile extraction (структурные метрики) + human summary + правка — REQ-STYLE-021, 024 · AC-STYLE-1,5
- [ ] T1.25 Style Embedding (pgvector) + few-shot выборка + style match score — REQ-STYLE-022, 026 · AC-STYLE-2
- [ ] T1.26 Инкрементальное дообучение, предупреждение о малом корпусе — REQ-STYLE-023, 025 · AC-STYLE-4

## M3 — Sources & Ingestion (недели 5–7)

- [ ] T1.30 Интерфейс SourceConnector + scheduler fetch-задач (cron per source, ретраи, degraded) — REQ-SRC-002, 011..012 · AC-SRC-4
- [ ] T1.31 Коннекторы: rss, web(+readability), telegram, file(PDF/DOCX со структурой) — REQ-SRC-001, 024 · AC-SRC-3
- [ ] T1.32 Нормализация ContentItem, фильтры до сохранения, immutable body — REQ-SRC-013, 020, 023 · AC-SRC-1
- [ ] T1.33 Дедуп: hash + семантический (0.92/30д/канал), связи-подтверждения — REQ-SRC-021..022 · AC-SRC-2
- [ ] T1.34 База знаний: загрузка документов, hybrid search (BM25+vector+RRF) — REQ-SRC-030..032 · AC-SRC-5

## M4 — Agents & Pipeline (недели 7–10)

- [ ] T1.40 Agent runner: tool-use цикл, typed I/O, Budget, allowlist + audit — REQ-AGENT-001..004 · AC-AGENT-1,4
- [ ] T1.41 Инструменты: sources.search, knowledge.search, memory.search/write, style.examples, facts.list — DES-AGENT §2
- [ ] T1.42 Channel Memory: структурный+векторный слои, проверка повторов, UI-редактирование — REQ-AGENT-020..023 · AC-AGENT-2
- [ ] T1.43 Агенты: Research (по источникам), Planner, Writer (claims-маркеры), SEO, Reviewer (структурированный отчёт, цикл ≤2) — REQ-AGENT-010, 012..015 · AC-AGENT-3,5
- [ ] T1.44 Оркестратор Asynq: контракт Stage, RunContext, resume после сбоя, события жизненного цикла, trace — REQ-PIPE-001..005 · AC-PIPE-1,2
- [ ] T1.45 Stage configs (модель/промпт/лимиты/fallback, горячее применение) — REQ-PIPE-010..013 · AC-PIPE-3,4
- [ ] T1.46 Типы контента (декларативные шаблоны: статья, новость, пост, thread, дайджест — стартовый набор) — REQ-PIPE-020..021
- [ ] T1.47 Ежедневный запуск по расписанию канала + ручной запуск — REQ-PIPE-003

## M5 — Quality Gate (недели 9–11)

- [ ] T1.50 Claims: связывание утверждений с evidence, unverified/stale, блок авто-публикации — REQ-QS-010..014 · AC-QS-1
- [ ] T1.51 Плагиат: n-граммы + близость абзацев, авто-rewrite ≤2, исключение цитат — REQ-QS-015..017 · AC-QS-2
- [ ] T1.52 Policy post-filter (детерминированный): banned words, дисклеймеры, глоссарий; версия system:policy; policy_blocked — REQ-QS-020..022 · AC-QS-3,4
- [ ] T1.53 Moderation через Gateway — REQ-QS-023
- [ ] T1.54 Quality Score (веса канала, пояснения, порог) — REQ-QS-001..003 · AC-QS-5
- [ ] T1.55 Eval-набор галлюцинаций (recall ≥ 0.8) — AC-QS-6

## M6 — Publishing & Calendar (недели 10–12)

- [ ] T1.60 Articles + immutable versions + diff + rollback + авторство ai/user/system — REQ-PUB-020..022 · AC-PUB-4
- [ ] T1.61 Режимы auto/approval/co-edit; approval-очередь: approve/reject/revise-с-инструкцией — REQ-PUB-010..013 · AC-PUB-1,2,3
- [ ] T1.62 Publisher-интерфейс + telegram-адаптер (форматирование, ретраи, failed) — REQ-PUB-030..033 · AC-PUB-5,6
- [ ] T1.63 Контент-календарь: статусы, drag&drop, таймзона канала — REQ-PUB-001..003
- [ ] T1.64 Уведомления (in-app + email) для approval/failed/degraded — REQ-PUB-012, REQ-SRC-012

## M7 — Billing & Analytics-минимум (недели 11–13)

- [ ] T1.70 Тарифы Free/Starter/Pro (+Enterprise-override), маппинг tier→модели конфигурацией — REQ-BILL-001..010 · AC-BILL-1
- [ ] T1.71 Usage: счётчики, 80%/100% пороги, билинговый период, заморозка при даунгрейде — REQ-BILL-011, 020..023 · AC-BILL-3,4
- [ ] T1.72 Платёжный провайдер (Stripe-совместимый), grace period, события биллинга — REQ-BILL-030..032
- [ ] T1.73 Сбор метрик Telegram по расписанию (1ч…7д), time series, unavailable-семантика — REQ-AN-001..003 · AC-AN-1,2
- [ ] T1.74 Дашборд канала: рост, CTR/ER (где доступно), лучшие темы/часы, стоимость контента — REQ-AN-010..011 · AC-AN-6

## M8 — Frontend & Release (недели 8–14, параллельно)

- [ ] T1.80 Next.js каркас: auth, workspace switcher, роли в UI
- [ ] T1.81 Мастер онбординга: канал → бренд → стиль → источники → первый запуск (метрика time-to-first-post)
- [ ] T1.82 Экраны: календарь, approval-очередь, редактор с diff версий, память канала, аналитика, админка платформы
- [ ] T1.83 e2e smoke: регистрация → онбординг → генерация → approve → публикация в тестовый TG-канал
- [ ] T1.84 Нагрузочный тест quota (конкурентные генерации) — AC-BILL-2
- [ ] T1.85 Security pass: tenancy-фаззинг (404), маскирование секретов, prompt-injection тесты на фикстурах источников

## Definition of Done (Phase 1)

1. Все AC модулей WS, STYLE, SRC, PIPE, AGENT, LLM, PUB, QS, BILL (MVP-скоуп) зелёные в CI.
2. Метрики `00-overview.md §8` измеряются на staging.
3. Ежедневный запуск демо-канала стабильно проходит 7 дней подряд без ручных вмешательств (режим approval).
