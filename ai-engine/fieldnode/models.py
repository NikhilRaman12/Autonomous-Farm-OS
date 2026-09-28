from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field

Action = Literal["WATER", "PLANT", "HARVEST", "SELL", "PASS"]

class Tile(BaseModel):
    id: str
    x: int
    y: int
    status: Literal["ready", "planted", "growing", "harvestable"]
    crop: str | None = None
    growth: float = 0
    moisture: float = 0

class FarmState(BaseModel):
    season: int = 1
    day: int = 1
    hour: int = 8
    remaining_turns: int = 648
    tiles: list[Tile]
    seeds: int = 8
    produce: int = 0
    fertilizer: int = 4
    inventory_capacity: int = 24
    cash: float = 420
    revenue: float = 190
    expenses: float = 76
    market_price: float = 38
    market_demand: float = 0.82
    market_trend: Literal["rising", "stable", "falling"] = "rising"
    events: list[str] = Field(default_factory=list)

class Proposal(BaseModel):
    agent: str
    action: Action
    tile_id: str | None = None
    quantity: int = 1
    priority: float = 0
    confidence: float = 0
    rationale: str
    resources: dict[str, float] = Field(default_factory=dict)

class A2AMessage(BaseModel):
    message_id: str
    sender: str
    receiver: str
    kind: Literal["PROPOSAL", "RESPONSE", "NEGOTIATION", "EVENT", "RESULT"]
    payload: dict
    confidence: float = 0
