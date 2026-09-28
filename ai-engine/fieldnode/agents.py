from __future__ import annotations
from .models import FarmState, Proposal, A2AMessage

def crop_health_agent(s: FarmState) -> Proposal:
    thirsty = min((t for t in s.tiles if t.status == "growing"), key=lambda t: t.moisture, default=None)
    if thirsty and thirsty.moisture < 40:
        return Proposal(agent="crop-health", action="WATER", tile_id=thirsty.id, priority=100, confidence=.96,
                        rationale=f"{thirsty.id} is below the crop moisture safety threshold.")
    return Proposal(agent="crop-health", action="PASS", priority=20, confidence=.78,
                    rationale="No immediate crop-health intervention is required.")

def harvest_agent(s: FarmState) -> Proposal:
    tile = next((t for t in s.tiles if t.status == "harvestable"), None)
    if tile:
        return Proposal(agent="harvest", action="HARVEST", tile_id=tile.id, priority=95, confidence=.99,
                        rationale=f"{tile.id} reached harvest maturity; harvesting protects the window.")
    return Proposal(agent="harvest", action="PASS", priority=10, confidence=.8,
                    rationale="No tile is currently harvestable.")

def market_agent(s: FarmState) -> Proposal:
    if s.produce > 0 and s.market_demand >= .75:
        return Proposal(agent="market", action="SELL", quantity=1, priority=60, confidence=.9,
                        rationale="Demand is strong; sell a controlled quantity to preserve upside.")
    return Proposal(agent="market", action="PASS", priority=15, confidence=.8,
                    rationale="No attractive sale window is available.")

def planting_agent(s: FarmState) -> Proposal:
    tile = next((t for t in s.tiles if t.status == "ready"), None)
    if tile and s.seeds > 0:
        return Proposal(agent="crop-planning", action="PLANT", tile_id=tile.id, priority=45, confidence=.86,
                        rationale=f"{tile.id} is available and seed inventory supports another cycle.")
    return Proposal(agent="crop-planning", action="PASS", priority=10, confidence=.8,
                    rationale="Planting is not currently justified.")

def resource_agent(s: FarmState, proposals: list[Proposal]) -> A2AMessage:
    water_need = sum(1 for p in proposals if p.action == "WATER")
    allowed = water_need <= 1
    return A2AMessage(message_id="resource-check", sender="resource-allocation",
                      receiver="orchestrator", kind="RESPONSE",
                      payload={"water_available": allowed, "cash": s.cash, "seeds": s.seeds},
                      confidence=.98)

def collect_proposals(s: FarmState) -> tuple[list[Proposal], list[A2AMessage]]:
    proposals = [crop_health_agent(s), harvest_agent(s), market_agent(s), planting_agent(s)]
    return proposals, [resource_agent(s, proposals)]
