// Shared, engine-shaped fixtures for the selector test suites. Every builder
// returns a FRESH deep structure on each call so a test that mutates its input
// can never leak into another test. Field names mirror the real backend
// payloads (committee_cycle_evaluations feed, /dashboard/v2, and
// /institutional-report/{ticker}) — no toy shapes.

// --- committee_cycle_evaluations feed (Recommendation Explorer / Research
// Memory). Newest cycle first, as the backend returns it. AAPL walks
// BUY → BUY → HOLD → AVOID with a confidence rise then two falls; MSFT is a
// single BUY expressed on the 0–100 scale; NVDA is an honest NOT_EVALUATED row
// (no action / confidence) to prove nothing is fabricated.
export function committeeCycles() {
  return [
    {
      cycle_id: 'c4',
      run_id: 4,
      evaluated_at: '2026-07-14T12:00:00',
      duration_seconds: 1.2,
      evaluations: [
        { ticker: 'AAPL', action: 'AVOID', status: 'EVALUATED', strength: 'Weak', agreement_pct: 55, confidence: 0.4 },
        { ticker: 'MSFT', action: 'BUY', status: 'EVALUATED', strength: 'Strong', agreement_pct: 90, confidence: 88 },
      ],
    },
    {
      cycle_id: 'c3',
      run_id: 3,
      evaluated_at: '2026-07-10T12:00:00',
      duration_seconds: 1.1,
      evaluations: [
        { ticker: 'AAPL', action: 'HOLD', status: 'EVALUATED', strength: 'Moderate', agreement_pct: 62, confidence: 0.61 },
      ],
    },
    {
      cycle_id: 'c2',
      run_id: 2,
      evaluated_at: '2026-07-05T12:00:00',
      duration_seconds: 1.0,
      evaluations: [
        { ticker: 'AAPL', action: 'BUY', status: 'EVALUATED', strength: 'Strong', agreement_pct: 80, confidence: 0.75 },
      ],
    },
    {
      cycle_id: 'c1',
      run_id: 1,
      evaluated_at: '2026-07-01T12:00:00',
      duration_seconds: 0.9,
      evaluations: [
        { ticker: 'AAPL', action: 'BUY', status: 'EVALUATED', strength: 'Moderate', agreement_pct: 70, confidence: 0.5 },
        // Honest not-evaluated row: no action, no confidence.
        { ticker: 'NVDA', status: 'NOT_EVALUATED' },
      ],
    },
  ]
}

// Paper-fund slice used by the Explorer's executionStatus(): AAPL is an
// executed simulated position carrying an unrealized return; MSFT is a
// recommendation-only ticker (no position, no order).
export function paperFundForExecution() {
  return {
    open_positions: {
      AAPL: { quantity: 50, current_price: 180, cost_basis: 150, unrealized_return_pct: 20 },
    },
    virtual_orders: [{ order_id: 'o-aapl', ticker: 'AAPL', side: 'BUY', quantity: 50, filled_at: '2026-07-05T12:01:00' }],
  }
}

