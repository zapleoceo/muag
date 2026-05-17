-- VERA: initial schema
-- Apply via:
-- docker compose exec -T db psql -U bot tgbot -f /app/migrations/001_agent_tables.sql

CREATE TABLE IF NOT EXISTS agents (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    role        TEXT NOT NULL,           -- knowledge | action | process
    bot_token   TEXT,
    bot_username TEXT,
    system_prompt TEXT NOT NULL,
    tools       JSONB DEFAULT '[]',      -- [{type, ...config}]
    kb_namespace TEXT,
    home_topic_id BIGINT,
    quality_min FLOAT DEFAULT 0.65,
    max_retries INT DEFAULT 2,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id              BIGSERIAL PRIMARY KEY,
    trigger_type    TEXT,               -- mention | gmail | instagram | cron | command | manual
    trigger_data    JSONB,
    task_text       TEXT NOT NULL,
    topic_chat_id   BIGINT,
    topic_thread_id BIGINT,
    status          TEXT DEFAULT 'queued',
    -- queued → planning → running → reflecting → done | failed
    plan            JSONB,
    agent_calls     JSONB DEFAULT '[]', -- [{agent, request, response, score, retries}]
    final_text      TEXT,
    owner_approved  BOOLEAN,
    created_at      TIMESTAMPTZ DEFAULT now(),
    finished_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS agent_triggers (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,      -- cron | webhook | instagram | gmail | telegram
    config          JSONB DEFAULT '{}', -- credentials, filters, cron_expr, prompt, ...
    agent_names     JSONB DEFAULT '[]', -- which agents to involve
    topic_thread_id BIGINT,
    is_active       BOOLEAN DEFAULT TRUE,
    last_fired_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tool_credentials (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,          -- poster | trello | gmail | instagram | perplexity | ...
    credentials JSONB NOT NULL,         -- {token, api_key, client_id, ...}
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT now()
);
