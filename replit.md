# Autonomous Farm OS

An autonomous Kaggriculture operations console that observes farm state, explains decisions, and executes validated simulator actions.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `lib/api-spec/openapi.yaml` — source of truth for farm API contracts and generated hooks.
- `artifacts/api-server/src/lib/farm-simulator.ts` — canonical in-memory simulator state, deterministic policy decisions, and action reconciliation.
- `artifacts/api-server/src/routes/farm.ts` — farm state, recommendation, season-plan, market-decision, and execution routes.
- `artifacts/farm-operations/src/App.tsx` — live operations console.
- `artifacts/farm-operations/src/index.css` — console visual system and responsive layout.

## Architecture decisions

- The first vertical slices use an in-memory simulator so the decision loop is observable and deterministic before persistence is introduced.
- OpenAPI remains the contract boundary; generated React hooks and Zod schemas are used by the console and API.
- Specialized planning outputs are read-only projections of the same canonical simulator state; action execution remains centralized and validated.
- Market actions compare immediate sale value against future value and expose the rationale before execution.

## Product

- Live farm state with temporal, land, inventory, financial, and market context.
- Guarded next-action recommendation with compatible tile selection and visible action feedback.
- Season master plan with crop allocation, projected economics, assumptions, and risk.
- Market decision engine with sell-now versus future-value comparison.
- Agent coordination report showing specialist recommendations and central authorization.

## User preferences

- Build the autonomous farm system one complete vertical slice at a time.

## Gotchas

- Regenerate API clients with `pnpm --filter @workspace/api-spec run codegen` after every OpenAPI change.
- The API server workflow owns the `/api` routes; the web workflow owns the root console.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
