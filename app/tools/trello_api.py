import httpx

from app.tools.base import BaseTool, ToolResult

_BASE = "https://api.trello.com/1"


class TrelloTool(BaseTool):
    name = "trello"
    description = "Manage Trello boards: list cards, create/update cards, move cards."

    def __init__(self, api_key: str, token: str) -> None:
        self._auth = {"key": api_key, "token": token}

    async def run(self, action: str, **kwargs) -> ToolResult:
        async with httpx.AsyncClient(timeout=20) as client:
            if action == "list_cards":
                board_id = kwargs["board_id"]
                resp = await client.get(f"{_BASE}/boards/{board_id}/cards", params=self._auth)
                resp.raise_for_status()
                cards = resp.json()
                summary = "\n".join(f"- {c['name']} [{c['idList']}]" for c in cards[:20])
                return ToolResult(ok=True, data=summary, raw={"cards": cards})

            if action == "create_card":
                payload = {**self._auth, "name": kwargs["name"], "idList": kwargs["list_id"]}
                if desc := kwargs.get("desc"):
                    payload["desc"] = desc
                resp = await client.post(f"{_BASE}/cards", params=payload)
                resp.raise_for_status()
                card = resp.json()
                return ToolResult(ok=True, data=f"Created card: {card['name']} ({card['id']})", raw=card)

            return ToolResult(ok=False, data=f"Unknown action: {action}")
