# Design Specification: Autonomous 3-Agent Trading System

## 1. Common Signal Contract
All analytical agents emit typed, schema-validated JSON structures.

```json
{
  "agent": "fundamental | technical",
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "timestamp": "2026-10-02T10:15:00+05:30",
  "direction": "LONG | SHORT | NEUTRAL",
  "confidence": 0.72,
  "horizon": "intraday | swing | positional",
  "rationale": [
    "Nifty energy sector outperforming benchmark over 1W and 1M",
    "FII net buyers in energy basket over rolling 5-day window",
    "Positive earnings surprise with expanding operating margins"
  ],
  "features": {
    "market_regime_score": 68.5,
    "sector_relative_strength": 1.15,
    "company_quality_score": 74.0,
    "news_sentiment_score": 0.65
  }
}
```

Agent 2 (Technical & Kelly) augments this payload with actionable trade parameters:
```json
{
  "entry": 2850.50,
  "stop_loss": 2815.00,
  "target": 2921.50,
  "win_prob": 0.62,
  "payoff_ratio": 2.00,
  "kelly_fraction": 0.052,
  "suggested_position_value": 75000.0
}
```

---

## 2. Agent 1: Fundamental & Market-Condition Analyst
**Purpose**: Assess macro, sector, flows, and corporate conditions using current data plus 1-week and 1-month historical trend context.

### 2.1 Input Data Categories
- **Index Context**: Nifty 50, Bank Nifty, Sector Indices, India VIX, Market Advance/Decline ratio.
- **Trend Context**: 1-week & 1-month percentage returns, realized volatility, market breadth, and distance from 20/50/200 DMA.
- **Institutional Flows**: Daily and 5-day / 20-day rolling net FII and DII flows.
- **Macro Factors**: RBI policy & rate stance, CPI/WPI, GDP/IIP, USD-INR exchange rate, Brent crude oil, US 10Y yield, GIFT Nifty cues.
- **Company Fundamentals**: P/E vs sector, P/B, ROE/ROCE, quarterly YoY & QoQ revenue/EBITDA/PAT growth, Debt/Equity, Promoter holding & pledging, Free Cash Flow.
- **Corporate Events**: Results calendar, dividend ex-dates, splits/bonuses, bulk/block deals, F&O ban list, ASM/GSM surveillance lists.
- **News & Filings**: Exchange announcements, regulatory filings, earnings call transcripts.

### 2.2 Processing & Scoring Pipeline
1. **Market Regime Score (0–100)**: Trend strength + market breadth + VIX level + institutional flow score + global sentiment.
2. **Sector Relative Strength**: Sector performance relative to Nifty 50 over 1-week and 1-month periods.
3. **Company Quality Score (0–100)**: Multi-factor composite of growth, profitability, balance sheet leverage, valuation, and governance.
4. **Event Risk Filter**: Hard veto to `NEUTRAL` if results are due within 24 hours, stock is under F&O ban, or under ASM/GSM surveillance.
5. **News Sentiment Score (-1.0 to +1.0)**: LLM classifies polarity, materiality, and event category.

### 2.3 Formula Aggregation
```python
fund_score = (
    0.30 * market_regime_score
    + 0.20 * sector_relative_strength_score
    + 0.30 * company_quality_score
    + 0.20 * news_sentiment_score_normalized
)

if fund_score >= 65:
    direction = "LONG"
elif fund_score <= 35 and is_shortable:
    direction = "SHORT"
else:
    direction = "NEUTRAL"

confidence = abs(fund_score - 50.0) / 50.0
```

### 2.4 LLM Guardrails
- LLMs are restricted strictly to text interpretation (news, exchange filings) and human-readable rationale synthesis.
- All numerical scores originate from deterministic calculations.
- Strict Pydantic JSON schema output; formatting failure defaults to `NEUTRAL` with an error flag.
- Every citation requires timestamp and source metadata to eliminate hallucinations.

---

## 3. Agent 2: Technical Analyst + Kelly Sizing
**Purpose**: Generate confluence-based entry, stop-loss, and profit target levels, and calculate risk-adjusted position sizing via fractional Kelly criterion.

### 3.1 Indicator Confluence Matrix
| Category | Indicators Used | Function |
|---|---|---|
| **Trend** | EMA (20, 50, 200), Supertrend (10, 3), ADX / DI+, Ichimoku Cloud | Directional bias and regime alignment |
| **Momentum** | RSI (14), MACD (12, 26, 9), Stochastic RSI, ROC | Velocity and divergence identification |
| **Volatility** | ATR (14), Bollinger Bands (20, 2), Keltner Squeeze | Volatility expansion and dynamic stops |
| **Volume / Flow** | Intraday VWAP, OBV, Volume vs 20-DMA, Delivery % (NSE) | Smart money accumulation/distribution |
| **Structure** | Classical / Fibonacci Pivots, 20/50-day breakout levels | Key support/resistance zones |

### 3.2 Regime Detection
- **TRENDING**: $ADX > 25$ with EMA 20 > EMA 50 > EMA 200 $\rightarrow$ Trend-following & breakout strategies active.
- **RANGING**: $ADX < 20$ with price fluctuating inside Bollinger Bands $\rightarrow$ Mean-reversion strategies active.
- **HIGH VOLATILITY**: India VIX or ATR percentile $> 80$ $\rightarrow$ Size haircut or defensive stand-aside.

