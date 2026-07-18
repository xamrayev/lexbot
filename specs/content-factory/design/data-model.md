# DES-DATA — Data Model

**Статус:** Draft · **Реализует:** REQ-WS-*, REQ-STYLE-*, REQ-SRC-*, REQ-PUB-02x, REQ-AN-*, REQ-BILL-02x

PostgreSQL 16 + pgvector. Все доменные таблицы несут `workspace_id` (tenancy)
и `created_at/updated_at`. Ниже — ключевые таблицы (DDL упрощён).

---

## 1. Identity & Tenancy

```sql
CREATE TABLE users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email         citext UNIQUE NOT NULL,
    password_hash text,                          -- null при OAuth
    locale        text NOT NULL DEFAULT 'ru'
);

CREATE TABLE workspaces (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name       text NOT NULL,
    plan_id    uuid NOT NULL REFERENCES plans(id),
    deleted_at timestamptz
);

CREATE TABLE workspace_members (
    workspace_id uuid REFERENCES workspaces(id),
    user_id      uuid REFERENCES users(id),
    role         text NOT NULL CHECK (role IN
                 ('owner','admin','editor','author','seo','viewer')),
    PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE invitations (
    id           uuid PRIMARY KEY,
    workspace_id uuid NOT NULL,
    email        citext NOT NULL,
    role         text NOT NULL,
    expires_at   timestamptz NOT NULL             -- REQ-WS-021: 7 дней
);

CREATE TABLE audit_log (                          -- REQ-WS-024
    id           bigserial PRIMARY KEY,
    workspace_id uuid NOT NULL,
    actor        text NOT NULL,                   -- user:<id> | ai:<agent> | system:policy
    action       text NOT NULL,
    entity       text NOT NULL,
    entity_id    uuid,
    before       jsonb,
    after        jsonb,
    occurred_at  timestamptz NOT NULL DEFAULT now()
);
```

## 2. Channels, Brand, Style

```sql
CREATE TABLE channels (
    id             uuid PRIMARY KEY,
    workspace_id   uuid NOT NULL REFERENCES workspaces(id),
    name           text NOT NULL,
    publish_mode   text NOT NULL DEFAULT 'approval'
                   CHECK (publish_mode IN ('auto','approval','co-edit')),  -- REQ-WS-014
    quality_threshold int NOT NULL DEFAULT 70,    -- REQ-QS-002
    timezone       text NOT NULL DEFAULT 'UTC',
    deleted_at     timestamptz                    -- REQ-WS-012: soft delete
);

CREATE TABLE brand_profiles (                     -- REQ-STYLE-001
    channel_id      uuid PRIMARY KEY REFERENCES channels(id),
    title           text, description text, topic text,
    audience        text, language text, tone text,
    banned_topics   text[], favorite_topics text[],
    seo_keywords    text[], hashtags text[],
    emoji_policy    text, formatting_style text,
    target_length   int4range,
    banned_words    text[],                       -- REQ-QS-020
    disclaimers     jsonb,                        -- {content_type: text}
    glossary        jsonb                         -- {term: preferred_term}
);

CREATE TABLE ai_personalities (                   -- REQ-STYLE-010..011
    id            uuid PRIMARY KEY,
    channel_id    uuid,                           -- null = глобальный пресет
    name          text NOT NULL,                  -- Журналист, Научный, Блогер...
    system_prompt text NOT NULL,
    temperature   real NOT NULL DEFAULT 0.7,
    examples      jsonb
);

CREATE TABLE style_profiles (                     -- REQ-STYLE-021
    channel_id       uuid PRIMARY KEY REFERENCES channels(id),
    vocabulary       jsonb,      -- любимые слова, частоты
    sentence_stats   jsonb,      -- распределения длин
    emotions         jsonb,
    structures       jsonb,      -- типовые структуры материалов
    headline_patterns jsonb,
    question_rate    real,
    humor            jsonb,
    cta_patterns     jsonb,
    human_summary    text,       -- REQ-STYLE-024
    corpus_size      int NOT NULL DEFAULT 0
);

CREATE TABLE style_documents (                    -- корпус обучения
    id          uuid PRIMARY KEY,
    channel_id  uuid NOT NULL,
    origin      text NOT NULL,   -- telegram|archive|web|pdf|word|notion|obsidian|gdocs
    content     text NOT NULL,
    embedding   vector(1536)     -- REQ-STYLE-022 (Style Embedding, per-channel)
);
CREATE INDEX ON style_documents USING hnsw (embedding vector_cosine_ops);
```

## 3. Sources & Ingestion

