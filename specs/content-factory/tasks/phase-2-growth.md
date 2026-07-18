# Tasks — Phase 2: Growth

**Цель:** самообучающаяся редакция: тренды, feedback loop, эксперименты,
массовая генерация, Workflow Builder, изображения, мультиязычность.

---

## Источники и исследование

- [ ] T2.01 Коннекторы: YouTube (транскрипты), Twitter/X, Reddit, GitHub — REQ-SRC-001
- [ ] T2.02 Коннекторы: Notion, Google Drive, Dropbox, Confluence, Email, Google Alerts, новостные API — REQ-SRC-001
- [ ] T2.03 AI Trend Finder: trend_signals (Google Trends, HN, Reddit, YouTube, Telegram, новости, GitHub), ранжирование под аудиторию — REQ-AGENT-011
- [ ] T2.04 web.search-инструмент для Research/Reviewer — DES-AGENT §2

## Feedback Loop и эксперименты

- [ ] T2.10 Еженедельная агрегация метрик → выводы в память (пороги выборки, low_confidence) — REQ-AN-020, 023 · AC-AN-3,4
- [ ] T2.11 Применение выводов в Planner/Writer + лента «что ИИ изменил и почему» + off-switch — REQ-AN-021..022
- [ ] T2.12 A/B: варианты заголовков/вступлений/CTA, выбор победителя, паттерн в память — REQ-AN-030..031 · AC-AN-5

## Пайплайн

- [ ] T2.20 Миграция оркестрации Asynq → Temporal (контракт Stage неизменен) — REQ-PIPE-001, ADR-002
- [ ] T2.21 Массовая генерация: batch-runs, семафоры per-workspace, частичный результат на лимите — REQ-PIPE-030..032 · AC-PIPE-6
- [ ] T2.22 Workflow Builder: визуальный редактор DAG, валидатор (ацикличность, quality-gate), исполнение — REQ-PIPE-040..041 · AC-PIPE-5
- [ ] T2.23 Полный набор типов контента (все 26 из REQ-PIPE-020) — REQ-PIPE-020..021
- [ ] T2.24 Событийный триггер запуска (TrendDetected) — REQ-PIPE-003

## Контент

- [ ] T2.30 Генерация изображений: обложка, баннер, иллюстрации, инфографика, миниатюры (Image через Gateway, стиль из Brand) — REQ-EXT-040
- [ ] T2.31 Мультиязычность: адаптация (не перевод), Quality Gate per язык — REQ-QS-030
- [ ] T2.32 Publisher-адаптеры: WordPress, generic webhook — REQ-PUB-030

## Платформа

- [ ] T2.40 Meilisearch/OpenSearch для полнотекстового поиска UI — DES-ARCH §2
- [ ] T2.41 Public API v1 (паритет с UI) + API-ключи со скоупами + OpenAPI из кода — REQ-EXT-001..004 · AC-EXT-1,3
- [ ] T2.42 Webhooks: HMAC, ретраи 24ч, DLQ, рецепты Slack/Discord/Telegram/Email — REQ-EXT-010..012 · AC-EXT-2

## Definition of Done (Phase 2)

1. Feedback loop доказуемо влияет на план (AC-AN-3) минимум на 3 живых каналах.
2. Batch 100 идей → 20 статей проходит в пределах лимитов и SLA.
3. Публичный API покрывает 100% операций MVP.
