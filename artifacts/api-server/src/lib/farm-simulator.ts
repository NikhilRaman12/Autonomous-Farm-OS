import {
  ExecuteFarmActionBody,
  type FarmActionInput,
  type FarmActionResult,
  type FarmRecommendation,
  type FarmState,
  type AgentsReport,
  type MarketDecision,
  type SeasonPlan,
} from "@workspace/api-zod";

const initialState: FarmState = {
  temporal: { season: 1, day: 3, hour: 8, remainingTurns: 648 },
  land: 6,
  tiles: [
    { id: "A1", x: 0, y: 0, status: "planted", crop: "Wheat", growth: 22, moisture: 84 },
    { id: "A2", x: 1, y: 0, status: "growing", crop: "Wheat", growth: 61, moisture: 28 },
    { id: "A3", x: 2, y: 0, status: "ready", crop: null, growth: 0, moisture: 0 },
    { id: "B1", x: 0, y: 1, status: "growing", crop: "Wheat", growth: 74, moisture: 52 },
    { id: "B2", x: 1, y: 1, status: "harvestable", crop: "Wheat", growth: 100, moisture: 66 },
    { id: "B3", x: 2, y: 1, status: "ready", crop: null, growth: 0, moisture: 0 },
  ],
  inventory: { seeds: 8, produce: 2, fertilizer: 4, capacity: 24, used: 2 },
  market: { crop: "Wheat", price: 38, demand: 0.82, trend: "rising" },
  financial: { cash: 420, revenue: 190, expenses: 76, projectedProfit: 612 },
  activeTasks: ["Protect the harvest window", "Keep growing plots above 40% moisture"],
  completedTasks: ["Season plan initialized", "Field inspection"],
  lastEvent: "Observation reconciled at day 3, hour 8",
};

let farmState: FarmState = structuredClone(initialState);

export function getFarmSeasonPlan(): SeasonPlan {
  const activePlots = farmState.tiles.filter((tile) => tile.status !== "ready").length;
  const harvestablePlots = farmState.tiles.filter((tile) => tile.status === "harvestable").length;
  return {
    season: farmState.temporal.season,
    objective: "Protect cash flow while converting every available plot into harvestable value",
    strategy: "Wheat-led rotation with small-batch selling and no land expansion until the current plots are fully utilized.",
    crops: [
      {
        crop: farmState.market.crop,
        plots: activePlots,
        expectedYield: Math.max(4, activePlots + farmState.inventory.seeds),
        projectedRevenue: Math.round((activePlots + 2) * farmState.market.price),
        confidence: 0.84,
      },
    ],
    projectedRevenue: Math.round((activePlots + farmState.inventory.seeds + harvestablePlots) * farmState.market.price),
    projectedCost: 146,
    projectedProfit: Math.round(farmState.financial.projectedProfit),
    assumptions: [
      "Market demand stays above 70% for the next selling window",
      "Growing plots are watered before moisture falls below 40%",
      "Existing land is fully utilized before expansion is considered",
    ],
    riskLevel: farmState.market.trend === "falling" ? "high" : "moderate",
  };
}

export function getFarmMarketDecision(): MarketDecision {
  const quantity = Math.max(1, Math.floor(farmState.inventory.produce / 2));
  const sellingValue = quantity * farmState.market.price;
  const futurePrice = farmState.market.trend === "rising" ? farmState.market.price + 4 : farmState.market.price;
  const futureValue = quantity * futurePrice - 3;

  if (farmState.inventory.produce === 0) {
    return {
      decision: "WAIT",
      headline: "Wait for the next harvest",
      rationale: "There is no saleable produce in inventory. Preserve turns for crop care and reassess after harvest.",
      quantity: 0,
      expectedSellingValue: 0,
      expectedFutureValue: 0,
      signal: "neutral",
      risk: "low",
    };
  }

  return {
    decision: "PARTIAL_SELL",
    headline: `Sell ${quantity} unit${quantity === 1 ? "" : "s"} now`,
    rationale: `Demand is ${(farmState.market.demand * 100).toFixed(0)}% and the trend is ${farmState.market.trend}. Capture immediate cash flow with a partial sale while holding the remainder for a better window.`,
    quantity,
    expectedSellingValue: sellingValue,
    expectedFutureValue: futureValue,
    signal: "positive",
    risk: "moderate",
  };
}

