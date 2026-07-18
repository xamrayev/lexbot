# План устранения техдолга и улучшений Enterprise LegalOS

> **Протокол работы с документом.** Этот файл — источник правды по ходу работ.
> При каждом продолжении: (1) прочитать документ, (2) взять первую часть со
> статусом ⬜ или 🔄, (3) пересоздать ветку `claude/enterprise-legalos-ecosystem-8b3yos`
> от свежего `origin/main`, (4) реализовать часть целиком, прогнать проверки,
> (5) обновить в этом файле статус части и чекбоксы пунктов, (6) закоммитить,
> запушить, открыть draft-PR. Одна часть = один PR.
>
> Статусы: ⬜ не начато · 🔄 в работе · ✅ завершено

| Часть | Тема | Статус |
|---|---|---|
| 1 | CI и тестовый фундамент | ✅ (PR #6) |
| 2 | Legislative Intelligence: парсинг Lex.uz и планировщик | ✅ (PR #7) |
| 3 | Качество RAG: чанкинг, reranker, оценка | ✅ (PR #7) |
| 4 | Безопасность: Redis-лимиты, токены, prompt-injection, шифрование/бэкапы | ⬜ |
| 5 | Надёжность и наблюдаемость: worker, метрики, логи | ⬜ |
| 6 | UX и мелочи: история чата, сессии бота, i18n, пагинация | ⬜ |

---

## Часть 1 — CI и тестовый фундамент

**Зачем:** ни одной автоматической проверки в репозитории нет; всё последующее
опасно менять без страховки.

- [x] **CI (GitHub Actions)** — `.github/workflows/ci.yml`:
  джоб `backend` (Python 3.11, `pip install -r legalos/backend/requirements.txt pytest`,
  `pytest legalos/backend/tests/`), джоб `frontend` (Node 20, `npm ci`, `npm run build`
  в `legalos/frontend/`). Триггеры: push в `main`, все PR.
- [x] **API-тесты с БД** — `legalos/backend/tests/test_api_integration.py`:
  поднимать PostgreSQL+pgvector как service-container в CI
  (`pgvector/pgvector:pg16`); фикстура `app` с `create_all` на тестовой БД;
  через `httpx.ASGITransport` прогнать сценарий: регистрация → логин → `/auth/me`
  → лимиты Free (21-е сообщение → 429) → изоляция тенантов (документ одного
  тенанта не виден другому). Локально без БД тесты скипаются
  (`pytest.mark.skipif` по `LEGALOS_TEST_DATABASE_URL`).

**Проверка:** оба джоба зелёные на PR; интеграционные тесты проходят в CI.

---

## Часть 2 — Legislative Intelligence: парсинг Lex.uz и планировщик

**Зачем:** сейчас хэшируется сырой HTML (смена вёрстки = ложная «новая
редакция», в индекс попадает разметка), а мониторинг никто не запускает по
расписанию.

- [x] **Парсинг Lex.uz** — новый модуль `app/services/legislative/parser.py`:
  `extract_act_text(html) -> str` — вытащить чистый текст акта (BeautifulSoup;
  выкинуть script/style/nav, схлопнуть пробелы); `split_by_articles(text)` —
  разбор по статьям регекспом на `N-modda`/`Статья N` с фолбэком на
  `split_into_chunks`. Хэшировать очищенный текст, а не HTML
  (`monitor.check_act_for_changes`); чанки актов делать по-статейно с метой
  `article`. Зависимость: `beautifulsoup4` в requirements. Чистые функции —
  покрыть тестами на образце HTML (фикстура в `tests/fixtures/`).
- [x] **Планировщик мониторинга** — периодическая задача в worker
  (`app/workers/consumer.py`): asyncio-цикл `scheduler_loop()`, который раз в
  `LEGALOS_LEGISLATION_CHECK_INTERVAL_HOURS` (дефолт 24) выбирает все акты и
  публикует по сообщению в очередь `legalos.legislation`. Джиттер и лог
  каждого прогона. Настройка в `core/config.py` + `.env.example`.

**Проверка:** юнит-тесты парсера на фикстуре HTML (текст без тегов, статьи
выделены); тест «изменение вёрстки при том же тексте не создаёт ревизию»;
запуск worker локально показывает лог планировщика.

---

## Часть 3 — Качество RAG: чанкинг, reranker, оценка

**Зачем:** символьная резка ломает предложения и игнорирует структуру;
LLM-reranker дорог; качество поиска не измеряется.

- [x] **Структурный чанкинг** — в `app/services/documents/ingest.py`:
  `split_into_chunks` резать по границам абзацев (`\n\n`), затем предложений,
  с добивкой до `CHUNK_SIZE` и перекрытием на уровне последних предложений;
  Markdown-заголовки от Docling начинают новый чанк и попадают в мету
  (`section`). Инварианты старых тестов сохранить (покрытие всего текста,
  максимум длины).
- [x] **Cross-encoder reranker** — `app/services/rag/rerankers.py`: третий режим
  `LEGALOS_RAG_RERANKER=cross_encoder` — ленивый `sentence-transformers`
  CrossEncoder (`BAAI/bge-reranker-v2-m3` или конфигурируемый
  `LEGALOS_CROSS_ENCODER_MODEL`), опциональная зависимость (закомментирована в
  requirements как docling/neo4j); при недоступности — фолбэк на порядок
  fusion с warning-логом. Вынести текущий LLM-reranker туда же, `pipeline.py`
  выбирает стратегию по настройке.
- [x] **Оценка качества** — `app/scripts/rag_eval.py` + датасет
  `data/rag_eval_labor_code.jsonl` (~30 пар «вопрос → номер статьи ТК», из
  тестовых вопросов README и типовых кадровых кейсов): скрипт гоняет
  `retrieve()` против засеянной базы, считает hit@k / MRR по мете `article`,
  печатает таблицу. Запуск руками: `python -m app.scripts.rag_eval`.

**Проверка:** тесты чанкера (не рвёт предложения посередине, заголовок в мете);
`rag_eval` отрабатывает на локальной БД с засеянным ТК (BM25-only без ключей).

---

## Часть 4 — Безопасность

**Зачем:** лимиты в PostgreSQL — лишние транзакции и гонки; refresh-токен
нельзя отозвать; prompt-injection только на регекспах; шифрование и бэкапы
заявлены в спеке, но не настроены.

- [ ] **Rate limiting и счётчики в Redis** — `app/services/billing/limiter.py`:
  дневные счётчики `INCR` + `EXPIRE` до конца суток (ключ
  `usage:{tenant}:{user}:{day}:{metric}`), sliding-window лимит запросов по
  IP на `/auth/*` (защита от брутфорса, 429). `check_and_increment`
  переключить на Redis с фолбэком на текущую PG-реализацию, если Redis
  недоступен. UsageCounter в PG оставить как асинхронную статистику (writeback
  из worker или на каждое N-е обращение).
- [ ] **Ротация refresh-токенов и отзыв** — в `core/security.py` добавить `jti`
  в refresh; `/auth/refresh` помечает старый `jti` в Redis-denylist
  (`SETEX` на остаток TTL) и выдаёт новую пару; повторное использование
  отозванного refresh → 401 всем сессиям пользователя (детект кражи).
  Endpoint `POST /auth/logout` — отзыв текущего refresh.
- [ ] **Prompt-injection: второй эшелон** — `services/security/guard.py`:
  опциональный LLM-judge (`LEGALOS_GUARD_LLM=true`) для входов, зацепивших
  «мягкие» паттерны; экранировать содержимое `<retrieved_documents>` от
  ложных закрывающих тегов; тесты на обход (unicode-гомоглифы, разрывы слов).
- [ ] **Шифрование и бэкапы** — сервис `backup` в docker-compose (`pg_dump` по
  cron в MinIO-бакет `legalos-backups`, ротация 14 дней); включить SSE-S3 в
  MinIO; том Nginx для TLS-сертификатов + пример конфига с `ssl_certificate`;
  раздел «Развёртывание в проде» в `docs/legalos/architecture.md` (что уже
  автоматизировано, что остаётся на стороне инфраструктуры).

**Проверка:** тесты лимитера (fakeredis), тест ротации (повторный refresh со
старым токеном → 401), тесты обхода guard; `docker compose config` валиден;
бэкап-скрипт создаёт дамп локально.

---

## Часть 5 — Надёжность и наблюдаемость

**Зачем:** упавшее сообщение в очереди теряется навсегда; метрик и структурных
логов нет — прод вслепую.

- [ ] **Worker-надёжность** — в `app/workers/consumer.py`: очереди объявлять с
  dead-letter-exchange `legalos.dlx`; при исключении — `nack` с republish и
  счётчиком попыток в заголовке (`x-retry-count`, максимум 3, затем в DLQ
  `legalos.dead`); лог содержимого мёртвых сообщений; идемпотентность
  обработчиков (проверка статуса документа перед переиндексацией).
- [ ] **Наблюдаемость** — `prometheus-client`: `/metrics` (счётчики запросов по
  роуту/статусу, латентность-гистограмма через middleware, счётчики
  LLM-вызовов и токенов в `openai_compatible.py`, глубина очередей из
  worker); структурные JSON-логи (`core/logging.py`, включается
  `LEGALOS_LOG_JSON=true`) с `request_id` (middleware) и `tenant_id`;
  `X-Request-ID` в ответах. README: как подключить Prometheus/Grafana.

**Проверка:** тест retry-логики (обработчик падает дважды → сообщение в DLQ на
третьей попытке, с fake-каналом); `/metrics` отдаёт метрики после пары
запросов; логи в JSON с request_id.

---

## Часть 6 — UX и мелочи

**Зачем:** видимые пользователю недоделки.

- [ ] **Клик по истории в чате** — backend: `GET /chat/conversations/{id}/messages`
  (сообщения + sources, с проверкой владельца); frontend (`app/page.tsx`):
  при клике грузить сообщения в окно чата, подставлять agent диалога,
  показывать sources последнего ответа в правой панели.
- [ ] **Сессии Telegram-бота** — хранить привязку `chat_id → credentials` не в
  памяти: бот получает свой Redis (`LEGALOS_REDIS_URL` в env бота, ключи
  `tg:session:{chat_id}` с токеном и conversation_id); при рестарте контейнера
  пользователи не теряются; refresh платформенного токена по 401.
- [ ] **i18n (русский/узбекский)** — без тяжёлых библиотек: словарь
  `frontend/lib/i18n.ts` (`ru`/`uz` ключи для всех строк интерфейса), хук
  `useT()`, переключатель языка в сайдбаре/topnav, выбор в localStorage;
  перевести все страницы (login, workspace, documents, compliance).
- [ ] **Пагинация** — backend: параметры `limit/offset` (+ `X-Total-Count`) для
  `/chat/conversations`, `/documents`, `/compliance/notifications`,
  `/compliance/checks`, `/legislation/acts`; frontend: кнопка «Показать ещё»
  в соответствующих списках.

**Проверка:** интеграционный тест messages-endpoint (чужой диалог → 404);
`next build`; скриншоты Playwright: история открывает диалог, интерфейс на
узбекском, «Показать ещё» дозагружает.

---

## Вне этого плана (отдельные решения)

SAML, Microsoft Teams-бот, API-интеграции MyGov/Soliq, коннекторы ERP/CRM/HRM —
требуют внешних регистраций/ключей; берутся отдельно после согласования.