### 3.3 Score Aggregation
```python
tech_score = (
    0.30 * trend_score
    + 0.25 * momentum_score
    + 0.20 * volume_score
    + 0.15 * structure_score
    + 0.10 * volatility_context_score
)

if tech_score >= 0.60:
    direction = "LONG"
elif tech_score <= -0.60:
    direction = "SHORT"
else:
    direction = "NEUTRAL"

confidence = min(abs(tech_score), 1.0)
```

### 3.4 Fractional Kelly Position Sizing
1. **Calibrated Probability ($p$)**: Raw confidence mapped through isotonic regression / Platt scaling to historic empirical outcomes.
2. **Payoff Ratio ($b$)**:
   $$b = \frac{|\text{target} - \text{entry}|}{|\text{entry} - \text{stop\_loss}|}$$
3. **Full Kelly Fraction ($f^*$):**
   $$f^* = \frac{b \cdot p - (1 - p)}{b}$$
   If $f^* \le 0$, result is `NO_TRADE`.
4. **Fractional Sizing ($f_{\text{used}}$):**
   $$f_{\text{used}} = \min(f^* \times 0.25, \text{max\_risk\_per\_trade})$$
   Default $\text{max\_risk\_per\_trade} = 1.0\%$ (hard cap $2.0\%$).
5. **Quantity Calculation (NSE Lot Sizing)**:
   $$\text{Risk Amount} = \text{Capital} \times f_{\text{used}}$$
   $$\text{Quantity} = \lfloor \frac{\text{Risk Amount}}{|\text{entry} - \text{stop\_loss}|} \rfloor$$
   For F&O: rounded down to the nearest integer multiple of lot size.
   Liquidity Cap: maximum quantity capped at $\le 1.5\%$ of 20-day Average Daily Volume (ADV).

---

## 4. Agent 3: Execution Agent & Deterministic Risk Engine
**Purpose**: Validate analytical consensus, enforce non-negotiable risk invariants, and manage order lifecycles.

### 4.1 Step 1: Strict Consensus Gate
A trade proposal proceeds to the risk engine **only** if all 4 conditions are met:
1. `agent1.direction == agent2.direction` (Neither is `NEUTRAL`).
2. `agent1.confidence >= 0.40` AND `agent2.confidence >= 0.60`.
3. Combined conviction: $0.40 \cdot \text{fund\_conf} + 0.60 \cdot \text{tech\_conf} \ge 0.65$.
4. Calibrated $p \ge 0.55$ and Payoff ratio $b \ge 1.50$ (ensuring positive expectancy after transaction costs).

If any check fails: return `NO_TRADE` with diagnostic reason code.

### 4.2 Step 2: Deterministic Risk Engine (Zero LLM Bypass)
| Risk Rule | Default Limit | Action on Breach |
|---|---|---|
| Max Risk Per Trade | 1.0% of current capital (Cap 2.0%) | Veto or downsize quantity |
| Max Open Positions | 5 concurrent positions | Veto fresh entries |
| Max Sector Exposure | 25.0% of portfolio capital | Veto new positions in sector |
| Max Single-Stock Exposure | 10.0% of portfolio capital | Veto or clamp quantity |
| Daily Portfolio Loss Limit | 2.0% of capital at day start | Immediately halt new trades for the day |
| Weekly Portfolio Loss Limit | 5.0% of capital at week start | Halt trading & require human review |
| Max Drawdown from Peak | 10.0–15.0% peak-to-trough | Hard stop of all active strategies |
| Permitted Execution Window | 09:30 to 15:00 IST | Disallow entry outside window |
| Minimum Liquidity Hurdle | ADV >= ₹10 Crore, non-ASM/GSM | Veto illiquid or restricted stocks |
| Cost Hurdle Check | Expected Gross Gain $\ge 3 \times$ Roundtrip Costs | Reject low-margin trades |
| Intraday MIS Square-Off | Auto square-off at 15:15 IST | Market-order close of open MIS |
| System Kill Switch | Latency > 15s, data stale, 3 API rejects | Immediate halt & alert notification |

### 4.3 Step 3: Order Construction & Lifecycle
- Orders submitted as Limit / Marketable Limit orders with bracketed Stop-Loss and Target.
- Lifecycle States:
  `CREATED` $\rightarrow$ `VALIDATED` $\rightarrow$ `SUBMITTED` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `PARTIAL/FILLED` $\rightarrow$ `CLOSED`.
- Trailing Stop: Trailed by $2 \times \text{ATR}$ (Chandelier exit) once trade reaches $+1R$ profit.

---

## 5. Indian Market Cost Model
The execution layer models realistic statutory charges per turnover according to Indian regulations:
1. **Brokerage**: Flat ₹20 per order or 0.03% (whichever lower).
2. **Securities Transaction Tax (STT)**: 0.1% on delivery (both sides); 0.025% on intraday equity (sell side); 0.0125% on futures (sell side); 0.0625% on options turnover (sell side).
3. **Exchange Transaction Charges**: NSE: 0.00297%, BSE: 0.00375%.
4. **SEBI Turnover Charges**: ₹10 per crore (0.0001%).
5. **Stamp Duty**: 0.015% on delivery buy, 0.003% on intraday buy, 0.002% on futures buy.
6. **Goods & Services Tax (GST)**: 18% on (Brokerage + Exchange Charges + SEBI Charges).
7. **Slippage Buffer**: 0.05% to 0.15% applied to modeled fills.