```sql
CREATE TABLE sources (                            -- REQ-SRC-010
    id            uuid PRIMARY KEY,
    channel_id    uuid NOT NULL REFERENCES channels(id),
    name          text NOT NULL,
    type          text NOT NULL,   -- telegram|rss|web|youtube|pdf|... (plugin id)
    config        jsonb NOT NULL,  -- url, chat_id и т.п. (секреты — ссылкой на secrets)
    priority      int NOT NULL DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    schedule      text NOT NULL,   -- cron
    filter        jsonb,           -- keywords, regex, language
    language      text,
    trust_level   int NOT NULL DEFAULT 50 CHECK (trust_level BETWEEN 0 AND 100),
    status        text NOT NULL DEFAULT 'active'  -- active|degraded|disabled  REQ-SRC-012
);

CREATE TABLE content_items (                      -- REQ-SRC-020, immutable (REQ-SRC-023)
    id           uuid PRIMARY KEY,
    channel_id   uuid NOT NULL,
    source_id    uuid NOT NULL REFERENCES sources(id),
    url          text,
    title        text,
    body         text NOT NULL,
    language     text,
    author       text,
    published_at timestamptz,
    media        jsonb,
    content_hash bytea NOT NULL,
    embedding    vector(1536),
    duplicate_of uuid REFERENCES content_items(id)  -- REQ-SRC-022
);
CREATE UNIQUE INDEX ON content_items (channel_id, content_hash);
CREATE INDEX ON content_items USING hnsw (embedding vector_cosine_ops);

CREATE TABLE knowledge_documents (                -- REQ-SRC-030, база знаний / RAG
    id          uuid PRIMARY KEY,
    channel_id  uuid NOT NULL,
    title       text,
    content     text NOT NULL,
    tsv         tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
    embedding   vector(1536)
);
```

## 4. Content, Versions, Calendar

```sql
CREATE TABLE articles (
    id            uuid PRIMARY KEY,
    channel_id    uuid NOT NULL,
    content_type  text NOT NULL,   -- article|news|story|thread|... (REQ-PIPE-020)
    status        text NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft','in_review','approved','scheduled',
                                    'published','failed','policy_blocked')),
    current_version int NOT NULL DEFAULT 1,
    quality_score jsonb,           -- {total, credibility, readability, seo, style, engagement}
    scheduled_at  timestamptz,
    published_at  timestamptz,
    external_ref  jsonb            -- {platform, id, url}  REQ-PUB-032
);

CREATE TABLE article_versions (                   -- REQ-PUB-020, immutable
    article_id  uuid REFERENCES articles(id),
    version     int NOT NULL,
    author      text NOT NULL,     -- ai:writer | user:<id> | system:policy (REQ-QS-021)
    title       text,
    body        text NOT NULL,
    seo         jsonb,             -- meta, keywords, tags
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (article_id, version)
);

CREATE TABLE article_claims (                     -- REQ-QS-010..011
    id          uuid PRIMARY KEY,
    article_id  uuid NOT NULL,
    version     int NOT NULL,
    claim       text NOT NULL,
    status      text NOT NULL CHECK (status IN ('verified','unverified','stale')),
    trust       int,
    evidence    jsonb              -- [{content_item_id|knowledge_doc_id, quote}]
);

CREATE TABLE comments (                           -- REQ-WS-023
    id          uuid PRIMARY KEY,
    article_id  uuid NOT NULL,
    version     int,
    author_id   uuid NOT NULL,
    body        text NOT NULL
);
```

## 5. Pipeline & Agents

```sql
CREATE TABLE pipeline_definitions (               -- REQ-PIPE-040: DAG как данные
    id          uuid PRIMARY KEY,
    channel_id  uuid,                             -- null = платформенный дефолт
    name        text NOT NULL,
    dag         jsonb NOT NULL,
    is_active   boolean NOT NULL DEFAULT true
);

CREATE TABLE stage_configs (                      -- REQ-PIPE-010
    id             uuid PRIMARY KEY,
    pipeline_id    uuid NOT NULL,
    stage_key      text NOT NULL,  -- summarize|extract_facts|write|review|seo|...
    model_id       uuid REFERENCES ai_models(id),
    fallback_model_id uuid REFERENCES ai_models(id),
    prompt_key     text NOT NULL,
    prompt_version int,
    max_tokens     int, temperature real,
    timeout_sec    int NOT NULL DEFAULT 120,
    max_retries    int NOT NULL DEFAULT 2
);

CREATE TABLE pipeline_runs (                      -- REQ-PIPE-001..005
    id          uuid PRIMARY KEY,
    channel_id  uuid NOT NULL,
    pipeline_id uuid NOT NULL,
    trigger     text NOT NULL,     -- schedule|manual|event
    status      text NOT NULL,     -- running|succeeded|degraded|failed
    trace_id    text NOT NULL,
    cost_usd    numeric(12,6) NOT NULL DEFAULT 0,
    stages      jsonb              -- [{stage_key, status, started, finished, cost, error}]
);

CREATE TABLE channel_memory (                     -- REQ-AGENT-020..022
    id          uuid PRIMARY KEY,
    channel_id  uuid NOT NULL,
    kind        text NOT NULL,     -- published|do_not_repeat|liked|disliked|pattern|preference
    content     jsonb NOT NULL,
    embedding   vector(1536),
    pinned      boolean NOT NULL DEFAULT false,   -- REQ-AGENT-023
    source      text NOT NULL      -- feedback_loop|user|agent
);
CREATE INDEX ON channel_memory USING hnsw (embedding vector_cosine_ops);
```

