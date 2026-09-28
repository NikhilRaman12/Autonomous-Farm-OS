from mcp.server.fastmcp import FastMCP
from .engine import initial_farm

mcp = FastMCP("fieldnode-farm-tools")

@mcp.tool()
def inspect_farm() -> dict:
    """Inspect the authoritative farm state."""
    return initial_farm().model_dump()

@mcp.tool()
def get_market() -> dict:
    """Return current simulated market conditions."""
    s = initial_farm()
    return {"crop":"Wheat","price":s.market_price,"demand":s.market_demand,"trend":s.market_trend}

if __name__ == "__main__":
    mcp.run()
