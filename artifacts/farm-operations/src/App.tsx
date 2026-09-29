import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { useExecuteFarmAction, useGetFarmAgentsReport, useGetFarmMarketDecision, useGetFarmRecommendation, useGetFarmSeasonPlan, useGetFarmState, useHealthCheck, getGetFarmStateQueryKey, getGetFarmRecommendationQueryKey, getGetFarmSeasonPlanQueryKey, getGetFarmMarketDecisionQueryKey, getGetFarmAgentsReportQueryKey, type FarmActionInputAction, type FarmState, type FarmRecommendation, type SeasonPlan, type MarketDecision, type AgentsReport } from '@workspace/api-client-react';
import { AlertTriangle, ArrowDownRight, ArrowUpRight, Check, ChevronRight, CircleDot, ClipboardList, Droplets, Leaf, Loader2, LockKeyhole, Package, RefreshCw, ScanLine, Sprout, Store, Sun, Tractor, TrendingUp, Wheat, Zap } from 'lucide-react';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/not-found';
import { Route, Switch, Router as WouterRouter, useLocation } from 'wouter';
import './index.css';

const queryClient = new QueryClient();

const money = (value: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
const number = (value: number) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value);
const titleCase = (value: string) => value.toLowerCase().replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
const actionNeedsTile = (action: string) => action === 'WATER' || action === 'PLANT' || action === 'HARVEST';
const isCompatibleTile = (status: string, action: string) => action === 'WATER' ? status === 'growing' || status === 'planted' : action === 'HARVEST' ? status === 'harvestable' : action === 'PLANT' ? status === 'ready' : true;

function StatusPill({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'good' | 'accent' | 'warn' }) {
  return <span className={`status-pill status-${tone}`}><span className="status-dot" />{children}</span>;
}

function Sidebar({ health }: { health?: string }) {
  const [location] = useLocation();
  return (
    <aside className="sidebar">
      <div className="brand-lockup">
        <div className="brand-mark"><ScanLine size={20} strokeWidth={1.8} /></div>
        <div><div className="brand-name">AgriNexus</div><div className="brand-sub">Autonomous Farm OS</div></div>
      </div>
      <div className="sidebar-rule" />
      <div className="eyebrow sidebar-label">Workspace</div>
      <nav className="side-nav" aria-label="Primary navigation">
        <a className={`side-nav-item ${location === '/' ? 'is-active' : ''}`} href="/" data-testid="link-console">
          <CircleDot size={16} /><span>Autonomous control</span><span className="nav-live">AUTO</span>
        </a>
      </nav>
      <div className="sidebar-bottom">
        <div className="system-card">
          <div className="system-card-head"><span className="eyebrow">System link</span><StatusPill tone={health === 'ok' ? 'good' : 'warn'}>{health === 'ok' ? 'Nominal' : 'Checking'}</StatusPill></div>
          <div className="system-line"><span className="pulse" />Simulator connected</div>
          <div className="system-meta mono">KAGG-OPS / 04</div>
        </div>
        <div className="sidebar-foot"><LockKeyhole size={13} /> Autonomous mode · human override available</div>
      </div>
    </aside>
  );
}

function Header({ state, onRefresh, refreshing }: { state: FarmState; onRefresh: () => void; refreshing: boolean }) {
  return (
    <header className="topbar">
      <div className="mobile-brand"><div className="brand-mark small"><ScanLine size={16} /></div><span>FIELDNODE</span></div>
      <div className="breadcrumb"><span className="eyebrow">Operations</span><ChevronRight size={14} /><strong>Live console</strong></div>
      <div className="topbar-right">
        <div className="clock-readout"><Sun size={15} /><span>Season {state.temporal.season}</span><b>Day {state.temporal.day}</b><span className="clock-hour mono">{String(state.temporal.hour).padStart(2, '0')}:00</span></div>
        <button className="icon-button" onClick={onRefresh} disabled={refreshing} aria-label="Refresh farm state" data-testid="button-refresh">
          <RefreshCw size={16} className={refreshing ? 'spin' : ''} />
        </button>
        <div className="avatar">OP</div>
      </div>
    </header>
  );
}

