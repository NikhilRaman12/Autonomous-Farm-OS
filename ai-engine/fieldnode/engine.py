from __future__ import annotations
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from .models import FarmState, Proposal, A2AMessage
from .agents import collect_proposals
from .policy import select_valid
from .ml import predict_yield
from .reasoning import explain_decision

class GraphState(TypedDict, total=False):
    farm: FarmState
    proposals: list[Proposal]
    messages: list[A2AMessage]
    decision: Proposal
    result: dict
    prediction: float
    explanation: str

def observe(st: GraphState):
    return {"prediction": predict_yield(st["farm"])}

def deliberate(st: GraphState):
    proposals, messages = collect_proposals(st["farm"])
    return {"proposals": proposals, "messages": messages}

def orchestrate(st: GraphState):
    decision, reason = select_valid(st["farm"], st["proposals"])
    explanation = explain_decision(st["farm"], decision)
    decision.rationale = f"{decision.rationale} Policy: {reason}. {explanation}"
    return {"decision": decision, "explanation": explanation}

def execute(st: GraphState):
    s = st["farm"].model_copy(deep=True)
    p = st["decision"]
    tile = next((t for t in s.tiles if t.id == p.tile_id), None)
    if p.action == "WATER" and tile:
        tile.moisture = min(100, tile.moisture + 50)
    elif p.action == "PLANT" and tile:
        s.seeds -= p.quantity; tile.status = "planted"; tile.crop = "Wheat"; tile.growth = 0; tile.moisture = 100
    elif p.action == "HARVEST" and tile:
        s.produce += p.quantity; tile.status = "ready"; tile.crop = None; tile.growth = 0; tile.moisture = 0
    elif p.action == "SELL":
        s.produce -= p.quantity; s.cash += p.quantity * s.market_price; s.revenue += p.quantity * s.market_price
    s.hour += 1
    if s.hour >= 24: s.hour = 0; s.day += 1
    s.remaining_turns = max(0, s.remaining_turns - 1)
    for t in s.tiles:
        if t.status == "growing":
            t.growth = min(100, t.growth + 5); t.moisture = max(0, t.moisture - 4)
        elif t.status == "planted":
            t.status = "growing"; t.growth = min(100, t.growth + 12)
        if t.growth >= 100 and t.crop:
            t.status = "harvestable"
    s.events.insert(0, f"{p.action} executed by autonomous orchestrator")
    return {"farm": s, "result": {"success": True, "action": p.model_dump(), "prediction": st.get("prediction", 0),
                                  "explanation": st.get("explanation", "")}}

def build_graph():
    g = StateGraph(GraphState)
    g.add_node("observe", observe)
    g.add_node("deliberate", deliberate)
    g.add_node("orchestrate", orchestrate)
    g.add_node("execute", execute)
    g.add_edge(START, "observe"); g.add_edge("observe", "deliberate")
    g.add_edge("deliberate", "orchestrate"); g.add_edge("orchestrate", "execute")
    g.add_edge("execute", END)
    return g.compile()

def initial_farm() -> FarmState:
    return FarmState(tiles=[
        {"id":"A1","x":0,"y":0,"status":"planted","crop":"Wheat","growth":22,"moisture":84},
        {"id":"A2","x":1,"y":0,"status":"growing","crop":"Wheat","growth":61,"moisture":28},
        {"id":"A3","x":2,"y":0,"status":"ready","crop":None,"growth":0,"moisture":0},
        {"id":"B1","x":0,"y":1,"status":"growing","crop":"Wheat","growth":74,"moisture":52},
        {"id":"B2","x":1,"y":1,"status":"harvestable","crop":"Wheat","growth":100,"moisture":66},
        {"id":"B3","x":2,"y":1,"status":"ready","crop":None,"growth":0,"moisture":0},
    ])

def run_cycle(s: FarmState):
    return build_graph().invoke({"farm": s})
