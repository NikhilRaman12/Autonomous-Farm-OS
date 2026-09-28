from .models import FarmState, Proposal

def validate(s: FarmState, p: Proposal) -> tuple[bool, str]:
    tile = next((t for t in s.tiles if t.id == p.tile_id), None)
    if p.action == "WATER":
        if not tile or tile.status != "growing": return False, "Water requires a growing tile."
        if tile.moisture >= 100: return False, "Tile is already fully hydrated."
    elif p.action == "PLANT":
        if not tile or tile.status != "ready": return False, "Planting requires a ready tile."
        if s.seeds < p.quantity: return False, "Insufficient seed inventory."
    elif p.action == "HARVEST":
        if not tile or tile.status != "harvestable": return False, "Tile is not harvestable."
        if s.produce + p.quantity > s.inventory_capacity: return False, "Insufficient storage capacity."
    elif p.action == "SELL":
        if p.quantity > s.produce: return False, "Insufficient produce."
    return True, "policy-approved"

def select_valid(s: FarmState, proposals: list[Proposal]) -> tuple[Proposal, str]:
    for p in sorted(proposals, key=lambda x: (x.priority, x.confidence), reverse=True):
        ok, reason = validate(s, p)
        if ok: return p, reason
    return proposals[-1], "no higher-priority action passed policy"