function Metric({ label, value, detail, tone = 'default', icon: Icon }: { label: string; value: string; detail: string; tone?: string; icon: typeof Leaf }) {
  return <div className={`metric metric-${tone}`} data-testid={`metric-${label.toLowerCase().replaceAll(' ', '-')}`}>
    <div className="metric-top"><span className="eyebrow">{label}</span><Icon size={15} /></div>
    <div className="metric-value">{value}</div><div className="metric-detail">{detail}</div>
  </div>;
}

function RecommendationPanel({ recommendation, state, selectedTile, setSelectedTile, onExecute, isPending, feedback, autopilot }: { recommendation: FarmRecommendation; state: FarmState; selectedTile: string | null; setSelectedTile: (id: string | null) => void; onExecute: (action: FarmActionInputAction, tileId: string | null, quantity: number | null) => void; isPending: boolean; feedback: { success: boolean; message: string } | null; autopilot: boolean }) {
  const [quantity, setQuantity] = useState(recommendation.action === 'SELL' ? Math.max(1, state.inventory.produce) : 1);
  const needsTile = actionNeedsTile(recommendation.action);
  const availableTiles = state.tiles.filter((tile) => isCompatibleTile(tile.status, recommendation.action));
  const activeTile = state.tiles.find((tile) => tile.id === selectedTile);
  const canExecute = !needsTile || Boolean(selectedTile);
  return (
    <section className="panel recommendation-panel fade-up" data-testid="panel-recommendation">
      <div className="panel-kicker"><div className="signal-icon"><Zap size={16} /></div><span className="eyebrow">Autonomous decision</span><span className="decision-line" /></div>
      <div className="recommendation-head"><div><div className="recommendation-action">{titleCase(recommendation.action)}</div><h2>{recommendation.label}</h2></div><div className="confidence"><strong>{Math.round(recommendation.confidence * 100)}%</strong><span>confidence</span></div></div>
      <p className="rationale">{recommendation.rationale}</p>
      <div className="value-row"><div><span className="eyebrow">Expected value</span><strong className="value-positive">{recommendation.expectedValue >= 0 ? '+' : ''}{money(recommendation.expectedValue)}</strong></div><div className="guardrail-count"><LockKeyhole size={14} />{recommendation.guardrails.length} guardrails verified</div></div>
      <div className="guardrails">{recommendation.guardrails.map((guardrail) => <div className="guardrail" key={guardrail}><Check size={13} />{guardrail}</div>)}</div>
      {needsTile && <div className="action-config">
        <div className="config-heading"><span className="eyebrow">Target tile</span><span className="mono config-count">{availableTiles.length} compatible</span></div>
        <div className="tile-select-row">
          {availableTiles.length ? availableTiles.map((tile) => <button key={tile.id} className={`tile-choice ${selectedTile === tile.id ? 'selected' : ''}`} onClick={() => setSelectedTile(tile.id)} data-testid={`button-select-tile-${tile.id}`}><span>{tile.id}</span><small>{tile.crop ? titleCase(tile.crop) : 'Open plot'}</small></button>) : <div className="no-compatible">No compatible tiles detected.</div>}
        </div>
        {activeTile && <div className="selected-readout"><span><CircleDot size={12} /> {activeTile.id} selected</span><span className="mono">{Math.round(activeTile.moisture)}% moisture</span></div>}
      </div>}
      {(recommendation.action === 'SELL' || recommendation.action === 'PLANT') && <div className="quantity-control"><label htmlFor="action-quantity" className="eyebrow">{recommendation.action === 'SELL' ? 'Units to sell' : 'Seed units'}</label><input id="action-quantity" type="number" min={1} max={recommendation.action === 'SELL' ? state.inventory.produce : state.inventory.seeds} value={quantity} onChange={(event) => setQuantity(Number(event.target.value))} data-testid="input-action-quantity" /><span className="mono">/ {recommendation.action === 'SELL' ? state.inventory.produce : state.inventory.seeds} available</span></div>}
      <button className="execute-button" disabled={isPending || !canExecute || (recommendation.action === 'SELL' && state.inventory.produce < 1)} onClick={() => onExecute(recommendation.action, needsTile ? selectedTile : null, recommendation.action === 'SELL' || recommendation.action === 'PLANT' ? quantity : null)} data-testid="button-execute-action">
        {isPending ? <><Loader2 size={17} className="spin" /> Reconciling state</> : autopilot ? <><Zap size={17} /> Autonomous execution active</> : <><Tractor size={17} /> Human override: execute now <ChevronRight size={17} /></>}
      </button>
      {!canExecute && <div className="inline-help">Select a compatible tile to arm this action.</div>}
      {feedback && <div className={`action-feedback ${feedback.success ? 'feedback-success' : 'feedback-error'}`} data-testid="status-action-feedback"><span>{feedback.success ? <Check size={15} /> : <AlertTriangle size={15} />}</span>{feedback.message}</div>}
    </section>
  );
}

