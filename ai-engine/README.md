# Fieldnode AI Engine

The AI control plane turns the original deterministic farmer-action loop into an autonomous multi-agent loop.

## Run

```bash
cd ai-engine
pip install -e .
streamlit run app.py
```

Optional LLM/TensorFlow providers can be added without changing the farm execution contract.

## Architecture

Observe → LangGraph StateGraph → specialist proposals → A2A messages → policy validation → execution → next state.

The MCP server exposes farm inspection/market tools. The simulator remains the execution adapter; agents never mutate authoritative state directly.
