"""Setup office supergroup topics — one topic per agent.

Creates forum topics in the office group and saves home_topic_id to DB.

Run once:
  docker compose exec agents python -m scripts.setup_office
"""
import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx
from sqlalchemy import select

from app.config import get_settings
from app.db.database import AsyncSessionLocal
from app.db.models import Agent

log = logging.getLogger(__name__)

# Emoji icons per role
_ROLE_ICONS = {
    "knowledge": "📚",
    "action": "⚡",
    "process": "🔄",
}


async def create_topic(bot_token: str, chat_id: int, name: str, icon: str) -> int | None:
    url = f"https://api.telegram.org/bot{bot_token}/createForumTopic"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json={
            "chat_id": chat_id,
            "name": f"{icon} {name}",
        })
        data = resp.json()
        if data.get("ok"):
            topic_id = data["result"]["message_thread_id"]
            log.info("Created topic '%s' → thread_id=%d", name, topic_id)
            return topic_id
        else:
            log.error("Failed to create topic '%s': %s", name, data.get("description"))
            return None


async def setup() -> None:
    logging.basicConfig(level="INFO")
    settings = get_settings()

    if not settings.main_bot_token:
        print("❌ MAIN_BOT_TOKEN not set")
        return

    if not settings.office_group_id:
        print("❌ OFFICE_GROUP_ID not set")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Agent).where(Agent.is_active == True))
        agents = result.scalars().all()

        if not agents:
            print("❌ No active agents in DB. Run seed_agents.py first.")
            return

        for agent in agents:
            if agent.home_topic_id:
                print(f"  ✓ {agent.name} already has topic {agent.home_topic_id} — skip")
                continue

            icon = _ROLE_ICONS.get(agent.role, "🤖")
            topic_id = await create_topic(
                settings.main_bot_token,
                settings.office_group_id,
                agent.name,
                icon,
            )
            if topic_id:
                agent.home_topic_id = topic_id
                print(f"  + {agent.name} → topic {topic_id}")
            else:
                print(f"  ✗ {agent.name} — failed to create topic")

            await asyncio.sleep(0.3)  # avoid rate limit

        await session.commit()

    # Also create orchestrator result topic
    print("\nDone. Add OFFICE_GROUP_ID to .env if not already set.")
    print(f"Group ID: {settings.office_group_id}")


if __name__ == "__main__":
    asyncio.run(setup())
