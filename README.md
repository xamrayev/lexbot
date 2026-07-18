# Enterprise LegalOS

Экосистема AI-решений для автоматизации юридических, кадровых, бухгалтерских и управленческих процессов организаций Республики Узбекистан.

| Продукт | Аудитория | Интерфейсы |
|---|---|---|
| **HR Assistant (Free / HR Pro)** | HR-специалисты | Web, Telegram Bot, MS Teams (план) |
| **Enterprise LegalOS** | Компании, банки, госорганизации, холдинги, университеты | Desktop Web, API |

## Быстрый старт

```bash
cd legalos
cp .env.example .env          # заполните ключ AI-провайдера
docker compose up -d
```

Подробности: [`legalos/README.md`](legalos/README.md) · Архитектура: [`docs/legalos/architecture.md`](docs/legalos/architecture.md)

## Структура репозитория

```
├── legalos/          # Платформа: FastAPI backend, Next.js frontend,
│                     # Telegram-бот, Docker Compose, Nginx
├── docs/legalos/     # Архитектурная документация
├── specs/            # Spec-Driven Development: спецификации новых продуктов
│   └── content-factory/  # Content Factory SaaS (ContentOS) — см. specs/content-factory/README.md
└── data/             # mehnat_kodeksi_processed.json — Трудовой кодекс РУз
                      # (датасет для наполнения базы знаний)
```

## Возможности платформы

- **AI Platform (Provider Pattern)** — OpenAI, DeepSeek, Gemini, Qwen, любой OpenAI-совместимый endpoint;
- **Enterprise RAG** — Hybrid Search: BM25 + pgvector + RRF + reranker, hook для Knowledge Graph;
- **7 агентов** — HR, Legal, Accounting, Procurement, CEO, Compliance, Tax;
- **Тарифы** — Free / HR Pro / Business / Enterprise / Government Edition;
- **Document Intelligence** — IBM Docling: PDF, DOCX, XLSX, HTML, OCR;
- **Legislative Intelligence** — мониторинг Lex.uz/Norma.uz, история редакций законов;
- **Безопасность** — Multi-Tenant, RBAC, JWT/OAuth2, Audit Log, защита от prompt injection.

---

**Автор:** NazarAI — UBS Namangan · **Лицензия:** MIT