export function getFarmAgentsReport(): AgentsReport {
  const recommendation = getFarmRecommendation();
  const thirsty = farmState.tiles.some((tile) => tile.status === "growing" && tile.moisture < 45);
  const harvestable = farmState.tiles.some((tile) => tile.status === "harvestable");
  return {
    orchestratorDecision: `${recommendation.action}: ${recommendation.label}`,
    lastReconciledAt: `Season ${farmState.temporal.season}, day ${farmState.temporal.day}, ${String(farmState.temporal.hour).padStart(2, "0")}:00`,
    agents: [
      {
        agentId: "season-planning",
        role: "Season planning",
        status: "ready",
        objective: "Protect season-level profit",
        recommendation: "Keep existing land fully utilized before expansion",
        confidence: 0.84,
        blockers: [],
      },
      {
        agentId: "crop-planning",
        role: "Crop planning",
        status: thirsty ? "recommending" : "ready",
        objective: "Protect crop lifecycle and yield",
        recommendation: thirsty ? "Water the lowest-moisture growing plot" : "Maintain current crop cadence",
        confidence: thirsty ? 0.94 : 0.81,
        blockers: thirsty ? ["Watering window is time-sensitive"] : [],
      },
      {
        agentId: "market-analysis",
        role: "Market analysis",
        status: "ready",
        objective: "Maximize selling value without price shock",
        recommendation: farmState.inventory.produce > 0 ? "Use a partial sale at current demand" : "Hold until inventory is available",
        confidence: 0.89,
        blockers: [],
      },
      {
        agentId: "resource-allocation",
        role: "Resource allocation",
        status: "ready",
        objective: "Balance turns, inventory, and field capacity",
        recommendation: "No hiring or land expansion is justified",
        confidence: 0.88,
        blockers: [],
      },
      {
        agentId: "execution",
        role: "Execution",
        status: harvestable ? "recommending" : "ready",
        objective: "Authorize only state-valid actions",
        recommendation: `${recommendation.action} is the next validated action`,
        confidence: recommendation.confidence,
        blockers: recommendation.guardrails,
      },
    ],
  };
}

function advanceTime() {
  farmState.temporal.hour += 1;
  if (farmState.temporal.hour >= 24) {
    farmState.temporal.hour = 0;
    farmState.temporal.day += 1;
  }
  farmState.temporal.remainingTurns = Math.max(0, farmState.temporal.remainingTurns - 1);

  for (const tile of farmState.tiles) {
    if (tile.status === "planted") {
      tile.status = "growing";
      tile.growth = Math.min(100, tile.growth + 12);
    } else if (tile.status === "growing") {
      tile.growth = Math.min(100, tile.growth + 5);
      tile.moisture = Math.max(0, tile.moisture - 4);
      if (tile.growth >= 100) tile.status = "harvestable";
    }
  }
}

export function getFarmState(): FarmState {
  return structuredClone(farmState);
}

export function getFarmRecommendation(): FarmRecommendation {
  const harvestable = farmState.tiles.find((tile) => tile.status === "harvestable");
  if (harvestable) {
    return {
      action: "HARVEST",
      label: `Harvest ${harvestable.id}`,
      rationale: `${harvestable.crop} is at peak readiness. Harvesting now protects yield and frees a productive tile.`,
      confidence: 0.98,
      expectedValue: 38,
      guardrails: ["Tile must be harvestable", "Inventory must have capacity"],
    };
  }

  const thirsty = farmState.tiles.find(
    (tile) => tile.status === "growing" && tile.moisture < 45,
  );
  if (thirsty) {
    return {
      action: "WATER",
      label: `Water ${thirsty.id}`,
      rationale: `${thirsty.crop} on ${thirsty.id} is below the moisture threshold. Watering avoids growth loss before the next observation.`,
      confidence: 0.94,
      expectedValue: 24,
      guardrails: ["Tile must be growing", "Moisture is capped at 100%"],
    };
  }

  if (farmState.inventory.produce > 0 && farmState.market.demand >= 0.75) {
    return {
      action: "SELL",
      label: "Sell one unit",
      rationale: `Demand is ${(farmState.market.demand * 100).toFixed(0)}% and price is ${farmState.market.price} credits. A small sale captures the rising market without dumping supply.`,
      confidence: 0.89,
      expectedValue: farmState.market.price,
      guardrails: ["Quantity must be in inventory", "Partial sale limits market impact"],
    };
  }

  const ready = farmState.tiles.find((tile) => tile.status === "ready");
  if (ready && farmState.inventory.seeds > 0) {
    return {
      action: "PLANT",
      label: `Plant ${ready.id}`,
      rationale: `${ready.id} is available and seed inventory supports another wheat cycle within the season window.`,
      confidence: 0.86,
      expectedValue: 31,
      guardrails: ["Tile must be ready", "Seed inventory must be positive"],
    };
  }

  return {
    action: "PASS",
    label: "Advance observation",
    rationale: "No higher-value action is currently justified. Advance one turn and observe again.",
    confidence: 0.74,
    expectedValue: 0,
    guardrails: ["No resources are spent", "State is re-evaluated after the turn"],
  };
}