## 6. LLM Platform (admin)

```sql
CREATE TABLE providers (                          -- REQ-LLM-003..004
    id         uuid PRIMARY KEY,
    name       text NOT NULL,
    adapter    text NOT NULL,      -- openai_compatible|anthropic|gemini|azure
    base_url   text,
    secret_ref uuid NOT NULL,      -- ссылка в secrets (REQ-LLM-023)
    enabled    boolean NOT NULL DEFAULT true
);

CREATE TABLE ai_models (                          -- REQ-LLM-020..021
    id          uuid PRIMARY KEY,
    provider_id uuid NOT NULL REFERENCES providers(id),
    display_name text NOT NULL,   -- "GPT-5", "DeepSeek", "Qwen"...
    model_id    text NOT NULL,    -- gpt-5, deepseek-chat, qwen3...
    kind        text NOT NULL,    -- chat|embedding|vision|image|audio
    tier        text NOT NULL CHECK (tier IN ('premium','fast','economy')),
    price_input  numeric(12,8),   -- $/1K tokens
    price_output numeric(12,8),
    enabled     boolean NOT NULL DEFAULT true
);

CREATE TABLE model_fallbacks (                    -- REQ-LLM-030
    model_id    uuid REFERENCES ai_models(id),
    fallback_id uuid REFERENCES ai_models(id),
    rank        int NOT NULL,
    PRIMARY KEY (model_id, rank)
);

CREATE TABLE prompts (                            -- REQ-LLM-040..041
    key        text NOT NULL,      -- generate_article|rewrite|seo|summarize|...
    version    int NOT NULL,
    template   text NOT NULL,
    variables  text[] NOT NULL,
    is_active  boolean NOT NULL DEFAULT false,
    PRIMARY KEY (key, version)
);

CREATE TABLE llm_calls (                          -- REQ-LLM-005, REQ-LLM-050
    id           bigserial PRIMARY KEY,
    trace_id     text NOT NULL,
    workspace_id uuid, channel_id uuid,
    run_id       uuid, stage_key text,
    model_id     uuid NOT NULL,
    fallback_used boolean NOT NULL DEFAULT false,
    tokens_in    int, tokens_out int,
    latency_ms   int,
    cost_usd     numeric(12,8),
    status       text NOT NULL,
    occurred_at  timestamptz NOT NULL DEFAULT now()
);
```

## 7. Billing & Analytics

```sql
CREATE TABLE plans (                              -- REQ-BILL-001, REQ-BILL-010
    id       uuid PRIMARY KEY,
    name     text NOT NULL,        -- Free|Starter|Pro|Enterprise
    limits   jsonb NOT NULL,       -- {channels, generations, sources, features[]}
    tiers    text[] NOT NULL       -- разрешённые классы моделей
);

CREATE TABLE usage_counters (                     -- REQ-BILL-020..021
    workspace_id uuid NOT NULL,
    period       daterange NOT NULL,
    metric       text NOT NULL,    -- generations|tokens_in|tokens_out|cost_usd|api_calls
    value        numeric NOT NULL DEFAULT 0,
    PRIMARY KEY (workspace_id, period, metric)
);

CREATE TABLE post_metrics (                       -- REQ-AN-001..002 (time series)
    article_id   uuid NOT NULL,
    collected_at timestamptz NOT NULL,
    metric       text NOT NULL,    -- views|ctr|comments|likes|shares|read_time|subs|unsubs
    value        numeric,          -- null = unavailable (REQ-AN-003)
    PRIMARY KEY (article_id, collected_at, metric)
);

CREATE TABLE experiments (                        -- REQ-AN-030..031
    id         uuid PRIMARY KEY,
    article_id uuid NOT NULL,
    dimension  text NOT NULL,      -- title|intro|cta
    variants   jsonb NOT NULL,
    winner     int,
    metric     text NOT NULL
);

CREATE TABLE secrets (                            -- Secrets Manager
    id         uuid PRIMARY KEY,
    workspace_id uuid,             -- null = платформенный секрет
    name       text NOT NULL,
    ciphertext bytea NOT NULL,     -- AES-256-GCM envelope
    key_id     text NOT NULL
);
```

## 8. Инварианты

1. `article_versions` и `content_items` — append-only (без UPDATE body; enforced
   триггером).
2. Любой INSERT в доменные таблицы содержит `workspace_id`, совпадающий с tenancy
   контекста запроса (проверка в репозитории + тест).
3. `usage_counters` инкрементируется в той же транзакции, что и `llm_calls`
   (согласованность биллинга, AC-BILL-5).
4. Embeddings всегда фильтруются по `channel_id` до векторного поиска (изоляция,
   REQ-WS-011).
