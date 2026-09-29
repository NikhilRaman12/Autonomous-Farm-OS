# AgriNexus OS

## Multi-Agent Autonomous Farm Intelligence

**Tagline:** Specialist agents. One farm. Continuous adaptation.

AgriNexus replaces the old "Farm Command Center" framing with a cooperative agent architecture designed around the actual Kaggriculture mechanics.

## Agent mesh

| Agent | Responsibility |
|---|---|
| Crop Agent | Plant, water, weed control, harvest and crop lifecycle protection |
| Crop Portfolio Agent | Select crop type from crop deficit, season time and market signal |
| Livestock Agent | Buy, build, place, feed, care for and harvest cows, sheep and geese |
| Fertility Agent | Collect daily animal fertilizer and allocate it to high-leverage crops |
| Market Agent | Meter sales, purchase seeds/animals, hire hands and maintain liquidity |
| Expansion Agent | Evaluate BUY_LAND using cash, utilization and workforce capacity |
| Workforce Agent | Estimate visible workload and scale hired hands |
| Arbitration Layer | Resolve conflicting proposals and authorize one coherent action set |

## Decision loop

OBSERVE → SPECIALIST PROPOSALS → ARBITRATE → GUARDRAILS → EXECUTE → RECONCILE

The environment remains the source of truth. Agents propose actions; the arbitration layer resolves conflicts; the next observation closes the loop.

## Farm capabilities

AgriNexus supports the complete game surface:

- Plant, water, fertilize, weed and harvest Wheat, Carrot, Tomato, Strawberry and Melon.
- Buy, feed, care for and harvest Goose (eggs), Cow (milk) and Sheep (wool).
- Collect fertilizer from surviving animals and use it on high-leverage crops.
- Purchase neighboring quadrants with BUY_LAND after liquidity and utilization gates are satisfied.
- Trade through bounded market batches so the shared dynamic market is not flooded.
- Hire farm hands and assign work by urgency plus Manhattan movement cost.
- Preserve feed reserves and end-of-season liquidity.

The official Kaggriculture mechanics define a 10×10 farm split into four quadrants, a 720-turn / 30-day season, animal fertilizer availability, dynamic shared market pricing, and a maximum of 10 market orders per turn.

## Runtime separation

- main.py is the dependency-free Kaggriculture submission entry point.
- streamlit_app.py is the AgriNexus visual simulation twin.
- The Streamlit layer is never required by the competition runtime.

This keeps the submission deterministic while giving reviewers a visible explanation of the multi-agent architecture.