// --- /dashboard/v2 payload (Portfolio Intelligence / Executive Briefing /
// Mission Control). A single coherent RUNNING autonomous-paper snapshot.
export function dashboardV2() {
  return {
    generated_at: '2026-07-14T15:30:05',
    version: 'dashboard-v2',
    operations: {
      operational_mode: { mode: 'AUTONOMOUS_PAPER', paper_only: true },
      warnings: [],
      recent_errors: [],
      database: { status: 'EVALUATED', exists: true, table_count: 20, total_rows: 100 },
      learning: {
        status: 'EVALUATED',
        learning_active: true,
        learning_entries: 5,
        latest_lesson: 'Rebalanced tech exposure',
        latest_learning_at: '2026-07-14T15:00:00',
      },
    },
    reliability: {
      overall_reliability: { grade: 'A', score: 92, status: 'EVALUATED' },
      confidence: { level: 'HIGH', coverage: 0.8, history_available: true },
      reliability_trend: { direction: 'stable' },
      warning_count: 1,
      error_count: 0,
      critical_count: 0,
      recent_incidents: [],
    },
    market: {
      status: 'EVALUATED',
      market_is_open: true,
      market_session: 'regular',
      active_provider: 'yahoo',
      healthy: true,
      fallback_used: false,
    },
    scheduler: {
      status: 'EVALUATED',
      running: true,
      enabled: true,
      tick_count: 12,
      last_tick_at: '2026-07-14T15:25:00',
      last_status: 'OK',
      last_reason: null,
      error_count: 0,
    },
    performance: {
      realized_vs_unrealized: { status: 'EVALUATED', realized_pl: 250, unrealized_pl: 800 },
      symbol_contribution: {
        status: 'EVALUATED',
        best: { symbol: 'AAPL', unrealized_pl: 1500, contribution_to_portfolio_percent: 7.5 },
        worst: { symbol: 'MSFT', unrealized_pl: 300, contribution_to_portfolio_percent: 1.5 },
      },
      sector_contribution: { items: [{ sector: 'Technology', contribution_to_portfolio_percent: 9.0 }] },
      portfolio_return_drivers: {
        drivers: [
          { symbol: 'AAPL', value: 1500 },
          { symbol: 'MSFT', value: -200 },
        ],
      },
      cash_drag: { status: 'EVALUATED', cash_pl_contribution: -12, cash_weight_percent: 25 },
    },
    portfolio: {
      portfolio_status: { last_update: '2026-07-14T15:30:00' },
      portfolio_health_score: { status: 'EVALUATED', score: 82 },
      cash_reserve_status: { status: 'EVALUATED', cash_percent: 25 },
      largest_position_concentration: { status: 'EVALUATED', concentration_percent: 45, symbol: 'AAPL', current_value: 9000 },
      sector_exposure_summary: {
        items: [
          { sector: 'Technology', exposure_percent: 60 },
          { sector: 'Cash', exposure_percent: 25 },
        ],
        largest_sector: 'Technology',
      },
      risk_utilization: {
        status: 'EVALUATED',
        decision_count: 10,
        rejected_decisions: 2,
        by_rule: [{ rule: 'max_position' }, { rule: 'sector_cap' }],
      },
    },
    research_cycle: {
      status: 'EVALUATED',
      enabled: true,
      research_due: false,
      last_recommendation_run_time: '2026-07-14T09:00:00',
      stages: [
        { stage: 'research_generation', status: 'COMPLETED', at: '2026-07-14T09:00:00', duration_seconds: 2.0, details: { recommendation_count: 3 } },
        {
          stage: 'committee_evaluation',
          status: 'COMPLETED',
          at: '2026-07-14T09:05:00',
          duration_seconds: 3.0,
          details: {
            evaluations: [
              { ticker: 'AAPL', action: 'BUY', strength: 'Strong', agreement_pct: 90, confidence: 0.88, status: 'EVALUATED', reason: 'Momentum + earnings' },
              { ticker: 'MSFT', action: 'HOLD', strength: 'Moderate', agreement_pct: 60, confidence: 0.55, status: 'EVALUATED' },
              { ticker: 'NVDA', action: 'AVOID', strength: 'Weak', agreement_pct: 50, confidence: 0.4, status: 'EVALUATED' },
            ],
          },
        },
      ],
    },
    paper_fund: {
      fund_status: 'RUNNING',
      price_provider: 'yahoo',
      cash: 5000,
      realized_pl: 250,
      last_update: '2026-07-14T15:30:00',
      next_update: '2026-07-14T15:35:00',
      interval_minutes: 5,
      latest_snapshot: {
        cash: 5000,
        current_value: 15000,
        portfolio_value: 20000,
        total_return: 12.5,
        daily_return: 1.2,
        as_of: '2026-07-14T15:30:00',
      },
      open_positions: {
        AAPL: { quantity: 50, current_value: 9000, current_price: 180, cost_basis: 150 },
        MSFT: { quantity: 15, current_value: 6000, current_price: 400, cost_basis: 380 },
      },
      virtual_orders: [
        { order_id: 'o1', side: 'BUY', ticker: 'AAPL', quantity: 10, filled_at: '2026-07-14T15:30:00' },
      ],
      activity_log: [
        { activity_type: 'ORDERS_FILLED', message: 'Filled 1 order', at: '2026-07-14T15:30:00' },
        { activity_type: 'COMMITTEE_EVALUATED', message: 'Committee done', at: '2026-07-14T09:05:00' },
        { activity_type: 'RECOMMENDATIONS_GENERATED', message: '3 recommendations', at: '2026-07-14T09:00:00' },
        { activity_type: 'CYCLE_STARTED', message: 'Cycle start', at: '2026-07-14T08:59:00' },
      ],
    },
    learning: {},
  }
}

