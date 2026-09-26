import { Router, type IRouter } from "express";
import {
  ExecuteFarmActionResponse,
  GetFarmRecommendationResponse,
  GetFarmStateResponse,
} from "@workspace/api-zod";
import {
  executeFarmAction,
  getFarmRecommendation,
  getFarmMarketDecision,
  getFarmAgentsReport,
  getFarmSeasonPlan,
  getFarmState,
} from "../lib/farm-simulator";

const router: IRouter = Router();

router.get("/farm/state", (_req, res) => {
  res.json(GetFarmStateResponse.parse(getFarmState()));
});

router.get("/farm/recommendation", (_req, res) => {
  res.json(GetFarmRecommendationResponse.parse(getFarmRecommendation()));
});

router.get("/farm/season-plan", (_req, res) => {
  res.json(getFarmSeasonPlan());
});

router.get("/farm/market-decision", (_req, res) => {
  res.json(getFarmMarketDecision());
});

router.get("/farm/agents/report", (_req, res) => {
  res.json(getFarmAgentsReport());
});

router.post("/farm/actions/execute", (req, res) => {
  try {
    res.json(ExecuteFarmActionResponse.parse(executeFarmAction(req.body)));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to execute action.";
    res.status(400).json({ error: message });
  }
});

export default router;