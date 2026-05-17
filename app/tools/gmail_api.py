"""Gmail tool — read recent emails and send replies."""
import base64
import json
import logging
from email.mime.text import MIMEText

from app.tools.base import BaseTool, ToolResult

log = logging.getLogger(__name__)


class GmailTool(BaseTool):
    name = "gmail"
    description = "Read recent Gmail messages and send email replies."

    def __init__(self, credentials_json: str) -> None:
        self._creds_json = credentials_json

    def _build_service(self):
        import asyncio

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds_data = json.loads(self._creds_json)
        creds = Credentials(
            token=creds_data["token"],
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
        )
        return build("gmail", "v1", credentials=creds)

    async def run(self, action: str, **kwargs) -> ToolResult:
        import asyncio

        def _sync():
            svc = self._build_service()
            if action == "list":
                max_results = kwargs.get("max_results", 10)
                resp = svc.users().messages().list(userId="me", maxResults=max_results).execute()
                msgs = resp.get("messages", [])
                summaries = []
                for m in msgs[:5]:
                    detail = svc.users().messages().get(userId="me", id=m["id"], format="metadata").execute()
                    headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
                    summaries.append(f"From: {headers.get('From')} | Subject: {headers.get('Subject')}")
                return ToolResult(ok=True, data="\n".join(summaries), raw={"messages": msgs})

            if action == "send":
                msg = MIMEText(kwargs["body"])
                msg["to"] = kwargs["to"]
                msg["subject"] = kwargs["subject"]
                raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
                svc.users().messages().send(userId="me", body={"raw": raw}).execute()
                return ToolResult(ok=True, data=f"Sent to {kwargs['to']}")

            return ToolResult(ok=False, data=f"Unknown action: {action}")

        try:
            return await asyncio.get_event_loop().run_in_executor(None, _sync)
        except Exception:
            log.exception("Gmail tool error")
            return ToolResult(ok=False, data="Gmail error — check logs")
