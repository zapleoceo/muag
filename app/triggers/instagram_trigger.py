"""Instagram trigger — polls new comments and DMs via Graph API."""
import logging

import httpx

from app.triggers.base import BaseTrigger, TriggerEvent

log = logging.getLogger(__name__)

_GRAPH = "https://graph.facebook.com/v19.0"


class InstagramTrigger(BaseTrigger):
    type = "instagram"

    def __init__(self, name: str, config: dict, agent_names: list[str]) -> None:
        self.name = name
        self._agent_names = agent_names
        self._access_token: str = config.get("access_token", "")
        self._ig_user_id: str = config.get("ig_user_id", "")
        self._seen_ids: set[str] = set()

    async def poll(self) -> list[TriggerEvent]:
        if not self._access_token or not self._ig_user_id:
            log.warning("InstagramTrigger '%s': access_token or ig_user_id missing", self.name)
            return []

        events: list[TriggerEvent] = []
        try:
            events += await self._poll_comments()
            events += await self._poll_messages()
        except Exception:
            log.exception("InstagramTrigger '%s' poll failed", self.name)
        return events

    async def _poll_comments(self) -> list[TriggerEvent]:
        url = f"{_GRAPH}/{self._ig_user_id}/media"
        params = {
            "fields": "id,caption,comments{id,text,username,timestamp}",
            "access_token": self._access_token,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        events: list[TriggerEvent] = []
        for media in data.get("data", []):
            for comment in media.get("comments", {}).get("data", []):
                cid = comment["id"]
                if cid in self._seen_ids:
                    continue
                self._seen_ids.add(cid)
                task_text = (
                    f"Новый комментарий в Instagram от @{comment.get('username', '?')}:\n"
                    f"\"{comment['text']}\"\n\n"
                    f"Публикация: {(media.get('caption') or '')[:100]}\n\n"
                    f"Составь естественный ответ от имени владельца."
                )
                events.append(TriggerEvent(
                    trigger_name=self.name,
                    trigger_type="instagram",
                    task_text=task_text,
                    raw_data={"type": "comment", "comment": comment, "media_id": media["id"]},
                    agent_names=self._agent_names,
                ))
                log.info("InstagramTrigger: new comment from @%s", comment.get("username"))
        return events

    async def _poll_messages(self) -> list[TriggerEvent]:
        # Instagram DMs via Messenger API
        url = f"{_GRAPH}/{self._ig_user_id}/conversations"
        params = {
            "fields": "messages{id,message,from,created_time}",
            "access_token": self._access_token,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 400:
                # DM access requires special permissions — skip silently
                return []
            resp.raise_for_status()
            data = resp.json()

        events: list[TriggerEvent] = []
        for conv in data.get("data", []):
            for msg in conv.get("messages", {}).get("data", []):
                mid = msg["id"]
                if mid in self._seen_ids:
                    continue
                # Skip messages sent by us
                sender = msg.get("from", {})
                if str(sender.get("id")) == str(self._ig_user_id):
                    self._seen_ids.add(mid)
                    continue
                self._seen_ids.add(mid)
                task_text = (
                    f"Новое DM в Instagram от {sender.get('name', '?')}:\n"
                    f"\"{msg.get('message', '')}\"\n\n"
                    f"Составь естественный ответ от имени владельца."
                )
                events.append(TriggerEvent(
                    trigger_name=self.name,
                    trigger_type="instagram",
                    task_text=task_text,
                    raw_data={"type": "dm", "message": msg},
                    agent_names=self._agent_names,
                ))
                log.info("InstagramTrigger: new DM from %s", sender.get("name"))
        return events
