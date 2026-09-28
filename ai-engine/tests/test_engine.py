from fieldnode.engine import initial_farm, run_cycle
from fieldnode.policy import validate
from fieldnode.models import Proposal

def test_autonomous_cycle_executes():
    result = run_cycle(initial_farm())
    assert result["result"]["success"] is True
    assert result["decision"].action in {"WATER", "HARVEST", "SELL", "PLANT", "PASS"}

def test_policy_blocks_invalid_harvest():
    s = initial_farm()
    p = Proposal(agent="test", action="HARVEST", tile_id="A2", confidence=1, rationale="test")
    ok, _ = validate(s, p)
    assert not ok
