"""Tool that queries the muai RAG endpoint for knowledge-base search."""
import httpx

from app.config import get_settings
from app.tools.base import BaseTool, ToolResult


class MuaiRagTool(BaseTool):
    name = "muai_rag"
    description = "Search owner's Telegram message history and knowledge base."
    params = {"query": "search query string", "top_k": "number of results to return (default 5)"}

    async def run(self, query: str, top_k: int = 5) -> ToolResult:
        settings = get_settings()
        url = f"{settings.muai_api_url}/api/internal/rag/search"
        headers = {"Authorization": f"Bearer {settings.muai_api_secret}"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json={"query": query, "top_k": top_k}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            chunks = data.get("chunks", [])
            text = "\n\n".join(c.get("text", "") for c in chunks)
            return ToolResult(ok=True, data=text or "No results found.", raw=data)
