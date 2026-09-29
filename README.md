# Autonomous Farm OS — Sanity Context Agent

An autonomous farm operations system grounded in structured agricultural knowledge.

The simulator is packaged as a Sanity Context + AI agent experience: farm knowledge lives in Sanity, Sanity Context exposes that structured content through MCP, and the agent uses those tools to answer operational questions with traceable grounding.

## Why Sanity is essential

A generic chatbot can give farming advice. This system is designed so the agent must consult structured farm policy, crop profiles, field protocols, and market rules before recommending an action.

- cropProfile stores crop-specific lifecycle, moisture, yield, and harvest constraints.
- fieldProtocol stores operational rules and safety thresholds.
- marketRule stores selling/holding rules and risk limits.
- farmPolicy stores farm-wide objectives and guardrails.
- References connect operational knowledge instead of flattening everything into one prompt.

The agent is connected through Sanity Context MCP, not a custom keyword-search shim.

## Architecture

Sanity Studio
  -> structured farm schemas
  -> published Content Lake
  -> Sanity Context MCP
  -> OpenAI Agents SDK
  -> Farm Decision Agent
  -> retrieve structured facts
  -> reason over current simulator state
  -> apply guardrails
  -> recommendation + evidence
  -> Autonomous Farm OS console

## Repository areas

- artifacts/farm-operations/ — interactive operations console.
- artifacts/api-server/ — deterministic farm simulator and guarded action execution.
- studio/ — Sanity Studio schema and seed content.
- agent/ — Sanity Context MCP + OpenAI Agents SDK agent.
- docs/ — architecture and challenge submission notes.

## Run the existing simulator

    pnpm install
    pnpm run typecheck
    pnpm run build

## Configure Sanity

Create a Sanity project with a public production dataset or a private dataset with the required Context permissions.

The committed studio/ folder contains the challenge-specific schemas. Set SANITY_STUDIO_PROJECT_ID and SANITY_STUDIO_DATASET, then run:

    cd studio
    npx sanity schema deploy
    npx sanity deploy

Import the supplied structured farm content:

    npx sanity dataset import seed/farm-content.ndjson production

The Sanity Context MCP dataset source requires a deployed Studio schema.

## Configure Sanity Context

In the Sanity Dashboard:

1. Enable Sanity Context for the organization if required.
2. Create a Context MCP endpoint.
3. Add the dataset source: PROJECT_ID.production.
4. Scope it to the farm document types with a GROQ filter.
5. Create an organization API token with Context Viewer permission.
6. Copy the MCP endpoint URL.

Example filter:

    _type in ["farmPolicy", "cropProfile", "fieldProtocol", "marketRule"]

Keep the organization token server-side.

## Run the grounded agent

Python 3.10+:

    cd agent
    python -m venv .venv
    pip install -r requirements.txt
    cp .env.example .env

Set SANITY_CONTEXT_MCP_URL, SANITY_ORGANIZATION_TOKEN, and OPENAI_API_KEY, then:

    python agent.py "Which plot should be watered next and why?"

The agent retrieves Sanity schema/content first, then produces a decision with supporting Sanity evidence.

## Demo questions

- Which plot should be watered next and which crop rule supports that decision?
- Can I harvest this crop today if inventory capacity is only 20% free?
- Should the farm sell wheat now or hold it?
- What changes if the market trend turns from rising to falling?
- Which rule blocks planting a new crop?
- What evidence in the farm knowledge base justifies the recommendation?

The strongest demos show that the answer depends on structured content rather than generic agricultural knowledge.

## Safety model

The AI agent recommends. The simulator remains the execution authority.

No LLM response is allowed to mutate farm state directly. Actions pass through deterministic validation in farm-simulator.ts, including valid tile state, inventory availability, capacity, action compatibility, and quantity validation.

This separates reasoning from execution.

## Challenge submission

Target: DEV Sanity Challenge — Path One: Ship an Agent That Queries Real Content.

The submission requires a DEV post using #sanitychallenge plus a Sanity project ID or public dataset URL. The judging criteria include meaningful Sanity Context/structured-content use, technical implementation, Knowledge Bases, and usability.

Recommended demo:

1. Open Farm Command Center.
2. Show the structured Sanity schema.
3. Ask a question whose answer depends on crop/field/market rules.
4. Show MCP retrieval and the structured facts.
5. Change one Sanity document.
6. Ask the same question again and show that the recommendation changes.
7. Execute only after deterministic simulator validation.

The critical proof is: changing structured Sanity content changes the agent's operating policy.

Do not commit API keys, organization tokens, private credentials, or .env files.
