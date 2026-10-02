# Architecture: Autonomous 3-Agent Trading System (Indian Markets: NSE / BSE)

## 1. Goals
- **Fully autonomous pipeline**: data → analysis → decision → execution → learning.
- **Three specialized agents** with strict separation of duties.
- **Safety first**: deterministic risk engine that no AI/LLM agent can override.
- **Broker-agnostic execution layer** for Indian brokers (Zerodha Kite, Upstox, Angel One, Dhan, Fyers, etc.).
- **Full auditability**: every decision stored with reasoning, confidence, features, and raw inputs.

## 2. Realistic Performance Target
- **Win rate**: 50–65% (realistic post-cost expectation).
- **Profit factor**: > 1.5.
- **Sharpe ratio**: > 1.0.
- **Max drawdown**: < 10–15% (hard stop at limit).
- **Expectancy per trade**: Positive after brokerage, STT, exchange fees, SEBI charges, stamp duty, GST, and slippage.
- **Signal precision**: 65–75% on high-conviction executed trades through selective abstention.

---

## 3. High-Level Architecture Diagram

```
┌────────────────────────────────────────────────────────┐
│                      Scheduler                         │
│             (Market hours, IST, NSE holidays)          │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
    ┌───────────────────┐       ┌───────────────────┐
    │     AGENT 1       │       │      AGENT 2      │
    │   Fundamental &   │       │    Technical &    │
    │  Market-Context   │       │  Position Sizing  │
    │                   │       │                   │
    │ • Macro / sector  │       │ • Indicators      │
    │ • News & sentiment│       │ • Regime detection│
    │ • FII/DII flows   │       │ • Signal scoring  │
    │ • 1W/1M context   │       │ • Kelly sizing    │
    └─────────┬─────────┘       └─────────┬─────────┘
              │                           │
              │ FundamentalSignal (JSON)  │ TechnicalSignal (JSON)
              └─────────────┬─────────────┘
                            ▼
              ┌───────────────────────────┐
              │    AGENT 3 – Execution    │
              │ 1. Consensus gate         │
              │ 2. Risk Engine (Hard)     │
              │ 3. Order construction     │
              │ 4. Order management       │
              └─────────────┬─────────────┘
                            ▼
              ┌───────────────────────────┐
              │   Broker Adapter Layer    │
              │ (Zerodha Kite / Upstox /  │
              │  Angel One / Dhan / Paper)│
              └─────────────┬─────────────┘
                            ▼
                     NSE / BSE Exchange
┌────────────────────────────────────────────────────────┐
│ Shared Layers: Data Layer · Memory Store · Logging ·   │
│ Monitoring & Alerts · Backtest/Paper Engine            │
└────────────────────────────────────────────────────────┘
```

---

## 4. Components

| Component | Responsibility | Tech Stack |
|---|---|---|
| **Scheduler** | Runs agents on IST market calendar (09:15–15:30), handles NSE holidays, pre/post-market jobs | Python, APScheduler / Cron |
| **Data Layer** | Market data, fundamentals, news, FII/DII flows, corporate actions | Broker WebSocket, NSE/BSE feeds, vendor APIs |
| **Agent 1** | Fundamental + market-condition analysis (1W/1M context) | Python + LLM for text analysis + quant scoring |
| **Agent 2** | Technical analysis + Kelly criterion sizing | Python (pandas, numpy, scipy, TA-Lib / pandas-ta) |
| **Agent 3** | Consensus gate, trade proposal builder, order management | Python, broker SDK |
| **Risk Engine** | Deterministic limits, exposure caps, and emergency kill switch | Plain deterministic code (No LLM bypass) |
| **Memory Store** | Trade journal, episodic memory, regime history, lessons learned | SQLite / PostgreSQL + JSONB |
| **Backtest / Paper Engine** | Validation before live deployment with Indian cost model | Custom vector / event-driven engine |
| **Monitoring** | Alerts, health checks, daily PnL & risk reports | Structured logging, Telegram / Email alerts |

---

## 5. Data Flow (Per Decision Cycle)
1. **Trigger**: Scheduler triggers cycle for each symbol in the active watchlist during allowed IST market hours (09:30–15:00 IST).
2. **Parallel Analysis**: Agent 1 and Agent 2 run concurrently and independently (no peeking to prevent anchoring bias).
3. **Structured Emission**: Each emits a typed JSON signal with direction, confidence, features, and rationale.
4. **Consensus Gate**: Agent 3 evaluates directional agreement and threshold convictions. If consensus fails, returns `NO_TRADE` and logs reason.
5. **Deterministic Risk Check**: Agent 3 computes proposed quantity from Agent 2's Kelly sizing, then submits proposal to the `RiskEngine`. The Risk Engine can validate, downsize, or veto.
6. **Execution**: If approved, Agent 3 constructs bracketed orders (Entry + Stop Loss + Target) and sends via `BrokerAdapter`.
7. **Audit & Journaling**: Order lifecycle, fills, slippage, and resulting PnL are recorded to persistent memory.
8. **End of Day (EOD)**: Square off intraday MIS positions before 15:15 IST, generate reconciliation reports, update calibration memory.

---

## 6. Key Architectural Principles
- **Separation of Concerns**: Analysts recommend; only Agent 3 and Risk Engine touch money.
- **Hard Guardrails in Code**: Position limits, sector exposure caps, daily loss limit, and kill switch are 100% deterministic code.
- **Zero Inter-agent Anchoring**: Agent 1 and Agent 2 share no intermediate thoughts before signal emission.
- **Fail-Safe Operation**: Any data outage, latency spike, or feed anomaly triggers a stand-aside mode.
- **Idempotent Order Management**: Every order carries a unique client ID; automated retries follow strict idempotency guarantees.
- **Staged Progression**: Backtest → Paper Trading (2–3 months) → Small Live (≤ 5% capital) → Scale.
