# Streamlit production UI

The primary demo UI is now a Streamlit operations console.

## Run locally

\`\`\`bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements-streamlit.txt
streamlit run streamlit_app.py
\`\`\`

Open the local URL printed by Streamlit, normally http://localhost:8501.

## What the UI demonstrates

- live farm command center
- autonomous orchestrator recommendation
- state-valid action execution
- 3×2 farm topology
- inventory and financial ledgers
- market demand/price signals
- five-agent coordination
- execution timeline
- simulation reset and turn progression

The Kaggriculture competition submission remains isolated in the root \`main.py\`; the Streamlit UI does not alter the competition contract.