function findTile(tileId: string | null | undefined) {
  return farmState.tiles.find((tile) => tile.id === tileId);
}

function completeTask(label: string) {
  farmState.completedTasks = [label, ...farmState.completedTasks].slice(0, 5);
}

export function executeFarmAction(input: FarmActionInput): FarmActionResult {
  const parsed = ExecuteFarmActionBody.parse(input);
  const tile = parsed.tileId ? findTile(parsed.tileId) : undefined;

  if (parsed.action !== "SELL" && parsed.action !== "PASS" && !tile) {
    throw new Error("A valid tileId is required for this action.");
  }

  switch (parsed.action) {
    case "WATER":
      if (tile?.status !== "growing") throw new Error("Only growing tiles can be watered.");
      tile.moisture = Math.min(100, tile.moisture + 54);
      completeTask(`Watered ${tile.id}`);
      farmState.lastEvent = `Watered ${tile.id}; moisture reconciled to ${tile.moisture}%`;
      break;
    case "PLANT":
      if (tile?.status !== "ready") throw new Error("Only ready tiles can be planted.");
      if (farmState.inventory.seeds < 1) throw new Error("No seeds available.");
      farmState.inventory.seeds -= 1;
      tile.status = "planted";
      tile.crop = farmState.market.crop;
      tile.growth = 0;
      tile.moisture = 100;
      completeTask(`Planted ${tile.id}`);
      farmState.lastEvent = `Planted ${tile.crop} on ${tile.id}`;
      break;
    case "HARVEST":
      if (tile?.status !== "harvestable") throw new Error("Only harvestable tiles can be harvested.");
      if (farmState.inventory.used >= farmState.inventory.capacity) {
        throw new Error("Inventory capacity is full.");
      }
      farmState.inventory.produce += 1;
      farmState.inventory.used += 1;
      tile.status = "ready";
      tile.crop = null;
      tile.growth = 0;
      tile.moisture = 0;
      completeTask(`Harvested ${tile.id}`);
      farmState.lastEvent = `Harvested one unit from ${tile.id}`;
      break;
    case "SELL": {
      const quantity = parsed.quantity ?? 1;
      if (quantity > farmState.inventory.produce) throw new Error("Not enough produce in inventory.");
      const gross = quantity * farmState.market.price;
      farmState.inventory.produce -= quantity;
      farmState.inventory.used -= quantity;
      farmState.financial.cash += gross;
      farmState.financial.revenue += gross;
      farmState.financial.projectedProfit += gross;
      completeTask(`Sold ${quantity} unit${quantity === 1 ? "" : "s"} of ${farmState.market.crop}`);
      farmState.lastEvent = `Sold ${quantity} unit${quantity === 1 ? "" : "s"} for ${gross} credits`;
      break;
    }
    case "PASS":
      farmState.lastEvent = "Passed one turn for observation";
      break;
  }

  advanceTime();
  const state = getFarmState();
  return {
    success: true,
    message: farmState.lastEvent,
    state,
    recommendation: getFarmRecommendation(),
  };
}

export function resetFarmState() {
  farmState = structuredClone(initialState);
}