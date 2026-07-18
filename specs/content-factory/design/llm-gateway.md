# DES-LLM — LLM Gateway

**Статус:** Draft · **Реализует:** REQ-LLM-*, REQ-BILL-021, Constitution II, VI

Единая точка доступа ко всем LLM-провайдерам: маршрутизация, failover, лимиты,
логирование, стоимость.

---

## 1. Поток вызова

```
Application (agent/stage)
    ↓  llm.Client (класс качества или model_id + бюджет)
Quota Guard         — атомарная проверка лимитов ДО вызова (REQ-LLM-051)
    ↓
Router              — разрешение класса → модель по тарифу и конфигурации (REQ-LLM-021)
    ↓
Circuit Breaker / Rate Limiter (per model / provider key)   (REQ-LLM-031, 033)
    ↓
Provider Adapter    — OpenAI-compatible | Anthropic | Gemini | Azure (REQ-LLM-003)
    ↓
Usage Recorder      — llm_calls + usage_counters в одной транзакции (REQ-LLM-050)
```

## 2. Интерфейс провайдера (REQ-LLM-002)

```go
package llm

type Provider interface {
    Chat(ctx context.Context, req ChatRequest) (*ChatResponse, error)
    ChatStream(ctx context.Context, req ChatRequest) (ChatStream, error)
    Embedding(ctx context.Context, req EmbeddingRequest) ([][]float32, error)
    Image(ctx context.Context, req ImageRequest) (*ImageResponse, error)
    SpeechToText(ctx context.Context, req STTRequest) (*STTResponse, error)
    TextToSpeech(ctx context.Context, req TTSRequest) (*TTSResponse, error)
    Rerank(ctx context.Context, req RerankRequest) (*RerankResponse, error)
    Moderation(ctx context.Context, req ModerationRequest) (*ModerationResponse, error)

    Capabilities() CapabilitySet   // какие операции реально поддержаны
}

type ChatRequest struct {
    Model       string
    Messages    []Message
    Tools       []ToolDef        // tool use для агентов
    MaxTokens   int
    Temperature float32
    Metadata    CallMetadata     // trace_id, workspace, channel, run, stage
}

type ChatResponse struct {
    Content      string
    ToolCalls    []ToolCall
    TokensIn     int
    TokensOut    int
    FinishReason string
}
```

Адаптеры:

- `openai_compatible` — один адаптер закрывает OpenAI, OpenRouter, vLLM, Ollama,
  LM Studio, LiteLLM, DeepSeek, Groq, Together, Fireworks, Cerebras, Mistral
  (конфигурация: base URL + key + особенности диалекта);
- `anthropic`, `gemini`, `azure` — нативные адаптеры (маппинг ролей, tool use,
  streaming).

Новый провайдер = реализация интерфейса или строка конфигурации openai_compatible
(REQ-LLM-004). Регистрация — через registry:

```go
func Register(adapter string, factory func(cfg ProviderConfig) (Provider, error))
```

## 3. Клиент для приложений

Бизнес-код не выбирает провайдера — только класс качества или роль этапа:

```go
type Client interface {
    // tier: premium | fast | economy — разрешается Router'ом по тарифу workspace
    ChatTier(ctx context.Context, tier Tier, req ChatRequest) (*ChatResponse, error)
    // точная модель — только для стадий с явной конфигурацией (stage_configs)
    ChatModel(ctx context.Context, modelID uuid.UUID, req ChatRequest) (*ChatResponse, error)
    Embed(ctx context.Context, texts []string) ([][]float32, error)
    Moderate(ctx context.Context, text string) (*ModerationResult, error)
}
```

## 4. Router & Failover (REQ-LLM-030..032)

```
resolve(tier, workspace) → candidate models (по plan.tiers, enabled, breaker state)
try primary:
    timeout | 429 | 5xx | overloaded →
        record failure (breaker), try next in model_fallbacks (rank asc)
all failed → StageError{Retryable: true}
```

- Circuit breaker: per model, окно N=5 сбоев → open 60s → half-open (1 пробный).
- Rate limiter: token bucket per provider secret; при заполнении — очередь
  с дедлайном таймаута этапа (REQ-LLM-033).
- Failover сохраняет семантику: тот же промпт, маппинг параметров адаптером;
  ответ помечается `fallback_used=true` в `llm_calls`.

## 5. Quota Guard (REQ-LLM-051, REQ-BILL-021)

Атомарность через Redis Lua (счётчик периода) с write-behind в `usage_counters`:

```
EVAL: current = INCRBY usage:{ws}:{period}:{metric} estimated
      if current > limit: DECRBY ...; return QUOTA_EXCEEDED
```

После ответа — корректировка на фактические токены. Жёсткий/мягкий пороги бюджета
(REQ-LLM-052) проверяются тем же механизмом.

## 6. Prompt Library (REQ-LLM-040..042)

- Хранение: таблица `prompts (key, version, template, variables, is_active)`.
- Рендеринг: Go text/template без побочных функций; missing variable → ошибка до
  вызова модели (REQ-LLM-042).
- Кэш активных версий в памяти с инвалидацией по событию `PromptUpdated`.
- Базовый набор ключей: `generate_article`, `rewrite`, `seo`, `summarize`,
  `translate`, `title`, `fact_check`, `review`, `trend_analysis`.

## 7. Стоимость и телеметрия

- Стоимость = tokens_in × price_input + tokens_out × price_output (цены модели
  на момент вызова фиксируются в `llm_calls`).
- Метрики Prometheus: `llm_calls_total{model,status}`, `llm_latency_seconds{model}`,
  `llm_cost_usd_total{workspace,model}`, `llm_breaker_state{model}`,
  `llm_fallback_total{from,to}`.
- Трейсинг: OpenTelemetry span на каждый вызов, привязан к trace запуска пайплайна
  (Constitution X).
- Логи промптов — отдельный поток с ретенцией и редактированием секретов
  (REQ-LLM-005).

## 8. Тарифы и маппинг моделей (REQ-BILL-010, REQ-LLM-021)

```
plans.tiers:      Free → [economy]
                  Starter → [economy, fast]
                  Pro → [economy, fast, premium]
                  Enterprise → per-workspace override (enterprise_model_grants)
ai_models.tier:   gpt-5-nano → economy, gpt-5-mini → fast,
                  gpt-5 / claude / gemini / deepseek → premium (пример)
```

Пользователь видит только «Высокое качество / Быстро / Экономично»; резолвинг —
на Router. Админ управляет всем через `admin`-модуль: провайдеры, ключи, base URL,
модели всех типов (chat/embedding/vision/image/audio), включение/выключение, цены,
привязка к тарифам.

## 9. Тестирование

- Фейковый Provider (`llm/fake`) с программируемыми ответами/ошибками — для всех
  тестов пайплайна (никаких реальных вызовов в CI).
- Контрактные тесты адаптеров против записанных фикстур (VCR-подход).
- Arch-тест: импорт SDK провайдеров вне `internal/llm` — ошибка CI (AC-LLM-1).
