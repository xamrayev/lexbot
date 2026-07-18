# 11 — Requirements: API, Webhooks, Marketplace, Plugin SDK, Media

**Модуль:** `EXT` · **Статус:** Draft · **Зависит от:** все · **Design:** `../design/architecture.md`

---

## User Stories

- **US-EXT-1**: Как интегратор, я хочу полный API и webhooks, чтобы встроить ContentOS
  в свои процессы (Slack, CRM, Zapier, n8n, Make).
- **US-EXT-2**: Как автор стилей/промптов, я хочу продавать их в Marketplace.
- **US-EXT-3**: Как разработчик, я хочу Plugin SDK, чтобы добавлять новые источники
  и AI-провайдеров без изменения ядра.

## Functional Requirements (EARS)

### Public API

- **REQ-EXT-001**: THE SYSTEM SHALL предоставлять REST API, покрывающий все функции
  продукта (паритет с UI): каналы, источники, материалы, запуски пайплайна,
  календарь, аналитика, память.
- **REQ-EXT-002**: API SHALL аутентифицироваться API-ключами со скоупами
  (read/write per-domain) и rate limits per-key согласно тарифу.
- **REQ-EXT-003**: API SHALL версионироваться (`/v1/...`); breaking changes — только
  в новой мажорной версии.
- **REQ-EXT-004**: THE SYSTEM SHALL публиковать OpenAPI-спецификацию, генерируемую
  из кода, как артефакт CI.

### Webhooks

- **REQ-EXT-010**: THE SYSTEM SHALL отправлять webhooks на настроенные endpoint'ы
  для событий: `article.generated`, `post.published`, `post.failed`,
  `approval.requested`, `quota.warning`, `source.degraded` (маппинг из Event Bus).
- **REQ-EXT-011**: Webhooks SHALL подписываться HMAC-подписью; доставка — с ретраями
  (экспоненциальный backoff, до 24 ч) и DLQ с ручным повторением.
- **REQ-EXT-012**: THE SYSTEM SHALL предоставлять готовые интеграции-рецепты:
  Slack, Discord, Telegram-уведомления, Email; Zapier/n8n/Make — через webhooks + API.

### Marketplace (Phase 3)

- **REQ-EXT-020**: THE SYSTEM SHALL позволять публиковать и продавать артефакты:
  стили (Style Profile), workflow (DAG), шаблоны, промпты, конфигурации агентов,
  наборы источников, инструкции, плагины.
- **REQ-EXT-021**: WHEN артефакт публикуется, THE SYSTEM SHALL проверить его на
  отсутствие персональных данных и секретов (автоматический скан + ручная модерация
  для платных).
- **REQ-EXT-022**: Установка артефакта SHALL быть транзакционной: полностью
  применяется к каналу или не применяется вовсе; удаление — обратимо.
- **REQ-EXT-023**: THE SYSTEM SHALL вести выплаты авторам (revenue share, отчёты).

### Plugin SDK

- **REQ-EXT-030**: THE SYSTEM SHALL определять стабильные интерфейсы расширений:
  `SourceConnector` (новые источники), `Provider` (новые LLM-провайдеры),
  `Publisher` (новые платформы публикации), `WorkflowBlock` (новые блоки пайплайна).
- **REQ-EXT-031**: Плагины SHALL исполняться изолированно (отдельный процесс/
  контейнер с ограничениями ресурсов) и общаться с ядром по gRPC-контракту;
  сбой плагина не роняет ядро.
- **REQ-EXT-032**: Плагин SHALL декларировать манифест: имя, версия, требуемые
  разрешения (сеть, секреты, объём данных); разрешения подтверждает администратор.

### Изображения и видео (Phase 2–3)

- **REQ-EXT-040**: THE SYSTEM SHALL генерировать для материала: обложку, баннер,
  иллюстрации, инфографику, миниатюры — через Image-операцию Gateway; стиль
  изображений — из Brand Profile.
- **REQ-EXT-041**: THE SYSTEM SHALL создавать из статьи видео-производные
  (сценарий → Shorts/TikTok/Reels/YouTube-структура); рендеринг видео — через
  внешние сервисы-плагины.

## Acceptance Criteria

- [ ] AC-EXT-1: контрактный тест — каждая UI-операция MVP доступна через API v1. *(REQ-EXT-001)*
- [ ] AC-EXT-2: webhook с неверной HMAC-подписью отвергается получателем-эталоном; доставка ретраится и попадает в DLQ после 24 ч. *(REQ-EXT-011)*
- [ ] AC-EXT-3: API-ключ со скоупом read не может создать материал (403). *(REQ-EXT-002)*
- [ ] AC-EXT-4: демо-плагин SourceConnector (например, Hacker News) подключается без изменения ядра; его сбой не влияет на пайплайны. *(REQ-EXT-030..031)*
- [ ] AC-EXT-5: артефакт с API-ключом внутри блокируется при публикации в Marketplace. *(REQ-EXT-021)*
