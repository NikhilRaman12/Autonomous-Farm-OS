# Sanity Context Agent Architecture

## Decision contract

The farm simulator owns state and execution.

Sanity owns structured operating knowledge.

The AI agent owns reasoning and explanation.

| Layer | Responsibility | Can mutate state? |
|---|---|---:|
| Sanity Content Lake | policies, crop rules, protocols, market rules | No |
| AI decision agent | retrieve + reason + recommend | No |
| Farm execution service | validate + apply action | Yes |

## Why structured content changes the result

The agent can query exact fields such as:
- minimumDemandToSell
- moistureFloor
- harvestReadiness
- inventoryReservePercent
- protocol preconditions
- protocol safety guardrails
- crop-specific market rules

A generic RAG system could retrieve prose about farming. This model lets the agent reason over the farm's actual operating policy.

## Evaluation scenario

1. Start with wheat moisture floor = 40%.
2. Ask which plot should be watered.
3. The agent queries the crop profile and field protocol.
4. Lower the wheat moisture floor in Sanity to 30%.
5. Ask again and show that the reasoning changes.

Repeat with the market rule:
1. Set minimum demand to 75%.
2. Ask whether to sell.
3. Change the rule to 90%.
4. Ask again.
5. The agent must explain why the recommendation changed.

This is the proof that Sanity is part of the agent's decision boundary rather than a decorative CMS.

## Security

The Context endpoint uses an organization API token with Context Viewer permission. The token remains server-side. The MCP is read-only; state changes stay behind the farm application's deterministic validation layer.
