import httpx

from app.tools.base import BaseTool, ToolResult

_BASE = "https://joinposter.com/api"


class PosterTool(BaseTool):
    name = "poster_pos"
    description = "Query Poster POS: get sales stats, products, transactions."

    def __init__(self, token: str) -> None:
        self._token = token

    async def run(self, method: str, params: dict | None = None) -> ToolResult:
        url = f"{_BASE}/{method}"
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, params={"token": self._token, **(params or {})})
            resp.raise_for_status()
            data = resp.json()
            return ToolResult(ok=True, data=str(data.get("response", data)), raw=data)
