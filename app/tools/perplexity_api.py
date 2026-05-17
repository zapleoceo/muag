import httpx

from app.tools.base import BaseTool, ToolResult

_BASE = "https://api.perplexity.ai"


class PerplexityTool(BaseTool):
    name = "web_search"
    description = "Search the web for current information using Perplexity AI."

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def run(self, query: str) -> ToolResult:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [{"role": "user", "content": query}],
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{_BASE}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return ToolResult(ok=True, data=text, raw=data)
