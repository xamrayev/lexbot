# DES-PIPE — Content Pipeline & Publishing

**Статус:** Draft · **Реализует:** REQ-PIPE-*, REQ-SRC-01x/02x, REQ-QS-*, REQ-PUB-03x

---

## 1. Оркестрация (REQ-PIPE-001)

**MVP — Asynq**: каждый этап — задача; состояние запуска — в `pipeline_runs.stages`
(jsonb) + идемпотентные обработчики. Продолжение после сбоя: воркер читает последний
завершённый этап и ставит следующий.

**Phase 2 — Temporal**: конвейер как workflow, этапы — activities; ретраи, таймауты
и resume «из коробки». Контракт этапа не меняется, поэтому миграция — замена
оркестратора, не этапов.

### Контракт этапа

```go
type Stage interface {
    Key() string
    Run(ctx context.Context, rc *RunContext) (StageResult, error) // идемпотентно
}

type RunContext struct {   // сериализуется между этапами (S3/PG)
    RunID, TraceID string
    Channel  ChannelContext
    Items    []ContentItemRef      // после ingest/dedup
    Facts    []Claim               // после extraction
    Ideas    []TopicCandidate
    Plan     []PlannedPost
    Draft    *ArticleDraft
    Review   *ReviewReport
    Quality  *QualityReport
}
```

Каждый этап читает `stage_configs` (модель, промпт, лимиты, fallback — REQ-PIPE-010)
в момент запуска → изменения применяются без рестарта (REQ-PIPE-011).

## 2. Маппинг 15 канонических этапов

| # | Этап | Модуль/агент | Класс модели |
|---|---|---|---|
| 1 | Поиск нового контента | source (fetch jobs) | — |
| 2 | Удаление дубликатов | source (hash + embedding) | embedding |
| 3 | Суммаризация | stage `summarize` | economy |
| 4 | Извлечение фактов | stage `extract_facts` | fast |
| 5 | Проверка источников | quality (trust, cross-check) | — /fast |
| 6 | Проверка актуальности | quality + memory (повторы, freshness) | embedding |
| 7 | Генерация идей | Research Agent | fast |
| 8 | План публикаций | Planning Agent | fast |
| 9 | Написание статьи | Writer Agent | premium |
| 10 | Саморедактирование | Reviewer Agent (цикл ≤2) | premium/fast |
| 11 | SEO | SEO Agent | economy |
| 12 | Проверка качества | quality (score, плагиат, политика) | fast |
| 13 | Отправка пользователю | approval queue + уведомления | — |
| 14 | Публикация | publish adapter | — |
| 15 | Сбор аналитики | analytics (scheduled) | — |

Multi-Model Pipeline (REQ-PIPE-012): классы в таблице — дефолт, переопределяются
`stage_configs`.

## 3. Ingestion (REQ-SRC-01x/02x)

```
scheduler (cron per source) → fetch job → SourceConnector.Fetch()
    → normalize → filter → hash dedup → embed → semantic dedup (0.92, 30d, per-channel)
    → save content_item → event SourceUpdated
```

`SourceConnector` (Plugin SDK, REQ-SRC-002):

```go
type SourceConnector interface {
    Type() string
    Validate(cfg json.RawMessage) error
    Fetch(ctx context.Context, cfg json.RawMessage, since time.Time) ([]RawItem, error)
}
```

MVP-коннекторы: telegram (Bot API/MTProto reader), rss, web (crawler + readability),
file (PDF/DOCX через извлечение с сохранением структуры — REQ-SRC-024).

## 4. Quality Gate (этап 12)

Последовательность (REQ-QS-*):

1. **Claims check** — каждый `[claim:id]` маркер связан с evidence; непокрытые →
   `unverified` (REQ-QS-011); freshness-окно → `stale` (REQ-QS-014).
2. **Plagiarism** — n-граммы (≥12 слов) + попарная близость абзацев к исходникам
   (≥0.95) → авто-Rewrite (≤2 цикла) → повторная проверка (REQ-QS-015..016);
   цитаты с атрибуцией — исключение (REQ-QS-017).
3. **Policy post-filter** (детерминированный, NFR-QS-2): banned words (замена/блок),
   дисклеймеры по типу материала, глоссарий терминов; изменения — версия
   `system:policy` (REQ-QS-020..021); неисправимое → `policy_blocked` (REQ-QS-022).
4. **Moderation** через Gateway (REQ-QS-023).
5. **Quality Score** — веса канала × компоненты: credibility (доля verified claims),
   readability (метрики читабельности для языка канала), seo (чеклист SEO Agent),
   style (style match score, REQ-STYLE-026), engagement (прогноз Reviewer).
   Ниже порога → не публикуем автоматически (REQ-QS-002).

## 5. Approval & Publishing (REQ-PUB-*)

```
Quality Gate pass
  ├─ mode=auto и score ≥ threshold → schedule → publish
  ├─ mode=auto и score < threshold → approval queue
  ├─ mode=approval → approval queue → (approve → schedule) | (revise → Writer цикл) | reject
  └─ mode=co-edit → draft для совместного редактирования
```

`Publisher` (адаптеры, REQ-PUB-030):

```go
type Publisher interface {
    Platform() string
    Publish(ctx context.Context, a ArticleVersion, cfg json.RawMessage) (ExternalRef, error)
    FetchMetrics(ctx context.Context, ref ExternalRef) (map[string]float64, error) // REQ-AN-001
}
```

MVP: `telegram` (Bot API: text limits, markdown → entities, медиавложения). Phase 2:
`wordpress`, `webhook`. Ретраи по политике; после исчерпания → `failed` +
уведомление, материал остаётся `approved` (REQ-PUB-031).

## 6. Массовая генерация (REQ-PIPE-030..032)

Batch-запуск = родительский run + дочерние runs per материал; постановка задач
через семафор per-workspace (ограничение параллелизма); Quota Guard останавливает
постановку на границе лимита с частичным результатом.

## 7. Workflow Builder (Phase 2, REQ-PIPE-040..042)

- Блоки = зарегистрированные Stage'ы + плагины `WorkflowBlock`.
- DAG хранится в `pipeline_definitions.dag` (JSON): nodes{stage_key, config},
  edges; валидатор: ацикличность, типы вход/выход, обязательный quality-gate перед
  publish-узлом.
- Исполнение — тем же оркестратором (топологический порядок).

## 8. Наблюдаемость

- Каждый этап: span OpenTelemetry (trace_id запуска), метрики
  `pipeline_stage_duration_seconds{stage}`, `pipeline_runs_total{status}`,
  `pipeline_cost_usd{channel}`.
- Событие `StageCompleted` содержит длительность и стоимость этапа — дашборд
  Grafana «стоимость/латентность по этапам».