function FarmMap({ state, selectedTile, setSelectedTile }: { state: FarmState; selectedTile: string | null; setSelectedTile: (id: string) => void }) {
  const maxX = Math.max(...state.tiles.map((tile) => tile.x), 1);
  const maxY = Math.max(...state.tiles.map((tile) => tile.y), 1);
  return (
    <section className="panel farm-panel fade-up fade-up-delay-1" data-testid="panel-farm-grid">
      <div className="panel-header"><div><span className="eyebrow">Field topology</span><h2>Active plots</h2></div><div className="map-legend"><span><i className="legend-dot ready" />Ready</span><span><i className="legend-dot growing" />Growing</span><span><i className="legend-dot harvestable" />Harvest</span></div></div>
      <div className="map-wrap">
        <div className="axis-y">{Array.from({ length: maxY + 1 }, (_, index) => <span key={index}>{index}</span>)}</div>
        <div className="farm-grid" style={{ gridTemplateColumns: `repeat(${maxX + 1}, minmax(54px, 1fr))` }}>
          {state.tiles.map((tile) => <button key={tile.id} className={`farm-tile tile-${tile.status} ${selectedTile === tile.id ? 'is-selected' : ''}`} onClick={() => setSelectedTile(tile.id)} style={{ gridColumn: tile.x + 1, gridRow: maxY - tile.y + 1 }} data-testid={`button-farm-tile-${tile.id}`}>
            <span className="tile-id mono">{tile.id}</span><span className="tile-crop">{tile.crop ? titleCase(tile.crop) : 'Open'}</span><span className="tile-growth">{tile.status === 'ready' ? 'Available' : `${Math.round(tile.growth)}%`}</span><span className="moisture-bar"><i style={{ width: `${Math.min(100, tile.moisture)}%` }} /></span>
          </button>)}
        </div>
      </div>
      <div className="map-footer"><span><span className="mono">{state.tiles.length}</span> monitored plots</span><span className="map-coords mono">X 0—{maxX} / Y 0—{maxY}</span></div>
    </section>
  );
}

function InventoryCard({ state }: { state: FarmState }) {
  const inventory = state.inventory;
  const usedPercent = inventory.capacity ? (inventory.used / inventory.capacity) * 100 : 0;
  return <section className="panel compact-panel fade-up fade-up-delay-2" data-testid="panel-inventory"><div className="panel-header"><div><span className="eyebrow">Resource ledger</span><h2>Inventory</h2></div><Package size={18} /></div><div className="inventory-total"><strong>{number(inventory.used)}</strong><span>/ {number(inventory.capacity)} capacity</span></div><div className="capacity-bar"><i style={{ width: `${Math.min(100, usedPercent)}%` }} /></div><div className="inventory-list"><div><span><Sprout size={14} />Seeds</span><strong>{number(inventory.seeds)}</strong></div><div><span><Wheat size={14} />Produce</span><strong>{number(inventory.produce)}</strong></div><div><span><Droplets size={14} />Fertilizer</span><strong>{number(inventory.fertilizer)}</strong></div></div></section>;
}

