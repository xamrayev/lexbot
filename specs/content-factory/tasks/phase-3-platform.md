# Tasks — Phase 3: Platform (ContentOS)

**Цель:** экосистема: Marketplace, Plugin SDK, Copilot, видео, enterprise,
выделение микросервисов.

---

## Marketplace

- [ ] T3.01 Каталог артефактов: стили, workflow, шаблоны, промпты, конфигурации агентов, наборы источников, инструкции, плагины — REQ-EXT-020
- [ ] T3.02 Скан на PII/секреты + модерация платных артефактов — REQ-EXT-021 · AC-EXT-5
- [ ] T3.03 Транзакционная установка/обратимое удаление артефакта — REQ-EXT-022
- [ ] T3.04 Выплаты авторам (revenue share, отчёты) — REQ-EXT-023
- [ ] T3.05 Экспорт Style Profile/Workflow владельцем — REQ-STYLE-027, REQ-PIPE-042

## Plugin SDK

- [ ] T3.10 Контракты protobuf: SourceConnector, Provider, Publisher, WorkflowBlock — REQ-EXT-030
- [ ] T3.11 Изолированное исполнение (go-plugin/gRPC, ресурсные лимиты, изоляция сбоев) — REQ-EXT-031 · AC-EXT-4
- [ ] T3.12 Манифест разрешений + подтверждение администратором — REQ-EXT-032
- [ ] T3.13 Референсный плагин (Hacker News source) + доккит для разработчиков — AC-EXT-4

## Продукт

- [ ] T3.20 AI Copilot в редакторе: заголовки, вступления, CTA, картинки, SEO, FAQ (streaming, явное применение) — REQ-AGENT-030..031
- [ ] T3.21 Видео-производные: статья → сценарий → Shorts/TikTok/Reels/YouTube (рендер через плагины) — REQ-EXT-041
- [ ] T3.22 Publisher-адаптеры соцсетей (Twitter/X, LinkedIn, …) — REQ-PUB-030
- [ ] T3.23 Zapier/n8n/Make интеграции поверх API+webhooks — REQ-EXT-012

## Enterprise & масштабирование

- [ ] T3.30 Enterprise-тариф: кастомные модели/лимиты per-workspace, SSO — REQ-BILL-002
- [ ] T3.31 Выделение AI Service (llm) в отдельный сервис (gRPC) — DES-ARCH §9
- [ ] T3.32 Выделение Analytics (потребитель Event Bus) — DES-ARCH §9
- [ ] T3.33 Выделение Billing (PCI-изоляция) — DES-ARCH §9
- [ ] T3.34 SLA-мониторинг, статус-страница, инцидент-runbooks — DES-INFRA

## Definition of Done (Phase 3)

1. Внешний разработчик подключает источник-плагин без доступа к ядру.
2. Первый платный артефакт продан через Marketplace c выплатой автору.
3. AI Service масштабируется независимо от монолита.
