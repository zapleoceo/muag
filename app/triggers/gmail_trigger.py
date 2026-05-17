"""Gmail trigger — polls inbox for new unread emails, creates tasks."""
import logging
from datetime import datetime, timezone

from app.triggers.base import BaseTrigger, TriggerEvent

log = logging.getLogger(__name__)


class GmailTrigger(BaseTrigger):
    type = "gmail"

    def __init__(self, name: str, config: dict, agent_names: list[str]) -> None:
        self.name = name
        self._agent_names = agent_names
        self._creds_json: str = config.get("credentials_json", "")
        self._max_results: int = config.get("max_results", 5)
        self._seen_ids: set[str] = set()

    async def poll(self) -> list[TriggerEvent]:
        if not self._creds_json:
            log.warning("GmailTrigger '%s': no credentials_json in config", self.name)
            return []

        try:
            return await self._fetch_new_emails()
        except Exception:
            log.exception("GmailTrigger '%s' poll failed", self.name)
            return []

    async def _fetch_new_emails(self) -> list[TriggerEvent]:
        import asyncio
        import json

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        def _sync() -> list[dict]:
            creds_data = json.loads(self._creds_json)
            creds = Credentials(
                token=creds_data["token"],
                refresh_token=creds_data.get("refresh_token"),
                token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=creds_data.get("client_id"),
                client_secret=creds_data.get("client_secret"),
            )
            svc = build("gmail", "v1", credentials=creds)
            resp = svc.users().messages().list(
                userId="me",
                q="is:unread",
                maxResults=self._max_results,
            ).execute()
            messages = []
            for m in resp.get("messages", []):
                if m["id"] in self._seen_ids:
                    continue
                detail = svc.users().messages().get(
                    userId="me", id=m["id"], format="metadata"
                ).execute()
                headers = {
                    h["name"]: h["value"]
                    for h in detail.get("payload", {}).get("headers", [])
                }
                snippet = detail.get("snippet", "")
                messages.append({
                    "id": m["id"],
                    "from": headers.get("From", ""),
                    "subject": headers.get("Subject", "(no subject)"),
                    "snippet": snippet,
                })
            return messages

        emails = await asyncio.get_event_loop().run_in_executor(None, _sync)
        events: list[TriggerEvent] = []
        for email in emails:
            self._seen_ids.add(email["id"])
            task_text = (
                f"Новое письмо от {email['from']}.\n"
                f"Тема: {email['subject']}\n"
                f"Фрагмент: {email['snippet']}\n\n"
                f"Подготовь краткое резюме и предложи ответ."
            )
            events.append(TriggerEvent(
                trigger_name=self.name,
                trigger_type="gmail",
                task_text=task_text,
                raw_data=email,
                agent_names=self._agent_names,
            ))
            log.info("GmailTrigger: new email from %s — %s", email["from"], email["subject"])

        return events