function MarketCard({ state, decision }: { state: FarmState; decision: MarketDecision }) {
  const rising = state.market.trend === 'rising';
  return <section className="panel compact-panel fade-up fade-up-delay-2" data-testid="panel-market"><div className="panel-header"><div><span className="eyebrow">Market signal</span><h2>Local exchange</h2></div><Store size={18} /></div><div className="market-crop"><div className="crop-orb"><Leaf size={18} /></div><div><strong>{titleCase(state.market.crop)}</strong><span>Demand index {number(state.market.demand)}</span></div></div><div className="market-price"><strong>{money(state.market.price)}</strong><span className={rising ? 'trend-up' : 'trend-down'}>{rising ? <ArrowUpRight size={15} /> : <ArrowDownRight size={15} />}{titleCase(state.market.trend)}</span></div><div className="market-meter"><i style={{ width: `${Math.min(100, state.market.demand * 100)}%` }} /></div><div className="market-foot"><span>Demand pressure</span><span className="mono">{number(state.market.demand)} / 1</span></div><div className="market-decision"><div><span className="eyebrow">Decision engine</span><strong>{decision.headline}</strong></div><span className={`decision-badge decision-${decision.signal}`}>{titleCase(decision.signal)}</span><p>{decision.rationale}</p><div className="market-comparison"><span>Sell now <b>{money(decision.expectedSellingValue)}</b></span><span>Future value <b>{money(decision.expectedFutureValue)}</b></span></div></div></section>;
}

function FinanceCard({ state }: { state: FarmState }) {
  const profitPositive = state.financial.projectedProfit >= 0;
  return <section className="panel compact-panel finance-panel fade-up fade-up-delay-2" data-testid="panel-financial"><div className="panel-header"><div><span className="eyebrow">Financial context</span><h2>Season ledger</h2></div><TrendingUp size={18} /></div><div className="finance-main"><span className="eyebrow">Projected profit</span><strong className={profitPositive ? 'value-positive' : 'value-negative'}>{money(state.financial.projectedProfit)}</strong><span className="finance-caption">at current action path</span></div><div className="finance-grid"><div><span>Cash</span><strong>{money(state.financial.cash)}</strong></div><div><span>Revenue</span><strong>{money(state.financial.revenue)}</strong></div><div><span>Expenses</span><strong>{money(state.financial.expenses)}</strong></div></div></section>;
}

function SeasonPlanCard({ plan }: { plan: SeasonPlan }) {
  return <section className="panel season-plan-panel fade-up fade-up-delay-3" data-testid="panel-season-plan">
    <div className="panel-header"><div><span className="eyebrow">Season master plan</span><h2>Plan under execution</h2></div><ClipboardList size={18} /></div>
    <div className="plan-strategy"><span className="eyebrow">Objective</span><strong>{plan.objective}</strong><p>{plan.strategy}</p></div>
    <div className="plan-crops">{plan.crops.map((crop) => <div className="plan-crop" key={crop.crop}><div><span className="eyebrow">{titleCase(crop.crop)} allocation</span><strong>{crop.plots} plots</strong></div><div className="plan-crop-value"><strong>{money(crop.projectedRevenue)}</strong><span>{Math.round(crop.confidence * 100)}% confidence</span></div></div>)}</div>
    <div className="plan-summary"><div><span className="eyebrow">Projected revenue</span><strong>{money(plan.projectedRevenue)}</strong></div><div><span className="eyebrow">Projected cost</span><strong>{money(plan.projectedCost)}</strong></div><div><span className="eyebrow">Net profit</span><strong className="value-positive">{money(plan.projectedProfit)}</strong></div><StatusPill tone={plan.riskLevel === 'high' ? 'warn' : 'accent'}>{titleCase(plan.riskLevel)} risk</StatusPill></div>
    <div className="plan-assumptions"><span className="eyebrow">Planning assumptions</span>{plan.assumptions.map((assumption) => <div className="guardrail" key={assumption}><Check size={13} />{assumption}</div>)}</div>
  </section>;
}

