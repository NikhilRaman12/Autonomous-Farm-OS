# Fieldnode Submission Architecture

The repository's original vertical slice is a TypeScript/Express simulator with a React operations console. Its decision logic was concentrated in the simulator and specialist "agent" output was largely rule-based.

This branch adds a real Python AI control plane under `ai-engine/`:

```
FarmState
  ↓
LangGraph StateGraph
  ↓
Observe + ML prediction
  ↓
Specialist agents
  ↓
A2A resource negotiation
  ↓
Orchestrator + policy validation
  ↓
Execution adapter
  ↓
Updated FarmState
  ↓
Next autonomous cycle
```

### What is real

- LangGraph controls the decision graph.
- LangChain provides an optional LLM reasoning layer; the system still runs without an API key.
- pandas + scikit-learn provide the prediction path.
- TensorFlow is an optional extension point for deep-learning workloads.
- MCP exposes farm inspection/market tools.
- A2A messages carry structured agent coordination.
- Pydantic provides typed state/proposal contracts.
- Policy validation prevents invalid actions before execution.
- Streamlit exposes an operational control center and autonomous multi-cycle run.
- The simulator remains an execution adapter, not the decision brain.

### Demo

```bash
cd ai-engine
pip install -e .
streamlit run app.py
```

Use **Run autonomous control loop** to let the system select and execute actions without selecting a farmer action manually.

### Design principle

LLMs reason about strategy and exceptions. Deterministic code handles state transitions, constraints and execution. This keeps the autonomous loop observable, reproducible and safe for a competition demo.
