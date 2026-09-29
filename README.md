# AgriNexus OS — Autonomous Multi-Agent Farm Intelligence

**The farm observes, reasons, arbitrates, acts, and reconciles — without a farmer clicking through every operation.**

AgriNexus OS is a Kaggriculture-native autonomous farm agent plus an observability control plane. The competition entry is the root `main.py`; the web/Streamlit experiences make the multi-agent decision loop visible.

## Autonomous operating loop

```
OBSERVE
   ↓
SPECIALIST AGENTS
   ├─ Crop
   ├─ Livestock
   ├─ Fertility
   ├─ Market
   ├─ Expansion
   └─ Workforce
   ↓
PROPOSALS / NEGOTIATION
   ↓
ARBITRATION
   ↓
GUARDRAILS
   ↓
EXECUTE
   ↓
RECONCILE
   └──────────────→ next observation
```

## Competition agent

`main.py` exposes:

```python
def agent(obs):
    ...
```

The policy is deterministic and competition-safe: no network calls, model downloads, external runtime files, or persistent state.

The agent manages the full operating surface: crop lifecycle, livestock production, animal fertilizer, bounded market trading, labor scaling, and land expansion.

## Why the UI is separate

The competition runner executes `agent(obs)` directly. The React and Streamlit applications are **observability twins**: they visualize agent proposals, arbitration, guardrails, farm state, market context, and reconciliation without becoming a dependency of the submitted agent.

The React control plane defaults to **Autopilot**. Human intervention is presented as an explicit override rather than the normal workflow.

## Run the visual control plane

### React/API

```bash
pnpm install
pnpm --filter @workspace/api-server run dev
```

Then run the web workspace using the repository's configured pnpm workflow.

### Streamlit twin

```bash
python -m streamlit run streamlit_app.py
```

## Validate the competition entry

```bash
python -m py_compile main.py
```

For the official Kaggriculture environment, install the current competition-compatible `kaggle-environments` release and run a 720-turn match locally before submission.

## Repository map

- `main.py` — competition-native autonomous agent
- `KAGGRICULTURE_SUBMISSION.md` — submission architecture and validation notes
- `artifacts/farm-operations/src/App.tsx` — autonomous React control plane
- `artifacts/farm-operations/src/index.css` — responsive visual system
- `artifacts/api-server/src/lib/farm-simulator.ts` — deterministic visual twin
- `streamlit_app.py` — lightweight autonomous observability twin
- `replit.md` — workspace/runbook notes

## Design principle

This project is intentionally **agent-first**:

> The UI does not make the farm autonomous.  
> The `agent(obs)` policy is autonomous.  
> The UI exists to make that autonomy inspectable.
