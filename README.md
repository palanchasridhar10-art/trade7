# Autonomous 3-Agent Trading System (Indian Markets: NSE / BSE)

An institutional-grade, multi-agent algorithmic trading system engineered specifically for Indian equities and derivatives (NSE / BSE). 

Built on a **zero-trust, safety-first architecture**, where analytical agents can only propose trades, while a non-overridable, **100% deterministic risk engine** controls capital allocation, execution, and emergency halts.

---

## 🎯 About the Performance & Precision Target

> **Important Reality Check**: No trading system can honestly promise a 90–95% raw win rate in live financial markets. Markets are adaptive, noisy, and dynamic. Professional hedge funds achieve long-term outperformance with **50–65% win rates** combined with asymmetric payoff structures (e.g. 2:1 or 3:1 reward-to-risk) and uncompromising risk management.
>
> This architecture achieves **high signal precision on executed trades (65–75%+)** through **selective abstention**: the system sits in cash ~70–85% of the time, only executing when independent fundamental and technical agents reach strong consensus and all hard deterministic risk guardrails pass.

### Realistic Post-Cost Performance Targets
| Metric | Realistic Target (After Indian Taxes & Slippage) |
|---|---|
| **Win Rate** | 50% – 65% |
| **Profit Factor** | > 1.50 |
| **Sharpe Ratio** | > 1.00 |
| **Max Drawdown** | < 10% – 15% (Hard automated stop) |
| **Expectancy per Trade** | Positive after Brokerage, STT, Exchange fees, SEBI charges, GST, and Slippage |
| **Signal Precision** | 65% – 75% (Only when both agents strongly agree) |

---

## 🏛️ System Architecture

```
                                 ┌────────────────────────────┐
                                 │     Scheduler (IST)        │
                                 │ (09:15 - 15:30, NSE Cal.)  │
                                 └─────────────┬──────────────┘
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
             ┌───────────────────┐                           ┌───────────────────┐
             │      AGENT 1      │                           │      AGENT 2      │
             │   Fundamental &   │                           │    Technical &    │
             │  Market-Condition │                           │  Position Sizing  │
             │                   │                           │                   │
             │ • Macro & VIX     │                           │ • EMA, ADX, RSI   │
             │ • 1W/1M Trends    │                           │ • VWAP & Volume   │
             │ • FII/DII Flows   │                           │ • Regime Class.   │
             │ • Company Quality │                           │ • Calibrated Win P│
             │ • Event Veto      │                           │ • Fractional Kelly│
             └─────────┬─────────┘                           └─────────┬─────────┘
                       │                                               │
                       │ FundamentalSignal (JSON)                      │ TechnicalSignal (JSON)
                       └───────────────────────┬───────────────────────┘
                                               ▼
                                 ┌───────────────────────────┐
                                 │    AGENT 3 – Execution    │
                                 │ 1. Consensus Gate (Strict)│
                                 │ 2. Deterministic Risk (0% │
                                 │    LLM bypass, hard caps) │
                                 │ 3. Bracket Order Builder  │
                                 └─────────────┬─────────────┘
                                               ▼
                                 ┌───────────────────────────┐
                                 │   Broker Adapter Layer    │
                                 │ (Paper / Kite / Upstox /  │
                                 │  Angel One / Dhan)        │
                                 └─────────────┬─────────────┘
                                               ▼
                                        NSE / BSE Exchange
```

---

## 🛡️ Deterministic Risk Invariants (Hard Guardrails in Code)

No LLM prompt or analytical agent can ever override the risk engine:
1. **Max Risk Per Trade**: Clamped at 1.0% (hard cap 2.0% of portfolio capital).
2. **Max Open Positions**: 5 simultaneous open positions maximum.
3. **Sector & Stock Exposure**: Capped at 25% max sector exposure, 10% max single-stock exposure.
4. **Daily Portfolio Loss Limit**: If realized + unrealized daily loss reaches **2.0%**, the system halts trading for the rest of the session.
5. **Weekly Portfolio Loss Limit**: If weekly loss reaches **5.0%**, trading halts pending manual operator review.
6. **Execution Window**: Algorithmic trades only permitted between **09:30 and 15:00 IST** (bypassing opening/closing volatility).
7. **Cost Hurdle Check**: Expected gross trade profit must exceed at least **3.0x** the estimated Indian statutory round-trip charges.
8. **Intraday MIS Auto-Squareoff**: Mandatory automated market square-off of intraday positions by **15:15 IST**.

