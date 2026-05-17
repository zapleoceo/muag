# VERA — план разработки

> Каждый коммит обновляет этот файл: что сделано, как работает, что дальше.

---

## Статус

| Фаза | Название | Статус |
|------|----------|--------|
| 1 | MVP — бот + approval + триггер | ✅ Готово |
| 2 | Virtual Office — агенты в Telegram-топиках | ✅ Готово |
| 3 | Триггеры — Gmail, Instagram, Webhook | ✅ Готово |
| 4 | Агенты — заполнить все 9 | ✅ Готово (seed script) |
| 5 | Admin UI | ✅ Готово |
| 6 | Hardening — deploy pipeline, alerting | ✅ Готово (self-improve ⏳) |

---

## Фаза 1 — MVP

**Цель:** первая живая команда `/task` → агент отвечает в Telegram.

### 1.1 Главный бот (aiogram) ✅
- **Файлы:** `app/bot/handler.py`, `app/bot/router.py`
- **Что делает:** принимает `/task <текст>` от владельца, запускает оркестратор в фоне, отвечает результатом. `/status` — последние 5 задач. `/agents` — список активных агентов
- **Как работает:** aiogram polling запускается как `asyncio.Task` внутри lifespan FastAPI. `_is_owner()` фильтрует по `OWNER_TELEGRAM_ID`

### 1.2 Approval flow ✅
- **Файлы:** `app/bot/approval.py`
- **Что делает:** `ask_owner()` отправляет InlineKeyboard с кнопками ✅/❌. Callbacks `approve:{id}` / `reject:{id}` пишут `owner_approved` в DB. При reject — задача переходит в `failed`
- **Как вызывать:** `await ask_owner(bot, owner_id, task_id, preview_text)` из action-агента перед выполнением

### 1.3 Telegram trigger ✅
- **Файлы:** `app/triggers/telegram_trigger.py`
- **Что делает:** `getUpdates` polling, парсит `/vera <текст>` (весь оркестратор) и `@AgentName: <текст>` (конкретный агент). Фильтрует по `OFFICE_GROUP_ID`
- **Состояние:** хранит `_last_update_id` между тиками (instance живёт в `_instances` dict в manager)

### 1.4 Cron trigger (fix) ✅
- **Файлы:** `app/triggers/cron.py`
- **Что делает:** парсит `*/N`, `0 */H`, `0 H` паттерны → интервал в минутах. Проверяет `_last_fired` между тиками. Первый запуск — срабатывает сразу
- **Config в DB:** `{"cron_expr": "*/30 * * * *", "prompt": "Проверь продажи за сегодня"}`

### 1.5 Seed скрипт ✅
- **Файлы:** `scripts/seed_agents.py`
- **Что делает:** вставляет 9 агентов (Knowledge, Research, Content, Trello, Gmail, Poster, Instagram, Tech, Health) — все с промптами и инструментами. Пропускает уже существующих
- **Запуск:** `docker compose exec agents python -m scripts.seed_agents`

---

## Фаза 2 — Virtual Office

### 2.1 AgentRunner ✅
- **Файлы:** `app/agents/runner.py`
- **Что делает:** при старте загружает всех агентов с `bot_token` из DB, стартует отдельный `aiogram.Dispatcher` для каждого. Бот отвечает только в своём `home_topic_id`
- **Как работает:** каждый агент-бот — отдельный `asyncio.Task`. Словари `_bots` и `_tasks` хранят живые инстансы. `stop_agent_runners()` — graceful shutdown

### 2.2 Setup скрипт ✅
- **Файлы:** `scripts/setup_office.py`
- **Что делает:** вызывает `createForumTopic` для каждого агента в `OFFICE_GROUP_ID`, сохраняет `home_topic_id` в DB. Пропускает уже настроенных
- **Запуск:** `docker compose exec agents python -m scripts.setup_office`
- **Требует:** forum (topics) включены в supergroup, бот — администратор группы

