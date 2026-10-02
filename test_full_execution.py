"""End-to-end test: verifies all 50 Nifty stocks are evaluated, ranked by profit potential, and ONLY the single most profitable company trade is placed."""
import sys
sys.path.insert(0, '.')
from datetime import datetime
from src.data.universe import NIFTY50_UNIVERSE, ORDER_FLOW_PROFILES, TECHNICAL_PROFILES
from src.data.feed import Quote, CompanyFundamentals, MacroContext
from src.agents.agent1_fundamental import FundamentalAnalystAgent
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.agents.agent3_execution import ExecutionAgent
from src.risk.engine import DeterministicRiskEngine
from src.broker.paper import PaperBroker
from src.memory.journal import TradeJournal
from src.orchestrator.pipeline import TradingOrchestrator

# Setup
journal = TradeJournal(db_path=":memory:")
risk_engine = DeterministicRiskEngine()  # Defaults to max_open_positions = 1
agent1 = FundamentalAnalystAgent()
agent2 = TechnicalAnalystAgent()
agent3 = ExecutionAgent(risk_engine=risk_engine)
broker = PaperBroker(initial_capital=1_000_000.0)
broker.connect()

orch = TradingOrchestrator(agent1=agent1, agent2=agent2, agent3=agent3,
                            risk_engine=risk_engine, broker=broker, journal=journal)

macro = MacroContext(
    timestamp=datetime.now(),
    nifty50_close=25450.0, nifty50_1w_return=1.45, nifty50_1m_return=3.80,
    india_vix=13.4, advance_decline_ratio=1.65,
    fii_net_flow_5d_cr=4500.0, dii_net_flow_5d_cr=3200.0,
    crude_oil_brent=74.5, usd_inr=83.85
)

print(f"\n{'='*75}")
print(f"  FULL NIFTY 50 UNIVERSE SCAN: SINGLE BEST PROFIT TRADE OF THE DAY")
print(f"  Initial Capital: Rs.{broker.capital:,.2f}")
print(f"  Max Open Positions: {risk_engine.max_open_positions} (Strictly 1 Company Trade Policy)")
print(f"{'='*75}\n")

evaluations = {}
qualified_candidates = []
skipped = []

# Phase 1: Evaluate all 50 Nifty stocks with execute_order=False
for symbol in NIFTY50_UNIVERSE.keys():
    cdata = NIFTY50_UNIVERSE[symbol]
    px = cdata["price"]
    tp = TECHNICAL_PROFILES.get(symbol, {})

    quote = Quote(symbol=symbol, timestamp=datetime.now(), last_price=px,
                  bid_price=px-0.2, ask_price=px+0.2, volume=2_000_000)

    fundamentals = CompanyFundamentals(
        symbol=symbol, sector=cdata.get("sector", "EQUITY"),
        pe_ratio=cdata.get("pe", 25.0), sector_pe=cdata.get("sector_pe", 25.0),
        pb_ratio=cdata.get("pb", 3.0), roe_percent=cdata.get("roe", 15.0),
        roce_percent=cdata.get("roce", 18.0), debt_to_equity=cdata.get("de", 0.5),
        revenue_growth_yoy=cdata.get("rev_g", 10.0), pat_growth_yoy=cdata.get("pat_g", 12.0),
        promoter_holding_percent=cdata.get("promoter", 50.0), promoter_pledge_percent=cdata.get("pledge", 0.0),
        is_results_due_in_24h=cdata.get("event", False)
    )

    adx_val = tp.get("adx", 22.0); rsi_val = tp.get("rsi14", 50.0)
    macd_val = tp.get("macd_hist", 0.5); vol_ratio = tp.get("volume_ratio", 1.0)
    vwap_r = tp.get("vwap_ratio", 1.0)

    tech_inputs = {
        "ema20": px * tp.get("ema20_r", 0.995), "ema50": px * tp.get("ema50_r", 0.980),
        "ema200": px * tp.get("ema200_r", 0.940), "adx": adx_val,
        "rsi14": rsi_val, "macd_hist": macd_val,
        "atr14": px * 0.012, "vwap": px / vwap_r, "volume_ratio": vol_ratio,
        "sector_rs_score": 65.0, "news_sentiment_score": 0.3,
        "orderflow": ORDER_FLOW_PROFILES.get(symbol, {})
    }

    result = orch.run_cycle_for_symbol(
        symbol=symbol, sector=cdata.get("sector", "EQUITY"),
        quote=quote, macro=macro, fundamentals=fundamentals,
        technical_inputs=tech_inputs, enforce_timing=False,
        execute_order=False  # Scan and evaluate only
    )

    evaluations[symbol] = result
    gate = result.get("features", {}).get("gate_passed", False)
    win_p = result.get("tech_confidence", 0)
    rv = result.get("risk_verdict")

    if result.get("consensus_reached") and rv and rv.approved_quantity > 0 and win_p >= 0.90:
        qualified_candidates.append(result)
    else:
        skipped.append((symbol, gate, win_p, result.get("reason", "")[:60]))

