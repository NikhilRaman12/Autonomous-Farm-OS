import importlib
from dataclasses import dataclass, field
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# AgriNexus OS — Streamlit twin of the competition policy
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AgriNexus Autonomous Farm",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp {
    background:
      radial-gradient(circle at 78% -5%, rgba(53, 130, 99, .24), transparent 34%),
      radial-gradient(circle at 5% 40%, rgba(28, 80, 66, .16), transparent 30%),
      #07100e;
    color:#edf7f2;
}
.block-container { max-width:1540px; padding-top:1.2rem; padding-bottom:3rem; }
[data-testid="stSidebar"] { background:#06100d; border-right:1px solid #1d332c; }
[data-testid="stMetric"] {
    background:linear-gradient(145deg,#0d1d18,#0a1512);
    border:1px solid #1d3a30; padding:15px; border-radius:15px;
}
[data-testid="stMetricLabel"] { color:#8fa9a0; }
[data-testid="stMetricValue"] { color:#edf7f2; }
.card {
    background:linear-gradient(145deg,#0e1e19,#091512);
    border:1px solid #1d3a30; border-radius:17px;
    padding:20px; margin-bottom:15px;
}
.eyebrow {
    color:#76caa0; text-transform:uppercase; letter-spacing:.14em;
    font-size:.67rem; font-weight:800;
}
.muted { color:#8fa9a0; }
.agent {
    border:1px solid #24463a; border-radius:12px;
    padding:12px; background:#0b1a15; min-height:120px;
}
.agent-name { font-weight:800; color:#edf7f2; }
.agent-role { color:#8fa9a0; font-size:.74rem; margin-top:3px; }
.pill {
    display:inline-block; padding:4px 9px; border-radius:999px;
    background:#103324; color:#6fe19f; font-size:.68rem; font-weight:800;
}
.crop {
    border:1px solid #24463a; border-radius:11px;
    padding:12px; background:#0b1a15; min-height:95px;
}
.crop-name { font-weight:800; }
.crop-meta { color:#8fa9a0; font-size:.74rem; margin-top:4px; }
.line { border-top:1px solid #1d332c; margin:18px 0; }
</style>
""", unsafe_allow_html=True)

try:
    policy = importlib.import_module("main")
    policy_name = getattr(policy, "SYSTEM_NAME", "AgriNexus OS")
    policy_tagline = getattr(
        policy,
        "SYSTEM_TAGLINE",
        "Specialist agents. One farm. Continuous adaptation.",
    )
    policy_loaded = callable(getattr(policy, "agent", None))
except Exception:
    policy = None
    policy_name = "AgriNexus OS"
    policy_tagline = "Specialist agents. One farm. Continuous adaptation."
    policy_loaded = False


@dataclass
class Plot:
    id: str
    crop: str | None
    status: str
    growth: int
    moisture: int
    fertilized: bool = False


@dataclass
class Animal:
    id: str
    kind: str
    product: str
    fed: bool = True
    cared: bool = True
    fertilizer_ready: bool = True
    output: int = 0


@dataclass
class FarmState:
    day: int = 6
    hour: int = 14
    cash: float = 2840
    revenue: float = 620
    expenses: float = 780
    fertilizer: int = 8
    wheat: int = 14
    seeds: dict = field(default_factory=lambda: {
        "WHEAT": 4, "CARROT": 2, "TOMATO": 1,
        "STRAWBERRY": 2, "MELON": 0,
    })
    land: int = 25
    quadrants: int = 1
    plots: list = field(default_factory=list)
    animals: list = field(default_factory=list)
    events: list = field(default_factory=list)
    market_price: dict = field(default_factory=lambda: {
        "WHEAT": 31, "CARROT": 39, "TOMATO": 67,
        "STRAWBERRY": 128, "MELON": 86, "EGG": 53,
        "MILK": 166, "WOOL": 204, "FERTILIZER": 91,
    })
    demand: dict = field(default_factory=lambda: {
        "WHEAT": .88, "CARROT": .71, "TOMATO": .77,
        "STRAWBERRY": .83, "MELON": .24, "EGG": .79,
        "MILK": .81, "WOOL": .67,
    })

    def __post_init__(self):
        if not self.plots:
            self.plots = [
                Plot("A1", "WHEAT", "growing", 58, 72),
                Plot("A2", "CARROT", "growing", 76, 54),
                Plot("A3", None, "ready", 0, 0),
                Plot("B1", "TOMATO", "growing", 42, 68, True),
                Plot("B2", "STRAWBERRY", "growing", 63, 79, True),
                Plot("B3", None, "ready", 0, 0),
            ]
        if not self.animals:
            self.animals = [
                Animal("COW-01", "COW", "MILK", True, True, True, 2),
                Animal("COW-02", "COW", "MILK", True, True, True, 1),
                Animal("SHEEP-01", "SHEEP", "WOOL", True, True, True, 1),
                Animal("GOOSE-01", "GOOSE", "EGG", True, True, True, 2),
            ]
        if not self.events:
            self.events = [
                "AgriNexus initialized six specialist agents",
                "Crop portfolio inspected",
                "Livestock welfare cycle verified",
                "Market signal refreshed",
            ]

    @property
    def profit(self):
        return self.revenue - self.expenses

    @property
    def turns(self):
        return max(0, 720 - ((self.day - 1) * 24 + self.hour))

    @property
    def inventory(self):
        return self.wheat + self.fertilizer + sum(self.seeds.values())

    def log(self, message):
        self.events.insert(0, f"Day {self.day:02d} · {self.hour:02d}:00 — {message}")
        self.events = self.events[:10]

    def advance(self):
        self.hour += 1
        if self.hour >= 24:
            self.hour = 0
            self.day += 1
        for p in self.plots:
            if p.status == "growing":
                p.growth = min(100, p.growth + 5)
                p.moisture = max(0, p.moisture - 4)
                if p.growth >= 100:
                    p.status = "harvestable"


def get_state():
    if "farm" not in st.session_state:
        st.session_state.farm = FarmState()
    return st.session_state.farm


def collective_decision(f):
    # The UI twin mirrors the competition policy's priority envelope.
    urgent = next((p for p in f.plots if p.status == "growing" and p.moisture < 40), None)
    harvest = next((p for p in f.plots if p.status == "harvestable"), None)
    fertilizer_target = next(
        (p for p in f.plots if p.crop in ("TOMATO", "STRAWBERRY", "MELON")
         and not p.fertilized and p.growth >= 35),
        None,
    )
    animal_need = next((a for a in f.animals if not a.fed or not a.cared), None)

    if urgent:
        return "WATER", f"Water {urgent.id}", "Crop Agent", "Protect the biological deadline before the next observation.", .97, 34
    if animal_need:
        return "CARE", f"Care for {animal_need.id}", "Livestock Agent", "Protect animal survival and bank the next production bonus.", .96, 28
    if harvest:
        return "HARVEST", f"Harvest {harvest.id}", "Crop Agent", "Convert peak biological value into tradable inventory.", .95, 31
    if fertilizer_target and f.fertilizer:
        return "FERTILIZE", f"Fertilize {fertilizer_target.id}", "Fertility Agent", "Use expiring animal fertilizer where yield leverage is highest.", .92, 26
    if f.quadrants == 1 and f.cash >= 2200 and sum(p.status != "ready" for p in f.plots) >= 4:
        return "BUY_LAND", "Expand to neighboring quadrant", "Expansion Agent", "Current footprint is productive enough to absorb additional capacity.", .88, 120
    if f.wheat > 8 and f.market_price["WHEAT"] >= 28:
        return "SELL", "Sell surplus wheat", "Market Agent", "Capture a healthy staple price while preserving herd feed.", .90, f.market_price["WHEAT"]
    return "PLANT", "Plant highest-value deficit crop", "Crop Portfolio Agent", "Keep productive land occupied without sacrificing liquidity.", .84, 24


def execute(f, action):
    if action == "WATER":
        target = next((p for p in f.plots if p.status == "growing" and p.moisture < 40), None)
        if target:
            target.moisture = min(100, target.moisture + 58)
            f.log(f"Crop Agent watered {target.id}")
    elif action == "CARE":
        target = next((a for a in f.animals if not a.fed or not a.cared), None)
        if target:
            target.fed, target.cared = True, True
            f.log(f"Livestock Agent fed and cared for {target.id}")
    elif action == "HARVEST":
        target = next((p for p in f.plots if p.status == "harvestable"), None)
        if target:
            f.wheat += 2 if target.crop == "WHEAT" else 1
            target.status, target.crop, target.growth, target.moisture = "ready", None, 0, 0
            f.revenue += f.market_price.get("WHEAT", 31)
            f.log(f"Crop Agent harvested {target.id}")
    elif action == "FERTILIZE":
        target = next((p for p in f.plots if p.crop in ("TOMATO", "STRAWBERRY", "MELON") and not p.fertilized), None)
        if target and f.fertilizer:
            f.fertilizer -= 1
            target.fertilized = True
            f.log(f"Fertility Agent fertilized {target.id}")
    elif action == "SELL" and f.wheat > 8:
        qty = min(2, f.wheat - 8)
        f.wheat -= qty
        f.cash += qty * f.market_price["WHEAT"]
        f.revenue += qty * f.market_price["WHEAT"]
        f.log(f"Market Agent sold {qty} wheat units")
    elif action == "BUY_LAND" and f.quadrants == 1 and f.cash >= 2200:
        f.cash -= 1000
        f.expenses += 1000
        f.quadrants = 2
        f.land = 50
        f.log("Expansion Agent unlocked the neighboring quadrant")
    elif action == "PLANT":
        target = next((p for p in f.plots if p.status == "ready"), None)
        choices = [c for c in f.seeds if f.seeds[c] > 0]
        if target and choices:
            crop = max(choices, key=lambda c: f.market_price[c] / max(1, {"WHEAT":25,"CARROT":35,"TOMATO":60,"STRAWBERRY":120,"MELON":250}[c]))
            f.seeds[crop] -= 1
            target.crop, target.status, target.growth, target.moisture = crop, "growing", 0, 100
            f.log(f"Crop Portfolio Agent planted {crop} on {target.id}")
    f.advance()


f = get_state()
decision, decision_label, lead_agent, rationale, confidence, value = collective_decision(f)

with st.sidebar:
    st.markdown("## 🌱 AgriNexus Autonomous Farm")
    st.caption("Autonomous Multi-Agent Farm Intelligence")
    st.divider()
    st.markdown("**Intelligence fabric**")
    workspace = st.radio(
        "View",
        ["Autonomous Loop", "Agent Mesh", "Crop Intelligence", "Livestock", "Market", "Expansion"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown('<span class="eyebrow">Policy engine</span>', unsafe_allow_html=True)
    if policy_loaded:
        st.success("main.py policy loaded")
    else:
        st.warning("Policy module unavailable")
    st.caption("Competition entry remains dependency-free and isolated. This UI is an observability twin, not the competition agent.")
    st.divider()
    if st.button("↻ Reset farm twin", use_container_width=True):
        st.session_state.farm = FarmState()
        st.rerun()
    st.caption("AgriNexus OS")
    st.caption("Specialist agents · shared state · one arbitration layer")

st.markdown('<span class="eyebrow">AGRI NEXUS · AUTONOMOUS MULTI-AGENT FARM</span>', unsafe_allow_html=True)
st.title("AgriNexus OS")
st.subheader("The farm observes, reasons, arbitrates, acts, and learns.")
st.caption(policy_tagline)

k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Farm liquidity", f"{f.cash:,.0f}", "credits")
k2.metric("Net position", f"{f.profit:,.0f}", f"revenue {f.revenue:,.0f}")
k3.metric("Land footprint", f"{f.land} tiles", f"{f.quadrants}/4 quadrants")
k4.metric("Living herd", len(f.animals), "egg · milk · wool")
k5.metric("Turns remaining", f"{f.turns}", f"Day {f.day} · {f.hour:02d}:00")

st.divider()

left, right = st.columns([1.05, 1.35])

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="eyebrow">Autonomous decision cycle</span>', unsafe_allow_html=True)
    st.title(decision_label)
    st.markdown(f'<span class="pill">LEAD · {lead_agent}</span>', unsafe_allow_html=True)
    st.write(rationale)
    st.metric("Decision confidence", f"{confidence*100:.0f}%", f"estimated value +{value}")
    st.markdown("**Authorization checks**")
    for item in [
        "Biological survival protected",
        "Inventory / cash constraint checked",
        "Dynamic-market exposure bounded",
        "Turn budget respected",
    ]:
        st.write("✓ " + item)
    if st.button(f"Advance autonomous cycle · {decision}", type="primary", use_container_width=True):
        execute(f, decision)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="eyebrow">Farm state graph</span>', unsafe_allow_html=True)
    st.subheader("Cultivation footprint")
    cols = st.columns(3)
    for i, p in enumerate(f.plots):
        with cols[i % 3]:
            crop = p.crop or "Open"
            status = p.status.title()
            st.markdown(
                f'<div class="crop"><div class="crop-name">{p.id} · {crop}</div>'
                f'<div class="crop-meta">{status} · growth {p.growth}% · moisture {p.moisture}%</div>'
                f'<div class="crop-meta">fertilized: {"yes" if p.fertilized else "no"}</div></div><br>',
                unsafe_allow_html=True,
            )
    st.caption(f"Unlocked footprint: {f.land}/100 tiles · neighboring quadrants can be acquired as productivity rises.")
    st.markdown('</div>', unsafe_allow_html=True)

if workspace == "Agent Mesh":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="eyebrow">Multi-agent orchestration</span>', unsafe_allow_html=True)
    st.header("The AgriNexus agent mesh")
    agent_cols = st.columns(3)
    agents = [
        ("Crop Agent", "Plant · water · harvest", "Protect yield and biological deadlines."),
        ("Livestock Agent", "Buy · feed · care · harvest", "Turn wheat into eggs, milk and wool."),
        ("Fertility Agent", "Collect · allocate fertilizer", "Spend short-lived fertilizer on high-leverage crops."),
        ("Market Agent", "Price · sell · buy", "Trade in bounded batches against live market pressure."),
        ("Expansion Agent", "Land · capacity", "Acquire neighboring quadrants only when utilization supports it."),
        ("Workforce Agent", "Hands · scheduling", "Scale labor and reduce movement waste."),
    ]
    for i, (name, ops, goal) in enumerate(agents):
        with agent_cols[i % 3]:
            st.markdown(
                f'<div class="agent"><div class="agent-name">{name}</div>'
                f'<div class="agent-role">{ops}</div><br><div class="muted">{goal}</div></div><br>',
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)

elif workspace == "Autonomous Loop":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="eyebrow">Autonomous operating loop</span>', unsafe_allow_html=True)
    st.header("No farmer click is required")
    st.write("The simulator twin demonstrates the same operating pattern as the competition policy: observe state → specialist proposals → arbitration → guardrails → action → reconciliation.")
    st.code("OBSERVE → CROP / LIVESTOCK / FERTILITY / MARKET / EXPANSION / WORKFORCE → ARBITRATE → GUARDRAILS → ACT → RECONCILE", language="text")
    st.info("Use the cycle control only to step the visual twin. The Kaggriculture submission itself runs from agent(obs) without a UI.")
    st.markdown("</div>", unsafe_allow_html=True)

elif workspace == "Crop Intelligence":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="eyebrow">Crop portfolio</span>', unsafe_allow_html=True)
    st.header("Five-crop adaptive portfolio")
    rows = []
    for crop in ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON"]:
        rows.append([
            crop,
            f.seeds.get(crop,0),
            f.market_price[crop],
            f"{f.demand.get(crop,.5)*100:.0f}%",
            "Feed + market" if crop=="WHEAT" else "Market diversification",
        ])
    st.dataframe(pd.DataFrame(rows, columns=["Crop","Seeds","Live price","Town demand","Role"]), use_container_width=True, hide_index=True)
    st.caption("The policy can plant all five crop types; portfolio selection is driven by deficit, season time, and market signal rather than a fixed crop script.")
    st.markdown('</div>', unsafe_allow_html=True)

elif workspace == "Livestock":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="eyebrow">Animal economy</span>', unsafe_allow_html=True)
    st.header("Eggs · milk · wool")
    animal_df = pd.DataFrame([
        [a.id, a.kind, a.product, "Fed" if a.fed else "Needs feed", "Cared" if a.cared else "Needs care", a.output, "Ready" if a.fertilizer_ready else "Collected"]
        for a in f.animals
    ], columns=["Animal","Type","Output","Feed","Care","Held output","Fertilizer"])
    st.dataframe(animal_df, use_container_width=True, hide_index=True)
    st.metric("Fertilizer available", f.fertilizer, "short-lived daily resource")
    st.caption("Every living animal is also a fertilizer source; the fertility agent prioritizes collection before the daily availability expires.")
    st.markdown('</div>', unsafe_allow_html=True)

elif workspace == "Market":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="eyebrow">Dynamic economy</span>', unsafe_allow_html=True)
    st.header("Market pressure and town demand")
    market = pd.DataFrame({"Product": list(f.market_price), "Price": list(f.market_price.values())})
    fig = go.Figure(go.Bar(x=market["Product"], y=market["Price"]))
    fig.update_layout(height=300, margin=dict(l=0,r=0,t=15,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#edf7f2")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    st.dataframe(
        pd.DataFrame([[k, f.market_price[k], f"{f.demand.get(k,.5)*100:.0f}%"] for k in f.market_price],
                     columns=["Product","Price","Town demand"]),
        use_container_width=True, hide_index=True
    )
    st.caption("Sales are deliberately metered because the shared market price responds to aggregate inventory.")
    st.markdown('</div>', unsafe_allow_html=True)

elif workspace == "Expansion":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<span class="eyebrow">Territory strategy</span>', unsafe_allow_html=True)
    st.header("Neighboring land expansion")
    st.metric("Current footprint", f"{f.land}/100 tiles", f"{f.quadrants}/4 quadrants")
    st.progress(f.land / 100)
    st.write("Expansion Agent evaluates liquidity, labor and productive utilization before issuing BUY_LAND.")
    st.info("Quadrants are expanded progressively; the policy does not buy land simply because cash is available.")
    st.markdown('</div>', unsafe_allow_html=True)

else:
    a,b,c = st.columns([1.05,1.05,.9])
    with a:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<span class="eyebrow">Resource ledger</span>', unsafe_allow_html=True)
        st.header("Production inputs")
        inv = pd.DataFrame({
            "Resource":["Wheat","Fertilizer","Seeds"],
            "Units":[f.wheat,f.fertilizer,sum(f.seeds.values())],
        })
        fig = go.Figure(go.Bar(x=inv["Units"], y=inv["Resource"], orientation="h"))
        fig.update_layout(height=220, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#edf7f2")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    with b:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<span class="eyebrow">Agent consensus</span>', unsafe_allow_html=True)
        st.header("Decision pipeline")
        st.code("OBSERVE\n   ↓\nSPECIALIST PROPOSALS\n   ↓\nARBITRATE\n   ↓\nGUARDRAILS\n   ↓\nEXECUTE\n   ↓\nRECONCILE", language="text")
        st.caption("Specialists propose. The authorization layer resolves conflicts. The environment remains the source of truth.")
        st.markdown('</div>', unsafe_allow_html=True)

    with c:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<span class="eyebrow">Farm economics</span>', unsafe_allow_html=True)
        st.header("Capital")
        st.metric("Revenue", f"{f.revenue:,.0f}")
        st.metric("Expenses", f"{f.expenses:,.0f}")
        st.metric("Net", f"{f.profit:,.0f}")
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<span class="eyebrow">Decision trace</span>', unsafe_allow_html=True)
st.header("Recent autonomous events")
for event in f.events[:7]:
    st.write(event)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<span class="eyebrow">System identity</span>', unsafe_allow_html=True)
st.header("AgriNexus OS")
st.write("Multi-agent autonomous farm intelligence for crop production, livestock welfare, fertilizer recovery, territorial expansion, and dynamic-market adaptation.")
st.markdown("**Specialist agents. One farm. Continuous adaptation.**")
st.caption("The competition entry remains root-level main.py with agent(obs). This Streamlit application is the local visualization and simulation twin.")
st.markdown('</div>', unsafe_allow_html=True)