### 2.3 Inter-bot протокол ✅
- **Файлы:** `app/agents/telegram_agent.py`, обновлён `app/agents/registry.py`
- **Что делает:** оркестратор постит задачу через main bot в топик агента → агент-бот отвечает reply → TelegramAgent.`_wait_for_reply()` читает getUpdates агентского бота 60 сек, возвращает текст ответа
- **Фоллбек:** если у агента нет `bot_token`/`home_topic_id` — используется LLMAgent (прямой вызов LLM)

---

## Фаза 3 — Триггеры

### 3.1 Gmail trigger ✅
- **Файлы:** `app/triggers/gmail_trigger.py`
- **Что делает:** опрашивает Gmail `is:unread`, фильтрует через `_seen_ids`, создаёт задачу для GmailAgent с темой + фрагментом письма
- **Credentials в DB:** `tool_credentials` type=`gmail`, `{"token":..., "refresh_token":..., "client_id":..., "client_secret":...}`
- **Config в AgentTrigger:** `{"credentials_json": "...", "max_results": 5}`

### 3.2 Instagram trigger ✅
- **Файлы:** `app/triggers/instagram_trigger.py`
- **Что делает:** опрашивает комментарии к постам и DM через Graph API v19.0. `_seen_ids` предотвращает дубли. DM — только если есть разрешение `instagram_manage_messages`
- **Config в AgentTrigger:** `{"access_token": "...", "ig_user_id": "..."}`

### 3.3 Webhook trigger ✅
- **Файлы:** `app/api/webhook.py`
- **Что делает:** `POST /webhook/{name}` ищет `AgentTrigger` с `type=webhook`, создаёт `AgentTask`. Поддерживает `task_template` в config для форматирования тела запроса
- **Пример:** Zapier делает POST → VERA получает задачу → нужные агенты отрабатывают

---

## Фаза 4 — Агенты

| Агент | Роль | Инструменты | Статус |
|-------|------|-------------|--------|
| ResearchAgent | Поиск в интернете | Perplexity | ⏳ |
| KnowledgeAgent | Поиск в переписках | muai RAG | ⏳ |
| TrelloAgent | Управление задачами | Trello | ⏳ |
| GmailAgent | Письма | Gmail | ⏳ |
| PosterAgent | Продажи | Poster POS | ⏳ |
| InstagramAgent | Соцсети | Instagram API | ⏳ |
| ContentAgent | Тексты / посты | LLM only | ⏳ |
| HealthAgent | Здоровье | cron + Telegram | ⏳ |
| TechAgent | Код / документация | Perplexity + RAG | ⏳ |

---

## Фаза 5 — Admin UI

- Single-page `static/index.html`, vanilla JS, без фреймворков ✅
- **Разделы:**
  - **Задачи** — таблица с badge-статусами, раскрываемые agent_calls
  - **▶ Запустить** — textarea + кнопка → `POST /api/tasks/`
  - **Агенты** — таблица + форма создания/редактирования/удаления
  - **Credentials** — таблица + форма с шаблонами JSON по типу (perplexity/trello/gmail/instagram/poster/openai)
  - **Триггеры** — read-only список
- **API:** `GET /api/triggers/` добавлен (`app/api/triggers_api.py`)
- **Static:** `app/main.py` монтирует `/static`, `GET /` → `index.html`
- **Deps:** добавлен `aiofiles`, `google-api-python-client`, `google-auth-oauthlib`

---

## Фаза 6 — Hardening

### 6.1 GitHub Actions auto-deploy ✅
- **Файл:** `.github/workflows/deploy.yml`
- **Что делает:** на каждый push в `master` → SSH на сервер → `git pull` → `docker compose build` → `docker compose up -d`
- **⚠️ Нужно добавить вручную** на https://github.com/zapleoceo/muag/settings/secrets/actions:
  - `SERVER_HOST` = `195.201.31.49`
  - `SERVER_PORT` = `9617`
  - `SERVER_SSH_KEY` = содержимое файла `D:\Projects\hetzner\hetzner_195.201.31.49_ed25519`

### 6.2 Error alerting ✅
- **Файл:** `app/services/alerting.py`
- **Что делает:** `AlertingHandler` — logging handler уровня ERROR, отправляет сообщение в Telegram владельцу. Cooldown 5 мин на одинаковые ошибки. Трейсбек обрезается до 800 символов
- **Подключён** в `main.py` lifespan

