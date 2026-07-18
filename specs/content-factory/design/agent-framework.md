# DES-AGENT — AI Agent Framework

**Статус:** Draft · **Реализует:** REQ-AGENT-*, REQ-STYLE-02x

Агент — не «один большой промпт», а управляемый цикл «рассуждение → инструмент →
наблюдение» с типизированным контрактом, бюджетом и allowlist инструментов.

---

## 1. Контракт агента (REQ-AGENT-001)

```go
package agent

type Agent interface {
    Key() string                     // research|planner|writer|seo|reviewer|publisher|analytics
    Run(ctx context.Context, in Input) (Output, error)
}

type Input struct {
    Channel   ChannelContext   // brand, personality, publish mode, quality threshold
    Style     StyleContext     // style profile summary + few-shot примеры (top-k по embedding)
    Task      json.RawMessage  // типизированный вход конкретного агента
    Budget    Budget           // MaxSteps, MaxTokens, MaxCostUSD (REQ-AGENT-004)
    TraceID   string
}

type Output struct {
    Result   json.RawMessage
    Partial  bool             // budget_exceeded → частичный результат
    Cost     CostReport
}
```

Исполнение — runner с tool-use циклом поверх `llm.Client`:

```
loop (пока не final и не исчерпан Budget):
    resp := llm.Chat(messages, tools=allowlist(agent))
    if resp.ToolCalls: выполнить → добавить результат в messages
    else: final
```

## 2. Инструменты и allowlist (REQ-AGENT-002..003)

| Инструмент | research | planner | writer | seo | reviewer | publisher | analytics |
|---|---|---|---|---|---|---|---|
| `sources.search` (по content_items) | ✅ | ✅ | ✅ | — | ✅ | — | — |
| `knowledge.search` (RAG, hybrid) | ✅ | — | ✅ | — | ✅ | — | — |
| `web.search` (Phase 2) | ✅ | — | — | — | ✅ | — | — |
| `memory.search` / `memory.write` | ✅ | ✅ | ✅ | — | ✅ | — | ✅ |
| `style.examples` (few-shot) | — | — | ✅ | — | ✅ | — | — |
| `facts.list` (утверждения этапа extraction) | — | — | ✅ | — | ✅ | — | — |
| `image.generate` | — | — | — | — | — | ✅ | — |
| `publish.send` | — | — | — | — | — | ✅ | — |
| `metrics.query` | — | ✅ | — | — | — | — | ✅ |

Вызов вне allowlist → ошибка + запись в audit_log (AC-AGENT-1). Контент источников
передаётся инструментами как данные, никогда — как системные инструкции
(prompt-injection защита, см. DES-ARCH §6).

## 3. Специализированные агенты

### Research Agent (REQ-AGENT-010..011)
- Вход: свежие `content_items`, приоритеты/доверие источников.
- Trend Finder — отдельная scheduled-задача: коннекторы Google Trends, HN, Reddit,
  YouTube и т.д. складывают сигналы в `trend_signals`; агент ранжирует темы
  относительно интересов аудитории (memory: liked/disliked темы).
- Выход: `[]TopicCandidate{title, why, evidence[], score}`.

### Planning Agent (REQ-AGENT-012)
- Вход: TopicCandidates, календарь, memory-паттерны, аналитика (лучшие часы/типы).
- Выход: план `[]PlannedPost{topic, content_type, scheduled_at, rationale}` —
  «сегодня новость, через два часа история, завтра большая статья, в пятницу подборка».

### Writer Agent (REQ-AGENT-013)
- Промпт собирается из: personality system prompt + brand constraints + style summary
  + few-shot (top-k `style_documents` по близости к теме) + факты с источниками.
- Пишет строго по шаблону типа контента (REQ-PIPE-021); каждое фактическое
  утверждение сопровождает маркером источника `[claim:id]` для этапа QS.

### SEO Agent (REQ-AGENT-015)
- Выход: meta description, keywords, теги/хештеги, alt-тексты, рекомендации структуры.

### Reviewer / AI Editor (REQ-AGENT-014)
- Структурированный отчёт (JSON Schema): repeats, grammar, hallucination_flags,
  tone_match, logic_issues, structure_issues, seo_issues, clarity, headline_ctr_score,
  style_match_score, verdict (`approve|revise`), revise_instructions.
- До 2 циклов Writer↔Reviewer, затем материал идёт дальше с текущим вердиктом.

### Publisher Agent (REQ-AGENT-016)
- Уважает publish_mode; форматирование делегирует publish-адаптеру.

### Analytics Agent (REQ-AGENT-017)
- Скользящие выводы → `channel_memory` (kind=pattern/liked/disliked), с порогом
  выборки (REQ-AN-023).

## 4. Channel Memory (REQ-AGENT-020..023)

Двухслойная (см. `data-model.md: channel_memory`):

- **Структурный слой** — записи с `kind`: published, do_not_repeat, liked, disliked,
  pattern, preference; pinned-записи никогда не вытесняются.
- **Векторный слой** — embedding содержимого для `memory.search`.

Проверка повторов идей (REQ-AGENT-021): косинусная близость новой идеи к
`kind=published` за окно канала (default 90 дней); порог 0.88 → reject/reframe.

UI памяти: список записей, удаление, ручное добавление запретов и предпочтений,
закрепление (REQ-AGENT-023).

## 5. Бюджеты (REQ-AGENT-004)

- Budget задаётся stage_config'ом и тарифом; runner останавливает цикл при
  достижении MaxSteps/MaxTokens/MaxCostUSD и возвращает `Partial=true`.
- Частичный результат сохраняется в run-контексте; пайплайн решает: fallback,
  retry с меньшим скоупом или деградация.

## 6. AI Copilot (Phase 3, REQ-AGENT-030..031)

- Отдельный endpoint `POST /v1/copilot/suggest` (streaming): варианты заголовков,
  вступлений, CTA, идей изображений, SEO, FAQ — на базе тех же инструментов
  writer/reviewer, но с бюджетом interactive-класса (короткие ответы, fast tier).
- Все предложения применяются явным действием пользователя; применение создаёт
  версию с автором `user:<id>` (Copilot лишь предлагал).
