---
name: Autonomous farm vertical-slice architecture
description: Durable sequencing decision for building the farm operator.
---

Build the farm operator as complete vertical slices over one canonical simulator state: contract, deterministic policy, validated execution, and visible console surface before adding the next agent capability.

**Why:** The specification requires closed-loop execution, and a shared deterministic state makes stale-plan and conflicting-agent failures visible early without hiding them behind persistence or LLM calls.

**How to apply:** Add future agents as projections and decision nodes over the same state; keep execution centralized and only introduce persistence or LLM reasoning when the corresponding slice has a concrete need.