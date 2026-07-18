# DES-INFRA — Infrastructure & Operations

**Статус:** Draft · **Реализует:** Constitution X, NFR-* всех модулей

---

## 1. Топология (MVP, Docker Compose)

```yaml
services:
  traefik:        # TLS, маршрутизация, rate limit на edge
  api:            # cmd/server (Go), горизонтально масштабируем
  worker:         # cmd/worker — pipeline/ingestion/analytics очереди
  frontend:       # Next.js
  postgres:       # 16 + pgvector
  redis:          # Asynq, кэш, quota guard, rate limiters
  nats:           # JetStream — Event Bus
  minio:          # файлы источников, media, run-контексты
  prometheus:
  grafana:
```

Phase 2+: Temporal (server + UI), Meilisearch/OpenSearch; выделение сервисов —
см. DES-ARCH §9.

## 2. Конфигурация

- 12-factor: env-переменные + файл дефолтов; никакой конфигурации в коде.
- Динамическая конфигурация (модели, промпты, тарифы, stage configs) — в PG,
  кэш с инвалидацией по событиям (`PromptUpdated`, `ModelUpdated`).
- Секреты процессов (DB DSN, master key) — env/секрет-хранилище оркестратора;
  секреты пользователей/провайдеров — Secrets Manager (DES-ARCH §6).

## 3. Наблюдаемость (Constitution X)

| Сигнал | Инструмент | Ключевые элементы |
|---|---|---|
| Метрики | Prometheus + Grafana | llm_* (DES-LLM §7), pipeline_* (DES-PIPE §8), http, очереди (глубина, возраст), бизнес (публикации, approvals) |
| Трейсы | OpenTelemetry → Tempo/Jaeger | trace_id: HTTP → очередь → этапы → LLM-вызовы |
| Логи | slog (JSON) → Loki | всегда: trace_id, workspace_id, channel_id; никогда: секреты, полные промпты (отдельный поток с ретенцией) |
| Алерты | Alertmanager | падение доли успешных runs < 99%, рост стоимости > бюджета, глубина очереди, breaker open, деградация источников |

## 4. Надёжность

- Очереди: at-least-once, идемпотентные обработчики (dedup по task id).
- Ретраи: экспоненциальный backoff + jitter; DLQ для webhooks и publish.
- Graceful shutdown: воркер дорабатывает текущий этап; состояние — в run-контексте.
- Бэкапы: PG — WAL-G (PITR), MinIO — версионирование бакетов; restore-тест —
  ежемесячно (runbook).
- RPO ≤ 15 мин, RTO ≤ 2 ч (MVP-цели).

## 5. CI/CD

Пайплайн (GitHub Actions):

1. lint (golangci-lint, eslint) + `go vet`;
2. arch-тесты границ модулей (DES-ARCH §3, AC-LLM-1);
3. unit + интеграционные тесты (testcontainers: PG+pgvector, Redis, NATS);
4. e2e пайплайна на фейковом Provider (AC-PIPE-1..2);
5. миграции — прогон вперёд/назад на чистой БД;
6. сборка образов, деплой в staging, smoke.

Правила: main всегда деплоябелен; фичи — за флагами; миграции только
backward-compatible (expand → migrate → contract).

## 6. Безопасность эксплуатации

- Traefik: TLS, security headers, edge rate limit per IP.
- Контейнеры: non-root, read-only FS где возможно, минимальные образы (distroless).
- Зависимости: dependabot/renovate + govulncheck в CI.
- Доступ к prod-данным — только через audit-логируемые инструменты.

## 7. Производительность (сводка NFR)

| NFR | Цель | Проверка |
|---|---|---|
| Gateway overhead | p99 < 50 мс | bench в CI |
| Полный запуск канала (≤50 items) | < 15 мин | e2e с фейковым Provider (тайминги этапов) |
| RSS 100 элементов | < 30 сек | интеграционный тест |
| Style learning (500 док.) | < 10 мин | фоновая задача, прогресс |
| Quality Gate | < 2 мин | e2e |
