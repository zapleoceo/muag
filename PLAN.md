# VERA — план разработки

> Каждый коммит обновляет этот файл: что сделано, как работает, что дальше.

---

## Статус

| Фаза | Название | Статус |
|------|----------|--------|
| 1 | MVP — бот + approval + триггер | ✅ Готово |
| 2 | Virtual Office — агенты в Telegram-топиках | ✅ Готово |
| 3 | Триггеры — Gmail, Instagram, Webhook | 🔄 В работе |
| 4 | Агенты — заполнить все 9 | ⏳ Ожидание |
| 5 | Admin UI | ⏳ Ожидание |
| 6 | Hardening — deploy pipeline, alerting | ⏳ Ожидание |

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

### 3.1 Gmail trigger
- **Файлы:** `app/triggers/gmail_trigger.py`
- **Что делает:** каждые N минут проверяет inbox, новые письма → создаёт задачу GmailAgent
- **Статус:** ⏳

### 3.2 Instagram trigger
- **Файлы:** `app/triggers/instagram_trigger.py`
- **Что делает:** polling новых комментариев/DM через Instagram Graph API, передаёт InstagramAgent
- **Статус:** ⏳

### 3.3 Webhook trigger
- **Файлы:** `app/api/webhook.py`
- **Что делает:** `POST /webhook/{name}` → создаёт задачу для указанных агентов
- **Статус:** ⏳

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

- Single-page `static/index.html`, vanilla JS, без фреймворков
- Разделы: Агенты / Credentials / Задачи / Триггеры / Запустить вручную
- **Статус:** ⏳

---

## Фаза 6 — Hardening

- [ ] GitHub Actions auto-deploy (`git push` → сервер)
- [ ] Error alerting → Telegram владельцу
- [ ] Rate limiting на API
- [ ] Task queue concurrency limit
- [ ] Self-improvement: агент сохраняет примеры, обновляет system_prompt
- **Статус:** ⏳

---

## Лог коммитов

| Коммит | Что сделано |
|--------|-------------|
| `7d71278` | Initial scaffold: orchestrator, tools, triggers, API, DB models |
| `0c04e3a` | Fix: tgbot_tgbot network name in docker-compose |
| `9773c20` | Phase 1 MVP: aiogram bot handler (/task /status /agents), approval flow с кнопками, Telegram trigger (polling getUpdates), cron trigger fix (interval parsing), seed script для 9 агентов |
| `(phase-2)` | Phase 2 Virtual Office: AgentRunner (один polling task на бота), setup_office.py (createForumTopic), TelegramAgent (inter-bot протокол через топики), registry обновлён — автовыбор LLM vs Telegram агента |

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
