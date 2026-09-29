# Autonomous Farm OS — Sanity Studio

This Studio defines the structured knowledge model consumed by the Sanity Context MCP agent.

Document types:
- Farm Policy — farm-wide objectives and thresholds.
- Crop Profile — crop-specific lifecycle and agronomic rules.
- Field Protocol — action preconditions and safety guardrails.
- Market Rule — crop-specific selling/holding logic.

Deploy the schema before creating a Sanity Context MCP dataset endpoint:

    npx sanity schema deploy
    npx sanity deploy
