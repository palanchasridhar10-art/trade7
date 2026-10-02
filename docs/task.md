# Tasks & Implementation Roadmap: Autonomous 3-Agent Trading System

Legend: `[ ]` todo · `[~]` in progress · `[x]` done.  
*Rule: Complete each phase's exit criteria before advancing to live execution.*

---

## Phase 0: Setup, Contracts & Compliance (Week 1)
- [x] Create project repository structure and documentation (`architecture.md`, `design.md`, `task.md`, `memory.md`)
- [x] Define typed Pydantic signal schemas (`FundamentalSignal`, `TechnicalSignal`, `ConsensusResult`, `TradeProposal`, `RiskVerdict`)
- [x] Specify non-overridable deterministic risk engine parameters
- [ ] Select primary broker adapter target (Zerodha Kite Connect, Upstox, Angel One SmartAPI, Dhan, or Fyers)
- [ ] Verify broker API retail algo registration requirements and static IP prerequisites
- [ ] Initialize Python environment, configuration templates (`settings.yaml`, `risk_limits.yaml`), and CI test runner
- [ ] Define initial liquid Nifty 50 + Bank Nifty watchlist

**Exit Criteria**: Local mock/paper test passes; typed contracts and risk limits committed.

---

## Phase 1: Data Layer (Weeks 1–3)
- [ ] Historical OHLCV ingestion (1-min, 5-min, 15-min, Daily) with split/bonus adjustments
- [ ] Real-time broker WebSocket tick/quote feed with auto-reconnection
- [ ] Fundamental data ingestion (Screener, corporate filings, balance sheets)
- [ ] Macro feeds: India VIX, FII/DII net flows, sector index levels, USD-INR, Brent crude
- [ ] News & regulatory filings stream with deduplication and source verification
- [ ] IST NSE trading calendar, pre-open session (09:00-09:15), market hours (09:15-15:30), and official holidays
- [ ] Automated data quality validator (detecting gaps, zero-volume spikes, latency, and staleness)

**Exit Criteria**: Clean reproducible historical dataset; automated data-quality report passes with zero unexplained gaps.

---

## Phase 2: Agent 1 – Fundamental & Market-Condition Analyst (Weeks 3–5)
- [ ] Implement Market Regime Scorer (incorporating 1-week and 1-month trend, breadth, and VIX)
- [ ] Implement Sector Relative Strength matrix (outperformance vs Nifty benchmark over 1W/1M)
- [ ] Implement Company Quality Score (growth, margins, debt/equity, promoter holding & pledge)
- [ ] Implement Event-Risk Filter (hard veto on earnings within 24h, F&O ban list, ASM/GSM categories)
- [ ] Implement LLM News & Filings Sentiment Classifier with strict Pydantic output and citations
- [ ] Standalone unit tests and edge validation

**Exit Criteria**: Standalone backtest confirms Agent 1 provides measurable directional filter or risk-reduction edge out-of-sample.

---

## Phase 3: Agent 2 – Technical Analyst + Kelly Sizing (Weeks 4–7)
- [ ] Technical indicator engine (EMA 20/50/200, Supertrend, ADX, RSI, MACD, Bollinger Bands, ATR, VWAP)
- [ ] Regime Detector (Trending, Ranging, High Volatility)
- [ ] Multi-timeframe confluence scoring (Daily bias + 15m/5m execution trigger)
- [ ] Walk-forward parameter optimization on train/validation splits
- [ ] Probability Calibration Engine (Isotonic regression / Platt scaling mapping score to empirical win rate)
- [ ] Fractional Kelly Sizing Module (Quarter-Kelly, hard portfolio risk caps, and NSE lot size rounding)

**Exit Criteria**: Statistically positive expectancy after all statutory costs and slippage in walk-forward evaluation.

---

## Phase 4: Agent 3 – Execution Agent & Deterministic Risk Engine (Weeks 6–9)
- [ ] Consensus Gate: strict directional agreement, threshold confidence, and positive expectancy requirement
- [ ] Deterministic Risk Engine: portfolio loss limits (daily 2%, weekly 5%), max open positions (5), sector caps (25%)
- [ ] Emergency Kill Switch (automated triggers on data staleness, API error clusters, anomaly PnL)
- [ ] Abstract `BrokerAdapter` interface + `PaperBroker` simulator with complete Indian statutory charges
- [ ] Order State Machine (`CREATED` $\rightarrow$ `SUBMITTED` $\rightarrow$ `FILLED` $\rightarrow$ `CLOSED`) with idempotent retries
- [ ] Dynamic trailing stop loss (ATR Chandelier exit) and mandatory 15:15 IST intraday MIS square-off
- [ ] Failure injection tests: network dropped, broker API down, partial fill, stale feed

**Exit Criteria**: 100% deterministic test coverage on risk rules; paper broker reproduces true execution constraints.

---

## Phase 5: Integration & Full Backtesting (Weeks 9–11)
- [ ] Orchestrator pipeline connecting scheduler $\rightarrow$ parallel agents $\rightarrow$ Agent 3 $\rightarrow$ risk $\rightarrow$ broker
- [ ] 5+ year historical multi-regime backtest (including 2020 COVID crash, 2021 bull run, 2022-2023 consolidation)
- [ ] Realistic Monte Carlo simulation and slippage stress-testing
- [ ] Final out-of-sample holdout validation
- [ ] Benchmark report generation: Win rate, Profit Factor (>1.5), Sharpe (>1.0), Max Drawdown (<10-15%)

**Exit Criteria**: Full system meets target metrics on unseen out-of-sample data with conservative cost modeling.

---

## Phase 6: Live Paper Trading (Weeks 11–24)
- [ ] Deploy continuous paper-trading pipeline during active IST market hours (09:15-15:30) for 2–3 months
- [ ] Real-time logging of all signals, consensus checks, and vetoes
- [ ] Daily reconciliation dashboard: simulated slippage vs live bid/ask spreads
- [ ] Model stability and calibration drift monitoring

**Exit Criteria**: Paper trading metrics remain within 10% tolerance of backtested expectations over ≥ 60 trading sessions.

---

## Phase 7: Small-Capital Live Deployment (Months 6–9)
- [ ] Live deployment with $\le 5\%$ of allocated capital
- [ ] Ultra-conservative parameters: 0.25x Kelly fraction, 0.5% max risk per trade
- [ ] Real-time automated Telegram / Email alerts on order placement, fill, and risk events
- [ ] Automated tax and P&L export (speculative intraday vs non-speculative F&O)

**Exit Criteria**: 3 consecutive profitable or stable months with zero risk-limit breaches.

---

## Phase 8: Scaling & Controlled Self-Learning (Ongoing)
- [ ] Controlled step-up in allocated capital
- [ ] Quarterly walk-forward parameter re-validation
- [ ] Episodic learning loop updates (see `memory.md`) requiring strict human approval for changes
- [ ] Expansion to defined-risk F&O multi-leg strategies (e.g. Bull Put / Bear Call spreads)

---

## Definition of Done (Per Feature)
1. Unit + integration tests passing with 90%+ branch coverage on risk-critical logic.
2. Comprehensive structured JSON logging with unique correlation ID per decision cycle.
3. Fully configuration-driven (zero magic constants or hardcoded thresholds).
4. Failure modes analyzed, documented, and safeguarded.
