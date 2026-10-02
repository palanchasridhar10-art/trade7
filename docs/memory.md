# Memory System Architecture: Autonomous 3-Agent Trading System

This document outlines the dual-layer memory architecture:
1. **Runtime Memory**: Operational state, trade journal, regime records, and probability calibration.
2. **Project Working Memory**: Developer and agent context, decision logs, open questions, and conventions.

---

## Part A: System Runtime Memory

### 1. Memory Layers
| Layer | Contents | Storage Technology | Retention |
|---|---|---|---|
| **Short-Term (Session)** | Today's signals, active orders, live positions, intraday PnL, risk utilization | Fast In-Memory cache (Dict / Redis) | Daily session |
| **Trade Journal (Episodic)** | Complete decision traces: inputs, Agent 1 & 2 signals, consensus outcomes, orders, fills, slippage, PnL | SQLite (local/dev) / PostgreSQL (prod) | Permanent |
| **Regime Memory** | Daily market regime labels (Trending, Ranging, High-Vol), historical breadth, strategy performance per regime | Database tables | Permanent |
| **Semantic Knowledge Base** | Validated empirical insights ("Breakouts on results day have 32% lower expectancy") | DB + Vector store (pgvector / Chroma) | Versioned |
| **Calibration Memory** | Historical (score $\rightarrow$ trade outcome) pairs for isotonic probability calibration & Kelly $(p, b)$ parameters | DB table | Rolling 90-day window |
| **Config & Parameters** | Exact historical parameter sets, model weights, validation evidence, deployment logs | Git + DB | Permanent |

---

### 2. Core Trade Journal Schema (SQL)

```sql
-- Record of every evaluation cycle (both traded and vetoed)
CREATE TABLE IF NOT EXISTS decisions (
    id UUID PRIMARY KEY,
    cycle_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL DEFAULT 'NSE',
    fund_signal JSONB NOT NULL,
    tech_signal JSONB NOT NULL,
    consensus BOOLEAN NOT NULL,
    risk_check JSONB NOT NULL,
    action TEXT NOT NULL, -- 'TRADE' or 'NO_TRADE'
    reason TEXT NOT NULL
);

-- Record of executed trades and their financial lifecycle
CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY,
    decision_id UUID REFERENCES decisions(id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL, -- 'BUY' or 'SELL'
    quantity INT NOT NULL,
    entry_price NUMERIC(12, 4) NOT NULL,
    stop_price NUMERIC(12, 4) NOT NULL,
    target_price NUMERIC(12, 4) NOT NULL,
    exit_price NUMERIC(12, 4),
    exit_reason TEXT, -- 'TARGET', 'STOP_LOSS', 'TRAILING_STOP', 'EOD_MIS', 'KILL_SWITCH'
    gross_pnl NUMERIC(12, 4),
    net_pnl NUMERIC(12, 4),
    fees_and_taxes NUMERIC(12, 4),
    slippage NUMERIC(12, 4),
    r_multiple NUMERIC(6, 2),
    kelly_fraction NUMERIC(6, 4),
    win_prob_est NUMERIC(6, 4),
    opened_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ
);

-- Market regime tracking per trading session
CREATE TABLE IF NOT EXISTS regimes (
    date DATE PRIMARY KEY,
    index_symbol TEXT NOT NULL,
    trend_state TEXT NOT NULL,       -- 'TRENDING_UP', 'TRENDING_DOWN', 'RANGING'
    volatility_state TEXT NOT NULL,  -- 'LOW', 'NORMAL', 'HIGH_VIX'
    india_vix NUMERIC(6, 2) NOT NULL,
    market_breadth NUMERIC(6, 2),
    fii_net_flow_cr NUMERIC(12, 2),
    dii_net_flow_cr NUMERIC(12, 2),
    label TEXT NOT NULL
);
```

---

### 3. Controlled Learning Loop
The system incorporates an institutional feedback loop with strict human guardrails:
1. **Nightly EOD Reconcile**: Ingest all trade fills, calculate exact slippage vs limit prices, compute R-multiples, and verify zero discrepancies with broker account statements.
2. **Weekly Calibration Update**: Refit isotonic regression models on the rolling out-of-sample window to update probability curves with conservative shrinkage.
3. **Monthly LLM Post-Mortem**: Automated analysis summarizing loss clusters, false breakouts, and macro anomalies into candidate hypotheses.
4. **Quarterly Walk-Forward Validation**: Re-optimize indicator weights and Kelly multipliers across historical walk-forward slices.
5. **Strict Governance Gate**: **No autonomous self-modification of risk limits or core logic.** All proposed parameter updates generate a pull request with backtest proof and require explicit human operator sign-off before entering production.

---

## Part B: Project Working Memory (For Developers & AI Agents)

### 1. Project Summary
- **Target Market**: Indian Equities (NSE/BSE) cash & F&O segments.
- **Architecture**: 3-Agent Autonomous System:
  - Agent 1: Fundamental, Macro & Sentiment (1W/1M context).
  - Agent 2: Technical Confluence & Fractional Kelly Position Sizing.
  - Agent 3: Consensus Gating, Deterministic Risk Engine & Broker Execution.
- **Accuracy Philosophy**: Reframed as **high signal precision on executed trades** through strict abstention and confluence gating, not a deceptive 90–95% raw win rate.

### 2. Key Decisions Log
| # | Decision | Rationale |
|---|---|---|
| **1** | Risk Engine is 100% deterministic code (No LLM bypass) | Absolute safety; eliminates prompt injection or hallucination risk. |
| **2** | Parallel and independent analysis for Agents 1 & 2 | Eliminates anchoring bias and confirmation loops. |
| **3** | Fractional Kelly (0.25x) capped at 1–2% portfolio risk | Shields against estimation error in win rate and payoff skew. |
| **4** | Initial universe restricted to liquid Nifty 50 / Bank Nifty | Guarantees tight bid-ask spreads and minimal market impact. |
| **5** | Staged roll-out: Backtest $\rightarrow$ Paper (3 mo) $\rightarrow$ Small Live (5% cap) | Real-world validation before risking substantial capital. |
| **6** | LLM restricted to news/sentiment text processing | Auditability and zero non-deterministic mathematical calculations. |
| **7** | Human operator approval mandatory for model updates | Eliminates uncontrolled model degradation or regime drift. |

### 3. Key Open Questions for Implementation
1. **Target Broker API**: Zerodha Kite Connect, Upstox, Angel One SmartAPI, Dhan, or Fyers?
2. **Trading Horizon**: Intraday (MIS - squared off by 15:15 IST) vs Swing (CNC/NRML held for days/weeks)?
3. **Market Segment**: Cash equity only vs Equity Futures & Options?
4. **Initial Capital & Risk Budget**: Total allocation and maximum daily/weekly loss thresholds?
5. **Data Feeds**: Free exchange/vendor feeds vs real-time broker WebSocket streams?
6. **Infrastructure**: Local developer machine vs cloud VPS in Mumbai (AWS `ap-south-1` / GCP `asia-south1`) with static IP?

### 4. Technical Conventions
- **Language**: Python 3.11+, full type annotations, Pydantic v2 schemas for all signals.
- **Timezone**: Explicit `Asia/Kolkata` (IST) awareness on all market timers and data timestamps; UTC stored in database.
- **Config**: YAML-driven configuration (`settings.yaml`, `risk_limits.yaml`), secrets loaded via environment variables (never committed).
- **Testing**: Deterministic unit tests for risk engine, consensus gate, Kelly sizing, and paper execution.
