import asyncio
import os
import sys
from urllib.parse import urlparse, urlunparse

import httpx
from dotenv import load_dotenv
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp, create_static_tool_filter

load_dotenv()

MCP_URL = os.environ["SANITY_CONTEXT_MCP_URL"]
SANITY_TOKEN = os.environ["SANITY_ORGANIZATION_TOKEN"]

SYSTEM = """
You are the Autonomous Farm OS decision agent.

Use Sanity Context MCP as the source of truth for farm policy, crop profiles,
field protocols, and market rules.

Grounding rules:
1. Inspect the available Sanity schema/content before making a recommendation.
2. Prefer exact structured fields over generic agricultural knowledge.
3. Never invent a crop threshold, market rule, inventory rule, or safety constraint.
4. If Sanity does not support a conclusion, say what evidence is missing.
5. Explain: observation -> Sanity evidence -> reasoning -> recommended action -> guardrails.
6. Include relevant Sanity document names/IDs or source paths in an Evidence section.
7. The agent recommends only; the application execution layer remains authoritative.
"""

async def main() -> None:
    question = " ".join(sys.argv[1:]).strip() or "Which plot should be watered next and why?"

    parsed = urlparse(MCP_URL)
    initial_context_url = urlunparse(
        parsed._replace(path=parsed.path.rstrip("/") + "/initial-context")
    )

    async with httpx.AsyncClient(timeout=30) as http:
        response = await http.get(
            initial_context_url,
            headers={"Authorization": f"Bearer {SANITY_TOKEN}"},
        )
        response.raise_for_status()
        initial_context = response.text

    async with MCPServerStreamableHttp(
        name="sanity-context",
        params={
            "url": MCP_URL,
            "headers": {"Authorization": f"Bearer {SANITY_TOKEN}"},
        },
        client_session_timeout_seconds=30,
        tool_filter=create_static_tool_filter(blocked_tool_names=["initial_context"]),
    ) as server:
        agent = Agent(
            name="Autonomous Farm Decision Agent",
            instructions=SYSTEM + "\n\n# Sanity Context initial context\n" + initial_context,
            mcp_servers=[server],
        )
        result = await Runner.run(agent, question)
        print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