---

## 🇮🇳 Indian Statutory Charges & Friction Model

The execution and paper-trading modules incorporate all regulatory Indian costs:
- **Brokerage**: ₹20 / executed order or 0.03% (whichever is lower).
- **Securities Transaction Tax (STT)**: 0.025% on intraday sell turnover; 0.1% on delivery (both sides).
- **Exchange Turnover Fees**: NSE: 0.00297%, BSE: 0.00375%.
- **SEBI Turnover Charges**: ₹10 per crore (0.0001%).
- **Stamp Duty**: 0.003% on intraday buy, 0.015% on delivery buy.
- **GST**: 18% on (Brokerage + Exchange Fees + SEBI Fees).
- **Slippage Simulation**: 0.08% buffer applied to entry and exit fills.

---

## 📂 Project Structure

```
autonomous_trading_system/
├── config/
│   ├── settings.yaml          # Watchlist, scheduling, agent weights & thresholds
│   └── risk_limits.yaml       # Non-negotiable risk engine invariants
├── docs/
│   ├── architecture.md        # System architecture and data flow
│   ├── design.md              # Component design & mathematical specs
│   ├── task.md                # 8-Phase implementation roadmap
│   └── memory.md              # Episodic SQL memory and learning loop design
├── src/
│   ├── core/
│   │   ├── constants.py       # Enums (OrderSide, SignalDirection, ProductType, etc.)
│   │   └── models.py          # Typed Pydantic models for contracts
│   ├── data/
│   │   ├── calendar.py        # NSE IST hours, holidays, and execution windows
│   │   └── feed.py            # OHLCV, macro context, fundamentals, quality checks
│   ├── agents/
│   │   ├── agent1_fundamental.py  # Macro, flows, 1W/1M trend, quality & event filter
│   │   ├── agent2_technical.py    # Confluence indicators, regime, Kelly sizing
│   │   └── agent3_execution.py    # Consensus gate, proposal builder, lifecycle
│   ├── risk/
│   │   └── engine.py          # Deterministic Risk Engine (Zero LLM bypass)
│   ├── broker/
│   │   ├── base.py            # Abstract BrokerAdapter interface
│   │   └── paper.py           # Paper trading with Indian statutory costs & slippage
│   ├── memory/
│   │   └── journal.py         # SQLite episodic trade journal and performance metrics
│   └── orchestrator/
│       └── pipeline.py        # Parallel agent coordinator & decision cycle
├── tests/
│   ├── test_consensus_gate.py # Validates strict consensus and abstention
│   ├── test_risk_engine.py    # Validates daily loss, position, exposure & kill switch
│   ├── test_kelly_sizing.py   # Validates fractional Kelly formula and caps
│   └── test_paper_trading.py  # Validates simulated execution and cost deduction
├── main.py                    # Demonstration script running full decision cycle
├── pyproject.toml             # Project build configuration
└── requirements.txt           # Core Python dependencies
```

---

## 🚀 Getting Started

### 1. Installation

Using `uv` (recommended) or standard Python 3.11+:

```powershell
cd C:\Users\palan\.gemini\antigravity-ide\scratch\autonomous_trading_system
uv pip install -r requirements.txt
```

### 2. Run the Automated Test Suite

```powershell
uv run pytest -v
```

### 3. Run the End-to-End Paper Trading Demonstration

```powershell
uv run python main.py
```

---

## ⚖️ Legal & SEBI Regulatory Compliance Notice

*Not financial advice. Algorithmic trading carries risk of substantial loss. In India, algorithmic trading via broker APIs is subject to SEBI circulars and exchange regulations (broker-level algo approval, API tagging, rate limits, and static IP requirements). Always validate strategies in paper trading for at least 2–3 months before deploying live capital.*