### 6.3 Task concurrency limit ✅
- **Файл:** `app/services/limiter.py`
- **Что делает:** `asyncio.Semaphore(3)` — не более 3 задач одновременно. `tasks_api.py` оборачивает каждый запуск через `run_with_limit()`

### 6.5 LLM — shared key pool ✅
- **Файлы:** `app/llm/http_provider.py`, `app/llm/factory.py`
- **Что делает:** VERA использует ключи myAI через `POST /api/internal/llm/complete`. Нет дублирования — Gemini/Deepseek/OpenAI ключи только в myAI DB. Авторизация — `MUAI_API_SECRET` == `API_SECRET_KEY`
- **Приоритет fallback:** Gemini local key → OpenAI local key → myAI HTTP proxy → Stub

### 6.4 Self-improvement loop
- **Статус:** ⏳ Следующий этап
- **Идея:** агент сохраняет удачные примеры (score > 0.8) в отдельную таблицу, раз в N запусков LLM анализирует паттерны и предлагает улучшение system_prompt

---

## Лог коммитов

| Коммит | Что сделано |
|--------|-------------|
| `7d71278` | Initial scaffold: orchestrator, tools, triggers, API, DB models |
| `0c04e3a` | Fix: tgbot_tgbot network name in docker-compose |
| `9773c20` | Phase 1 MVP: aiogram bot handler (/task /status /agents), approval flow с кнопками, Telegram trigger (polling getUpdates), cron trigger fix (interval parsing), seed script для 9 агентов |
| `09fbea1` | Phase 2 Virtual Office: AgentRunner (один polling task на бота), setup_office.py (createForumTopic), TelegramAgent (inter-bot протокол через топики), registry обновлён — автовыбор LLM vs Telegram агента |
| `5165db4` | Phase 3 Triggers: Gmail (unread poll + seen_ids), Instagram (comments + DMs via Graph API), Webhook (POST /webhook/{name} + task_template) |
| `8010099` | Phase 5 Admin UI: full SPA (Tasks/Run/Agents/Credentials/Triggers), triggers_api.py, static mount + GET /, aiofiles+google deps |
| `eca5b2d` | Phase 6 Hardening: GitHub Actions SSH deploy, AlertingHandler (ERROR→Telegram, 5min cooldown), task concurrency Semaphore(3) |
| `a6482a7` | Debug: outer_middleware для диагностики маршрутизации обновлений |
| `a1cfbd3` | Fix(CI): заменить appleboy/ssh-action на native ssh — ssh-keyscan теперь non-fatal |
| `38fe1a9` | Debug: print stderr в middleware и handler; добавлен edited_message handler |
| `1263126` | Fix(CI): ssh-keyscan || true, исправлен printf без \n |
| `096c854` | Feat: OpenAI provider fallback когда Gemini key исчерпан |
| `900003e` | Feat: HttpLLMProvider — VERA использует ключи myAI через internal API (нет дублирования ключей) |
| `716bf78` | Fix: Depends() в LLM proxy endpoint myAI |
| `текущий` | Cleanup: удалён debug код, исправлен synthesize guard (пустые результаты), PLAN.md обновлён |

---

## Архитектура (текущая)

```
Telegram /task
    ↓
app/bot/handler.py  (aiogram)
    ↓
app/agents/orchestrator.py
    ├─ plan()  →  выбрать агентов
    ├─ run()   →  параллельный запуск с инструментами
    ├─ reflect() → оценить качество (0.0–1.0), retry если низко
    └─ synthesize() → финальный ответ
    ↓
app/bot/approval.py  (если action-агент)
    ↓
Telegram → владельцу
```

```
Внешние события
    ↓
app/triggers/manager.py  (polling loop 60s)
    ├─ gmail_trigger.py
    ├─ instagram_trigger.py
    ├─ cron.py
    └─ telegram_trigger.py
    ↓
AgentTask (queued) → Orchestrator
```