// --- /institutional-report/{ticker} payload. Section-keyed, exactly as the
// report engine emits it. Includes deliberate engine "unavailable" defaults
// (empty string, 0, 'Unavailable') that the selector must fold into honest
// not-evaluated states.
export function institutionalReportPayload() {
  return {
    ticker: 'AAPL',
    metadata: {
      generation_time: '2026-07-14T09:05:00',
      report_version: 'ir-v1',
      data_sources_used: ['market', 'sec', 'committee'],
      active_providers: ['yahoo', 'edgar'],
    },
    policy: { deterministic: true, uses_llm: false, read_only: true },
    sections: [
      { title: 'Executive Summary', summary: 'AAPL shows durable momentum.', data: { action: 'BUY', confidence: 88, sec_filings: 3 } },
      { title: 'Recommendation', data: { action: 'BUY', rating: 'Strong Buy', overall_score: 82, validation_status: 'VALIDATED' } },
      { title: 'Confidence', summary: 'High conviction.', data: { confidence: 88, signal_label: 'STRONG', signal_quality_score: 74 } },
      {
        title: 'Investment Committee',
        summary: 'Committee broadly bullish.',
        data: {
          agreement: 90,
          bullish_members: [{ member_name: 'Growth Analyst' }, { member_name: 'Momentum Analyst' }],
          bearish_members: [{ member_name: 'Value Analyst' }],
          neutral_members: [],
        },
      },
      { title: 'Risk Assessment', data: { risk_score: 35, risks: ['Valuation stretched'], false_positive_warnings: [] } },
      { title: 'Technical Analysis', data: { technical_score: 70, score: 66 } },
      { title: 'Forecast Analysis', data: { forecast_direction: 'UP', forecast_confidence: 60, expected_change: 4.2 } },
      { title: 'Fundamental Analysis', data: { fundamental_score: 71, strongest_positive_factor: 'Cash flow' } },
      { title: 'SEC Highlights', data: { filing_count: 3, form_type_counts: { '10-K': 1, '8-K': 2 }, section_coverage: ['MD&A', 'Risk Factors'] } },
      // Portfolio Impact left at engine defaults → must degrade to not-evaluated.
      { title: 'Portfolio Impact', summary: 'Unavailable', data: { portfolio_score: 0, overall_conviction: 0 } },
      { title: 'Bull Case', data: ['Services margin expansion', 'Buybacks'] },
      { title: 'Bear Case', data: ['Hardware cyclicality'] },
      { title: 'Catalyst Timeline', data: [{ title: 'Earnings', date: '2026-07-31' }] },
      { title: 'Appendix', data: { sec_provider: 'edgar', evidence_breakdown: ['Technical: 40%', 'Fundamental: 35%'] } },
    ],
  }
}

// Card the user clicked to open the drawer (always present, enriches the header).
export function reportCard() {
  return { ticker: 'AAPL', action: 'BUY', confidence: 0.88, agreementPct: 90, strength: 'Strong' }
}
