# Autonomous Farm OS — Sanity Context Agent

This is the actual Path One agent harness.

It follows Sanity's recommended Context integration pattern:
1. fetch initial context from the MCP endpoint,
2. connect through Streamable HTTP MCP,
3. expose Sanity tools to the OpenAI Agents SDK,
4. let the model query structured content,
5. return an evidence-backed recommendation.

Run from this directory after configuring .env.

    pip install -r requirements.txt
    python agent.py "Should I sell wheat now?"

The Sanity organization token is never sent to the browser.
