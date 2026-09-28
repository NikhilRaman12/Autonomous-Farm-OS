import streamlit as st
from fieldnode.engine import initial_farm, run_cycle

st.set_page_config(page_title="Fieldnode | Autonomous Farm OS", page_icon="🌱", layout="wide")
st.title("Fieldnode — Autonomous Farm OS")
st.caption("Observe → multi-agent reason → validate → execute → learn")

if "farm" not in st.session_state:
    st.session_state.farm = initial_farm()

farm = st.session_state.farm
c1,c2,c3,c4 = st.columns(4)
c1.metric("Autonomy", "ON")
c2.metric("Day", f"{farm.day} · {farm.hour:02d}:00")
c3.metric("Cash", f"{farm.cash:.0f}")
c4.metric("Yield forecast", "—")

if st.button("Run autonomous cycle", type="primary"):
    result = run_cycle(farm)
    st.session_state.farm = result["farm"]
    st.session_state.last = result
    st.rerun()

if "last" in st.session_state:
    r = st.session_state.last
    d = r["result"]["action"]
    st.subheader("Autonomous decision")
    st.write(f"**{d['action']}** · {d.get('tile_id') or 'farm-wide'}")
    st.write(d["rationale"])
    st.metric("Model forecast", r["result"]["prediction"])

st.subheader("Farm digital twin")
st.dataframe([t.model_dump() for t in farm.tiles], use_container_width=True)

st.subheader("Agent architecture")
st.info("Crop Health → Harvest → Market → Crop Planning → Resource Allocation → Orchestrator → Policy → Execution")
