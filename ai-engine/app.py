import streamlit as st
from fieldnode.engine import initial_farm, run_cycle

st.set_page_config(page_title="Fieldnode | Autonomous Farm OS", page_icon="🌱", layout="wide")
st.title("Fieldnode — Autonomous Farm OS")
st.caption("Autonomous control plane: observe → agents → A2A → policy → execute → reflect")

if "farm" not in st.session_state:
    st.session_state.farm = initial_farm()
if "history" not in st.session_state:
    st.session_state.history = []

farm = st.session_state.farm
c1,c2,c3,c4 = st.columns(4)
c1.metric("Autonomy", "ON")
c2.metric("Farm clock", f"Day {farm.day} · {farm.hour:02d}:00")
c3.metric("Cash", f"{farm.cash:.0f}")
c4.metric("Produce", farm.produce)

col1, col2 = st.columns([1, 2])
with col1:
    cycles = st.number_input("Autonomous cycles", min_value=1, max_value=25, value=1)
    if st.button("Run autonomous control loop", type="primary"):
        for _ in range(cycles):
            result = run_cycle(st.session_state.farm)
            st.session_state.farm = result["farm"]
            st.session_state.history.insert(0, result)
        st.rerun()

with col2:
    if st.session_state.history:
        r = st.session_state.history[0]
        d = r["decision"]
        st.subheader("Latest autonomous decision")
        st.write(f"**{d.action}** · {d.tile_id or 'farm-wide'} · confidence {d.confidence:.0%}")
        st.write(d.rationale)
        st.caption("Decision path: Observe → ML forecast → specialist agents → A2A resource check → policy → execution")
        st.metric("Predicted yield", r.get("prediction", 0))

st.subheader("Agent proposals")
if st.session_state.history:
    latest = st.session_state.history[0]
    st.dataframe(
        [{"agent": p.agent, "action": p.action, "tile": p.tile_id or "—",
          "priority": p.priority, "confidence": p.confidence, "rationale": p.rationale}
         for p in latest.get("proposals", [])],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Run the autonomous loop to generate real agent proposals and an execution trace.")

st.subheader("Farm digital twin")
st.dataframe([t.model_dump() for t in farm.tiles], use_container_width=True, hide_index=True)

st.subheader("A2A communication")
if st.session_state.history:
    st.json([m.model_dump() for m in st.session_state.history[0].get("messages", [])])
else:
    st.caption("No messages yet.")

st.subheader("Autonomous history")
if st.session_state.history:
    st.dataframe(
        [{"day": r["farm"].day, "hour": r["farm"].hour, "action": r["decision"].action,
          "tile": r["decision"].tile_id or "—", "confidence": r["decision"].confidence}
         for r in st.session_state.history[:10]],
        use_container_width=True,
        hide_index=True,
    )
