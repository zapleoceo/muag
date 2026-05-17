from sqlalchemy import BigInteger, Boolean, Column, Float, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"

    id = Column(BigInteger, autoincrement=True, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    role = Column(Text, nullable=False)          # knowledge | action | process
    bot_token = Column(Text)
    bot_username = Column(Text)
    system_prompt = Column(Text, nullable=False)
    tools = Column(JSONB, default=list)          # [{type, ...config}]
    kb_namespace = Column(Text)
    home_topic_id = Column(BigInteger)           # thread_id in office group
    quality_min = Column(Float, default=0.65)
    max_retries = Column(Integer, default=2)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(BigInteger, autoincrement=True, primary_key=True)
    trigger_type = Column(Text)                  # mention | gmail | instagram | cron | command
    trigger_data = Column(JSONB)
    task_text = Column(Text, nullable=False)
    topic_chat_id = Column(BigInteger)
    topic_thread_id = Column(BigInteger)
    status = Column(Text, default="queued")
    # queued → planning → running → reflecting → acting → done | failed
    plan = Column(JSONB)
    agent_calls = Column(JSONB, default=list)    # [{agent, request, response, score, retries}]
    final_text = Column(Text)
    owner_approved = Column(Boolean)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    finished_at = Column(TIMESTAMP(timezone=True))


class ToolCredential(Base):
    __tablename__ = "tool_credentials"

    id = Column(BigInteger, autoincrement=True, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)   # poster | trello | gmail | instagram | perplexity | ...
    credentials = Column(JSONB, nullable=False)  # {token, api_key, client_id, ...}
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class AgentTrigger(Base):
    __tablename__ = "agent_triggers"

    id = Column(BigInteger, autoincrement=True, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)          # instagram | gmail | cron | webhook | telegram
    config = Column(JSONB, default=dict)         # credentials, filters, cron_expr, ...
    agent_names = Column(JSONB, default=list)    # which agents to involve
    topic_thread_id = Column(BigInteger)
    is_active = Column(Boolean, default=True)
    last_fired_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