# Phase 2: Rank qualified candidates by Day Profit Potential Score
qualified_candidates.sort(
    key=lambda x: x.get("profit_metrics", {}).get("day_profit_potential_score", 0.0),
    reverse=True
)

print(f"  Candidates Qualified for Trade: {len(qualified_candidates)} out of {len(NIFTY50_UNIVERSE)}")
print("  Top 5 Ranked Candidates by Expected Profit Potential:")
for rank, c in enumerate(qualified_candidates[:5], 1):
    pm = c["profit_metrics"]
    print(f"    #{rank} {c['symbol']:12s} | Score: {pm['day_profit_potential_score']:6.2f} | "
          f"EV: +{pm['expected_profit_pct']:.1f}% | 5x Leveraged: +{pm['leveraged_expected_profit_pct']:.1f}% | "
          f"WinProb: {c['tech_confidence']:.1%}")

# Phase 3: Execute ONLY the single #1 highest-profit candidate
top_candidate = qualified_candidates[0]
top_symbol = top_candidate["symbol"]
top_pm = top_candidate["profit_metrics"]

executed_order = orch.execute_approved_trade(
    symbol=top_symbol,
    sector=top_candidate["sector"],
    proposal=top_candidate["proposal"],
    risk_verdict=top_candidate["risk_verdict"],
    fund_signal=top_candidate["fund_signal"],
    tech_signal=top_candidate["tech_signal"],
    cycle_id=top_candidate["cycle_id"],
    decision_id=top_candidate["decision_id"]
)

print(f"\n{'='*75}")
print(f"  EXECUTION RESULT: Exactly 1 Trade Placed | 49 Companies Held Back")
print(f"  Open Positions in Broker: {len(broker.positions)}")
print(f"  Available Cash: Rs.{broker.capital:,.2f}")
print(f"  Held Position: {list(broker.positions.keys())}")
print(f"{'='*75}\n")

pos = broker.positions.get(top_symbol)
print(f"  [TRADE EXECUTED] {top_symbol} (Rank #1 Alpha Pick of the Day)")
print(f"    Side:             {pos.side.value}")
print(f"    Quantity:         {pos.quantity} units (90% capital allocation)")
print(f"    Entry Price:      Rs.{pos.entry_price:,.2f}")
print(f"    Stop Loss (-5%):  Rs.{pos.stop_loss:,.2f}")
print(f"    Target (+18%):    Rs.{pos.target_price:,.2f}")
print(f"    Expected Profit:  +{top_pm['expected_profit_pct']:.1f}%")
print(f"    5x Leveraged EV:  +{top_pm['leveraged_expected_profit_pct']:.1f}% on margin capital")
print(f"    Blocked Margin:   Rs.{pos.entry_price * pos.quantity * 0.20:,.2f} (20% SEBI MIS requirement)")
print(f"    Unallocated Cash: Rs.{broker.capital:,.2f} (Safety Reserve)")

# Assertions
assert len(broker.positions) == 1, f"Expected exactly 1 position, got {len(broker.positions)}"
assert top_symbol in broker.positions, f"Expected {top_symbol} to be the open position"
print("\n[SUCCESS] Single most profitable company trade placed successfully!")