function AgentCoordinationCard({ report }: { report: AgentsReport }) {
  return <section className="panel agent-panel fade-up fade-up-delay-3" data-testid="panel-agent-coordination">
    <div className="panel-header"><div><span className="eyebrow">Agent council</span><h2>Specialists reason. Arbitrator authorizes.</h2></div><Zap size={18} /></div>
    <div className="autonomy-loop"><span>OBSERVE</span><b>→</b><span>PROPOSE</span><b>→</b><span>ARBITRATE</span><b>→</b><span>GUARDRAILS</span><b>→</b><span>ACT</span><b>→</b><span>RECONCILE</span></div>
    <div className="orchestrator-readout"><span className="eyebrow">Central arbitration</span><strong>{report.orchestratorDecision}</strong><span className="mono">state reconciled · {report.lastReconciledAt}</span></div>
    <div className="agent-list">{report.agents.map((agent) => <div className="agent-row" key={agent.agentId}><div className={`agent-status agent-${agent.status}`}><span /></div><div className="agent-copy"><div><span className="eyebrow">{agent.role}</span><span className="agent-state">{titleCase(agent.status)}</span></div><strong>{agent.recommendation}</strong><span>{agent.objective}</span></div><div className="agent-confidence"><strong>{Math.round(agent.confidence * 100)}%</strong><span>confidence</span></div></div>)}</div>
  </section>;
}
function EventRail({ state }: { state: FarmState }) {
  const active = state.activeTasks ?? [];
  const completed = state.completedTasks ?? [];
  return <section className="event-rail fade-up fade-up-delay-3"><div className="event-column"><div className="rail-heading"><span className="eyebrow">Current queue</span><span className="mono">{active.length}</span></div>{active.length ? active.slice(0, 3).map((task, index) => <div className="task-row" key={task}><span className="task-index mono">0{index + 1}</span><span>{task}</span><span className="task-state active">active</span></div>) : <div className="empty-row">No active tasks in queue.</div>}</div><div className="event-column"><div className="rail-heading"><span className="eyebrow">Recent feedback</span><span className="mono">{completed.length}</span></div><div className="last-event"><div className="event-marker"><Check size={14} /></div><div><span className="eyebrow">Last simulator event</span><p data-testid="text-last-event">{state.lastEvent || 'No events recorded yet.'}</p></div></div></div></section>;
}

function LoadingConsole() {
  return <div className="loading-console"><div className="loading-head skeleton" /><div className="loading-metrics"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div><div className="loading-grid"><div className="skeleton" /><div className="skeleton" /></div></div>;
}

function ErrorConsole({ onRetry }: { onRetry: () => void }) {
  return <main className="error-console"><div className="error-symbol"><AlertTriangle size={28} /></div><span className="eyebrow">Signal lost</span><h1>Could not read the simulator.</h1><p>The farm state endpoint did not respond. The console will stay ready while you reconnect.</p><button className="execute-button small-button" onClick={onRetry} data-testid="button-retry"><RefreshCw size={15} /> Retry connection</button></main>;
}

