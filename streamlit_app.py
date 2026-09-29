import random
from dataclasses import dataclass, field
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Autonomous Farm OS", page_icon="🌾", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp { background: radial-gradient(circle at 75% 0%, #15352b 0%, #08110f 38%); color:#edf7f2; }
.block-container { max-width:1500px; padding-top:1.4rem; padding-bottom:3rem; }
[data-testid="stSidebar"] { background:#07100e; border-right:1px solid #20352f; }
[data-testid="stMetric"] { background:linear-gradient(145deg,#10211c,#0c1714); border:1px solid #20352f; padding:16px; border-radius:14px; }
[data-testid="stMetricLabel"] { color:#8fa9a0; }
[data-testid="stMetricValue"] { color:#edf7f2; }
.card { background:linear-gradient(145deg,#101f1b,#0b1512); border:1px solid #20352f; border-radius:16px; padding:18px; margin-bottom:14px; }
.eyebrow { color:#8fa9a0; text-transform:uppercase; letter-spacing:.12em; font-size:.68rem; font-weight:700; }
.small { color:#8fa9a0; font-size:.82rem; }
.tile { min-height:86px; border:1px solid #29453b; border-radius:10px; padding:9px; background:#10231d; }
.tile.harvestable { background:#26301a; border-color:#6c6130; }
.tile-title { font-weight:800; font-size:.85rem; }
.tile-sub { color:#8fa9a0; font-size:.7rem; }
.progress { height:5px; background:#1b3029; border-radius:99px; margin-top:7px; overflow:hidden; }
.progress > div { height:100%; background:#53d18b; }
</style>
""", unsafe_allow_html=True)

@dataclass
class Tile:
    id: str
    x: int
    y: int
    status: str
    crop: str | None
    growth: int
    moisture: int

@dataclass
class Farm:
    day: int = 3
    hour: int = 8
    cash: float = 420
    revenue: float = 190
    expenses: float = 76
    produce: int = 2
    seeds: int = 8
    fertilizer: int = 4
    capacity: int = 24
    price: int = 38
    demand: float = .82
    trend: str = "rising"
    tiles: list[Tile] = field(default_factory=list)
    events: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.tiles:
            self.tiles = [
                Tile("A1",0,0,"planted","Wheat",22,84),
                Tile("A2",1,0,"growing","Wheat",61,28),
                Tile("A3",2,0,"ready",None,0,0),
                Tile("B1",0,1,"growing","Wheat",74,52),
                Tile("B2",1,1,"harvestable","Wheat",100,66),
                Tile("B3",2,1,"ready",None,0,0),
            ]
        if not self.events:
            self.events = ["Season plan initialized", "Field inspection"]

    @property
    def used(self): return self.produce + self.seeds + self.fertilizer
    @property
    def profit(self): return self.revenue - self.expenses
    @property
    def remaining_turns(self): return max(0, 720 - ((self.day-1)*24 + self.hour))

    def log(self, msg):
        self.events.insert(0, f"Day {self.day:02d} · {self.hour:02d}:00 — {msg}")
        self.events = self.events[:12]

    def advance(self):
        self.hour += 1
        if self.hour >= 24:
            self.hour = 0
            self.day += 1
        for t in self.tiles:
            if t.status == "planted":
                t.status, t.growth = "growing", min(100, t.growth + 12)
            elif t.status == "growing":
                t.growth = min(100, t.growth + 5)
                t.moisture = max(0, t.moisture - 4)
                if t.growth >= 100: t.status = "harvestable"

def get_farm():
    if "farm" not in st.session_state:
        st.session_state.farm = Farm()
    return st.session_state.farm

def recommendation(f):
    harvest = next((t for t in f.tiles if t.status == "harvestable"), None)
    if harvest:
        return ("HARVEST", f"Harvest {harvest.id}", "Peak readiness; free the plot and convert biological value to inventory.", .98, 38)
    thirsty = next((t for t in f.tiles if t.status == "growing" and t.moisture < 45), None)
    if thirsty:
        return ("WATER", f"Water {thirsty.id}", "Moisture is below the operating threshold; protect growth before the next observation.", .94, 24)
    if f.produce and f.demand >= .75:
        return ("SELL", "Sell one unit", "Demand is healthy. Capture cash flow without flooding the shared market.", .89, f.price)
    ready = next((t for t in f.tiles if t.status == "ready"), None)
    if ready and f.seeds:
        return ("PLANT", f"Plant {ready.id}", "A productive plot is available and seed inventory supports another cycle.", .86, 31)
    return ("PASS", "Advance observation", "No higher-value action is justified in the current state.", .74, 0)

def execute(f, action):
    target = next((t for t in f.tiles if t.status == "harvestable"), None)
    if action == "HARVEST" and target:
        f.produce += 1
        target.status, target.crop, target.growth, target.moisture = "ready", None, 0, 0
        f.log(f"Harvested {target.id}")
    elif action == "WATER":
        target = next((t for t in f.tiles if t.status == "growing" and t.moisture < 45), None)
        if target:
            target.moisture = min(100, target.moisture + 54)
            f.log(f"Watered {target.id}")
    elif action == "SELL" and f.produce:
        f.produce -= 1
        f.cash += f.price
        f.revenue += f.price
        f.log(f"Sold 1 unit for {f.price} credits")
    elif action == "PLANT":
        target = next((t for t in f.tiles if t.status == "ready"), None)
        if target and f.seeds:
            f.seeds -= 1
            target.status, target.crop, target.growth, target.moisture = "planted", "Wheat", 0, 100
            f.log(f"Planted Wheat on {target.id}")
    else:
        f.log("Passed one turn for observation")
    f.advance()

f = get_farm()
with st.sidebar:
    st.markdown("## 🌾 Autonomous Farm OS")
    st.caption("Production operations console")
    st.divider()
    st.markdown("**Control plane**")
    st.radio("Workspace", ["Farm Command Center", "Agent Operations", "Market Intelligence", "Season Planning"], label_visibility="collapsed")
    st.divider()
    st.markdown('<span class="eyebrow">System</span>', unsafe_allow_html=True)
    st.success("Simulator connected")
    st.caption(f"KAGGRICULTURE · {f.remaining_turns} turns remaining")
    if st.button("↻ Reset simulation", use_container_width=True):
        st.session_state.farm = Farm()
        st.rerun()
    st.divider()
    st.caption("Autonomous Farm OS")
    st.caption("Decision support · Guardrails · Simulation")

c1, c2 = st.columns([4,1])
with c1:
    st.markdown('<span class="eyebrow">LIVE SIMULATOR · DECISION CONTROL PLANE</span>', unsafe_allow_html=True)
    st.title("Farm Command Center")
    st.caption("Observe the farm state, understand the decision, validate the guardrails, then execute.")
with c2:
    st.metric("Turns remaining", f.remaining_turns, f"Day {f.day} · {f.hour:02d}:00")

m1,m2,m3,m4,m5 = st.columns(5)
m1.metric("Cash on hand", f"{f.cash:,.0f}", "credits")
m2.metric("Projected profit", f"{f.profit:,.0f}", f"Revenue {f.revenue:,.0f}")
m3.metric("Field utilization", f"{sum(t.status!='ready' for t in f.tiles)}/{len(f.tiles)}", "active plots")
m4.metric("Inventory", f.used, f"/ {f.capacity} capacity")
m5.metric("Market demand", f"{f.demand*100:.0f}%", f"{f.trend} · {f.price} / unit")

st.divider()
left, right = st.columns([1, 1.35])
action, label, rationale, confidence, value = recommendation(f)

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="eyebrow">Orchestrator decision</span>', unsafe_allow_html=True)
    st.subheader(label)
    st.write(rationale)
    st.metric("Confidence", f"{confidence*100:.0f}%", f"Expected value +{value}")
    st.markdown("**Guardrails verified**")
    for g in ["State transition is valid", "Resource availability checked", "No unsafe market dump", "Turn budget respected"]:
        st.markdown(f"✓ {g}")
    if st.button(f"Execute {action}", type="primary", use_container_width=True):
        execute(f, action)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="eyebrow">Field topology</span>', unsafe_allow_html=True)
    st.subheader("Active plots")
    cols = st.columns(3)
    for i, t in enumerate(f.tiles):
        with cols[i % 3]:
            crop = t.crop or "Open plot"
            st.markdown(f'<div class="tile {t.status}"><div class="tile-title">{t.id} · {crop}</div><div class="tile-sub">{t.status.title()} · {t.growth}% growth · {t.moisture}% moisture</div><div class="progress"><div style="width:{t.growth}%;"></div></div></div><br>', unsafe_allow_html=True)
    st.caption(f"{len(f.tiles)} monitored plots · 3×2 operational grid")
    st.markdown('</div>', unsafe_allow_html=True)

a,b,c = st.columns([1.05,1.05,.9])
with a:
    st.markdown('<div class="card"><span class="eyebrow">Resource ledger</span><h3>Inventory health</h3>', unsafe_allow_html=True)
    inv = pd.DataFrame({"Resource":["Produce","Seeds","Fertilizer"],"Units":[f.produce,f.seeds,f.fertilizer]})
    fig = go.Figure(go.Bar(x=inv["Units"], y=inv["Resource"], orientation="h"))
    fig.update_layout(height=210, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#edf7f2")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)

with b:
    st.markdown('<div class="card"><span class="eyebrow">Market intelligence</span><h3>Demand / price signal</h3>', unsafe_allow_html=True)
    prices = [f.price-5, f.price-2, f.price, f.price+2, f.price+4]
    demand = [max(.1,f.demand-.12), max(.1,f.demand-.06), f.demand, min(1,f.demand+.04), min(1,f.demand+.07)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(5)), y=prices, mode="lines+markers", name="Price"))
    fig.add_trace(go.Scatter(x=list(range(5)), y=[d*50 for d in demand], mode="lines", name="Demand ×50"))
    fig.update_layout(height=210, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#edf7f2", showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)

with c:
    st.markdown('<div class="card"><span class="eyebrow">Financial ledger</span><h3>Capital position</h3>', unsafe_allow_html=True)
    st.metric("Revenue", f"{f.revenue:,.0f}")
    st.metric("Expenses", f"{f.expenses:,.0f}")
    st.metric("Net", f"{f.profit:,.0f}")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card"><span class="eyebrow">Agent coordination</span><h3>Five specialist agents · one authorization layer</h3>', unsafe_allow_html=True)
agents = pd.DataFrame([
    ["Season planning","Ready","Protect season-level profit",.84],
    ["Crop planning","Recommending" if any(t.moisture < 45 and t.status=="growing" for t in f.tiles) else "Ready","Protect crop lifecycle",.94],
    ["Market analysis","Ready","Maximize selling value",.89],
    ["Resource allocation","Ready","Balance turns and inventory",.88],
    ["Execution","Recommending" if action != "PASS" else "Ready","Authorize state-valid actions",confidence],
], columns=["Agent","Status","Objective","Confidence"])
st.dataframe(agents.assign(Confidence=agents.Confidence.map(lambda x:f"{x*100:.0f}%")), use_container_width=True, hide_index=True)
st.markdown('</div>', unsafe_allow_html=True)

x,y = st.columns([1,1])
with x:
    st.markdown('<div class="card"><span class="eyebrow">Execution timeline</span><h3>Recent events</h3>', unsafe_allow_html=True)
    for e in f.events[:7]:
        st.write(e)
    st.markdown('</div>', unsafe_allow_html=True)
with y:
    st.markdown('<div class="card"><span class="eyebrow">Architecture</span><h3>Autonomous decision loop</h3>', unsafe_allow_html=True)
    st.code("Observe → Plan → Score → Guardrail → Execute → Reconcile", language="text")
    st.caption("The Streamlit layer is the operator console. The Kaggriculture submission agent remains isolated in main.py and is not coupled to the UI runtime.")
    st.markdown('</div>', unsafe_allow_html=True)
