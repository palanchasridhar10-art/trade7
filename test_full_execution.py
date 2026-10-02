"""End-to-end test: verifies all 50 Nifty stocks are scanned and trades are auto-placed."""
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
risk_engine = DeterministicRiskEngine()
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

print(f"\n{'='*70}")
print(f"  FULL NIFTY 50 AUTO-EXECUTION TEST")
print(f"  Initial Capital: Rs.{broker.capital:,.2f}")
print(f"  Max Open Positions: {risk_engine.max_open_positions}")
print(f"{'='*70}\n")

trades_placed = []
skipped = []

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
        technical_inputs=tech_inputs, enforce_timing=False
    )

    action = result.get("action", "NO_TRADE")
    gate = result.get("features", {}).get("gate_passed", False)
    win_p = result.get("tech_confidence", 0)

    if action == "TRADE" and result.get("order"):
        trades_placed.append((symbol, win_p, result.get("order", {}).get("quantity", 0)))
        print(f"  [TRADE PLACED] {symbol:12s} | WinProb={win_p:.1%} | Gate={gate} | "
              f"Qty={result['order'].get('quantity',0)}")
    else:
        reason = result.get("reason", "")[:60]
        skipped.append((symbol, gate, win_p, reason))

print(f"\n{'='*70}")
print(f"  RESULTS: {len(trades_placed)} trades placed | {len(skipped)} skipped")
print(f"  Open Positions: {len(broker.positions)}")
print(f"  Available Cash: Rs.{broker.capital:,.2f}")
print(f"  Open Positions list: {list(broker.positions.keys())}")
print(f"{'='*70}\n")

if trades_placed:
    print("TRADES PLACED:")
    for s, wp, qty in trades_placed:
        pos = broker.positions.get(s)
        if pos:
            print(f"  {s:12s} | {pos.side.value:5s} | {qty:6d} units @ Rs.{pos.entry_price:,.2f}"
                  f" | SL=Rs.{pos.stop_loss:,.2f} | TGT=Rs.{pos.target_price:,.2f}")

print("\nSKIPPED (first 10):")
for s, gate, wp, reason in skipped[:10]:
    print(f"  {s:12s} | gate={gate} | win={wp:.0%} | {reason}")