function Console() {
  const queryClient = useQueryClient();
  const stateQuery = useGetFarmState({ query: { queryKey: getGetFarmStateQueryKey(), refetchInterval: 10000 } });
  const recommendationQuery = useGetFarmRecommendation({ query: { queryKey: getGetFarmRecommendationQueryKey(), refetchInterval: 10000 } });
  const seasonPlanQuery = useGetFarmSeasonPlan({ query: { queryKey: getGetFarmSeasonPlanQueryKey(), refetchInterval: 30000 } });
  const marketDecisionQuery = useGetFarmMarketDecision({ query: { queryKey: getGetFarmMarketDecisionQueryKey(), refetchInterval: 15000 } });
  const agentsReportQuery = useGetFarmAgentsReport({ query: { queryKey: getGetFarmAgentsReportQueryKey(), refetchInterval: 10000 } });
  const healthQuery = useHealthCheck({ query: { queryKey: ['/api/healthz'], refetchInterval: 30000 } });
  const executeAction = useExecuteFarmAction();
  const [selectedTile, setSelectedTile] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ success: boolean; message: string } | null>(null);
  const [autopilot, setAutopilot] = useState(true);
  const state = stateQuery.data;
  const recommendation = recommendationQuery.data;
  const seasonPlan = seasonPlanQuery.data;
  const marketDecision = marketDecisionQuery.data;
  const agentsReport = agentsReportQuery.data;
  const selectedForRecommendation = useMemo(() => {
    if (!state || !recommendation) return selectedTile;
    const selectedIsCompatible = selectedTile && state.tiles.some((tile) => tile.id === selectedTile && isCompatibleTile(tile.status, recommendation.action));
    const compatible = actionNeedsTile(recommendation.action) ? state.tiles.find((tile) => isCompatibleTile(tile.status, recommendation.action)) : undefined;
    return selectedIsCompatible ? selectedTile : compatible?.id ?? null;
  }, [recommendation, selectedTile, state]);

  useEffect(() => {
    if (!autopilot || !recommendation || !state || executeAction.isPending || recommendation.action === "PASS") return;
    const timer = window.setInterval(() => {
      if (executeAction.isPending) return;
      const needsTile = actionNeedsTile(recommendation.action);
      const tile = needsTile ? state.tiles.find((candidate) => isCompatibleTile(candidate.status, recommendation.action)) : null;
      if (needsTile && !tile) return;
      executeAction.mutate({
        data: {
          action: recommendation.action,
          tileId: tile?.id ?? null,
          quantity: recommendation.action === "SELL" || recommendation.action === "PLANT" ? 1 : null,
        },
      }, {
        onSuccess: (result) => {
          queryClient.setQueryData(getGetFarmStateQueryKey(), result.state);
          queryClient.setQueryData(getGetFarmRecommendationQueryKey(), result.recommendation);
          void queryClient.invalidateQueries({ queryKey: getGetFarmAgentsReportQueryKey() });
          setFeedback({ success: result.success, message: `Autopilot: ${result.message}` });
        },
        onError: (error) => setFeedback({ success: false, message: error instanceof Error ? error.message : "Autopilot action rejected." }),
      });
    }, 6500);
    return () => window.clearInterval(timer);
  }, [autopilot, recommendation, state, executeAction.isPending, queryClient]);

  const execute = (action: FarmActionInputAction, tileId: string | null, quantity: number | null) => {
    setFeedback(null);
    executeAction.mutate({ data: { action, tileId, quantity } }, {
      onSuccess: (result) => {
        queryClient.setQueryData(getGetFarmStateQueryKey(), result.state);
        queryClient.setQueryData(getGetFarmRecommendationQueryKey(), result.recommendation);
        setFeedback({ success: result.success, message: result.message });
        setSelectedTile(null);
      },
      onError: (error) => setFeedback({ success: false, message: error instanceof Error ? error.message : 'Action rejected by simulator.' }),
    });
  };

  if (stateQuery.isLoading || recommendationQuery.isLoading || seasonPlanQuery.isLoading || marketDecisionQuery.isLoading || agentsReportQuery.isLoading) return <LoadingConsole />;
  if (stateQuery.isError || recommendationQuery.isError || seasonPlanQuery.isError || marketDecisionQuery.isError || agentsReportQuery.isError || !state || !recommendation || !seasonPlan || !marketDecision || !agentsReport) return <ErrorConsole onRetry={() => { void stateQuery.refetch(); void recommendationQuery.refetch(); void seasonPlanQuery.refetch(); void marketDecisionQuery.refetch(); void agentsReportQuery.refetch(); }} />;

  return <div className="console-content">
    <Header state={state} onRefresh={() => { void stateQuery.refetch(); void recommendationQuery.refetch(); void seasonPlanQuery.refetch(); void marketDecisionQuery.refetch(); void agentsReportQuery.refetch(); }} refreshing={stateQuery.isFetching || recommendationQuery.isFetching || seasonPlanQuery.isFetching || marketDecisionQuery.isFetching || agentsReportQuery.isFetching} />
    <main className="main-content">
      <div className="console-heading fade-up"><div><div className="eyebrow heading-kicker"><span className="pulse" />Autonomous farm loop <StatusPill tone={healthQuery.data?.status === 'ok' ? 'good' : 'warn'}>{healthQuery.data?.status === 'ok' ? 'SIMULATOR NOMINAL' : 'RECONNECTING'}</StatusPill></div><h1>The farm runs itself.</h1><p>Specialist agents observe, negotiate, arbitrate, act, and reconcile continuously.</p></div><div className="turn-counter"><span className="eyebrow">Turns remaining</span><strong>{state.temporal.remainingTurns}</strong><span className="mono">continuous autonomous cycle</span></div></div><div className="autonomy-banner"><div><span className="eyebrow">AUTONOMOUS OPERATING LOOP</span><strong>OBSERVE → REASON → NEGOTIATE → ARBITRATE → ACT → LEARN</strong><span>Human intervention is an explicit override, not the normal workflow.</span></div><button className="autonomy-toggle" onClick={() => setAutopilot((value) => !value)}>{autopilot ? 'AUTOPILOT ACTIVE · PAUSE' : 'AUTOPILOT PAUSED · RESUME'}</button></div>
      <div className="metric-strip fade-up fade-up-delay-1"><Metric label="Land" value={`${number(state.land)} plots`} detail={`${state.tiles.length} coordinates monitored`} icon={Leaf} /><Metric label="Cash on hand" value={money(state.financial.cash)} detail={`${money(state.financial.projectedProfit)} projected profit`} tone="positive" icon={TrendingUp} /><Metric label="Inventory" value={`${number(state.inventory.used)} / ${number(state.inventory.capacity)}`} detail={`${number(state.inventory.capacity - state.inventory.used)} units free`} icon={Package} /></div>
      <div className="primary-grid"><RecommendationPanel recommendation={recommendation} state={state} selectedTile={selectedForRecommendation} setSelectedTile={setSelectedTile} onExecute={execute} isPending={executeAction.isPending} feedback={feedback} autopilot={autopilot} /><FarmMap state={state} selectedTile={selectedForRecommendation} setSelectedTile={setSelectedTile} /></div>
      <div className="context-grid"><FinanceCard state={state} /><MarketCard state={state} decision={marketDecision} /><InventoryCard state={state} /></div>
      <SeasonPlanCard plan={seasonPlan} />
      <AgentCoordinationCard report={agentsReport} />
      <EventRail state={state} />
    </main>
  </div>;
}

function Router() {
  return <ErrorBoundary><Switch><Route path="/" component={Console} /><Route component={NotFound} /></Switch></ErrorBoundary>;
}

function App() {
  return <QueryClientProvider client={queryClient}><Shell /></QueryClientProvider>;
}

function Shell() {
  const healthQuery = useHealthCheck({ query: { queryKey: ['/api/healthz'], refetchInterval: 30000 } });
  return <TooltipProvider><WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}><div className="app-shell noise"><Sidebar health={healthQuery.data?.status} /><Router /></div></WouterRouter><Toaster /></TooltipProvider>;
}

export default App;