"""Main Runner: Autonomous 3-Agent Trading System Simulation & Paper Demo."""

import sys
import os

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from datetime import datetime
import json
from src.core.constants import SignalDirection
from src.data.feed import MacroContext, CompanyFundamentals, Quote
from src.agents.agent1_fundamental import FundamentalAnalystAgent
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.agents.agent3_execution import ExecutionAgent
from src.risk.engine import DeterministicRiskEngine
from src.broker.paper import PaperBroker
from src.memory.journal import TradeJournal
from src.orchestrator.pipeline import TradingOrchestrator

def run_demonstration():
    print("=" * 80)
    print("  AUTONOMOUS 3-AGENT TRADING SYSTEM (INDIAN MARKETS: NSE / BSE)")
    print("  Mode: Paper Trading Simulation with Full Indian Statutory Cost Drag")
    print("=" * 80)

    # 1. Initialize Subsystems
    journal = TradeJournal(db_path="paper_trading_journal.db")
    broker = PaperBroker(initial_capital=1_000_000.0, slippage_pct=0.08)
    risk_engine = DeterministicRiskEngine({
        "max_risk_per_trade_percent": 1.0,
        "hard_risk_cap_percent": 2.0,
        "max_open_positions": 5,
        "max_sector_exposure_percent": 25.0,
        "max_single_stock_exposure_percent": 10.0,
        "daily_loss_limit_percent": 2.0
    })

    agent1 = FundamentalAnalystAgent()
    agent2 = TechnicalAnalystAgent()
    agent3 = ExecutionAgent(risk_engine=risk_engine)

    orchestrator = TradingOrchestrator(
        agent1=agent1,
        agent2=agent2,
        agent3=agent3,
        risk_engine=risk_engine,
        broker=broker,
        journal=journal
    )

    # Macro Context (Nifty 50, VIX, FII/DII)
    macro = MacroContext(
        timestamp=datetime.now(),
        nifty50_close=25120.00,
        nifty50_1w_return=1.45,
        nifty50_1m_return=3.80,
        india_vix=13.4,
        advance_decline_ratio=1.65,
        fii_net_flow_5d_cr=4500.0,
        dii_net_flow_5d_cr=3200.0,
        crude_oil_brent=74.5,
        usd_inr=83.85
    )

    test_scenarios = [
        {
            "symbol": "RELIANCE",
            "sector": "ENERGY",
            "quote": Quote(symbol="RELIANCE", timestamp=datetime.now(), last_price=2920.0, bid_price=2919.8, ask_price=2920.2, volume=2_500_000),
            "fundamentals": CompanyFundamentals(
                symbol="RELIANCE", sector="ENERGY", pe_ratio=26.5, sector_pe=28.0, pb_ratio=2.4,
                roe_percent=14.2, roce_percent=13.8, debt_to_equity=0.42, revenue_growth_yoy=11.2,
                pat_growth_yoy=16.5, promoter_holding_percent=50.3, promoter_pledge_percent=0.0
            ),
            "tech": {
                "ema20": 2880.0, "ema50": 2840.0, "ema200": 2720.0,
                "adx": 31.5, "rsi14": 62.4, "macd_hist": 4.5,
                "atr14": 28.0, "vwap": 2905.0, "volume_ratio": 1.45,
                "sector_rs_score": 72.0, "news_sentiment_score": 0.45,
                "orderflow": {
                    "bid_depth_qty": 350_000,
                    "ask_depth_qty": 210_000,
                    "buy_volume": 1_250_000,
                    "sell_volume": 850_000,
                    "cumulative_delta": 400_000,
                    "total_volume": 2_100_000,
                    "institutional_block_buys": 65_000,
                    "institutional_block_sells": 15_000
                }
            },
            "desc": "Confluence Scenario (High Conviction Long on both Agents + Bullish Orderflow)"
        },
        {
            "symbol": "TCS",
            "sector": "IT",
            "quote": Quote(symbol="TCS", timestamp=datetime.now(), last_price=4150.0, bid_price=4149.0, ask_price=4151.0, volume=1_100_000),
            "fundamentals": CompanyFundamentals(
                symbol="TCS", sector="IT", pe_ratio=31.0, sector_pe=29.0, pb_ratio=12.5,
                roe_percent=45.0, roce_percent=55.0, debt_to_equity=0.0, revenue_growth_yoy=6.5,
                pat_growth_yoy=7.2, promoter_holding_percent=72.0, promoter_pledge_percent=0.0
            ),
            "tech": {
                "ema20": 4200.0, "ema50": 4220.0, "ema200": 4100.0, # Bearish cross
                "adx": 18.0, "rsi14": 44.0, "macd_hist": -2.1,
                "atr14": 42.0, "vwap": 4180.0, "volume_ratio": 0.8,
                "sector_rs_score": 48.0, "news_sentiment_score": 0.1,
                "orderflow": {
                    "bid_depth_qty": 140_000,
                    "ask_depth_qty": 280_000,
                    "buy_volume": 420_000,
                    "sell_volume": 680_000,
                    "cumulative_delta": -260_000,
                    "total_volume": 1_100_000,
                    "institutional_block_buys": 5_000,
                    "institutional_block_sells": 45_000
                }
            },
            "desc": "Divergence Scenario (Fundamental Neutral vs Technical Bearish + Selling Tape -> Abstention)"
        },
        {
            "symbol": "INFY",
            "sector": "IT",
            "quote": Quote(symbol="INFY", timestamp=datetime.now(), last_price=1880.0, bid_price=1879.5, ask_price=1880.5, volume=3_200_000),
            "fundamentals": CompanyFundamentals(
                symbol="INFY", sector="IT", pe_ratio=28.0, sector_pe=29.0, pb_ratio=8.0,
                roe_percent=32.0, roce_percent=40.0, debt_to_equity=0.0, revenue_growth_yoy=8.0,
                pat_growth_yoy=9.5, promoter_holding_percent=14.5, promoter_pledge_percent=0.0,
                is_results_due_in_24h=True # EVENT RISK
            ),
            "tech": {
                "ema20": 1850.0, "ema50": 1820.0, "ema200": 1700.0,
                "adx": 34.0, "rsi14": 68.0, "macd_hist": 3.2,
                "atr14": 22.0, "vwap": 1870.0, "volume_ratio": 1.8,
                "sector_rs_score": 65.0, "news_sentiment_score": 0.5,
                "orderflow": {
                    "bid_depth_qty": 200_000,
                    "ask_depth_qty": 190_000,
                    "buy_volume": 1_620_000,
                    "sell_volume": 1_580_000,
                    "cumulative_delta": 40_000,
                    "total_volume": 3_200_000,
                    "institutional_block_buys": 20_000,
                    "institutional_block_sells": 18_000
                }
            },
            "desc": "Event Risk Scenario (Results in 24h -> Hard Veto)"
        }
    ]

    print("\n--- RUNNING DECISION CYCLES ACROSS CANDIDATE STOCKS ---")
    for s in test_scenarios:
        print(f"\n[Evaluating {s['symbol']}] : {s['desc']}")
        result = orchestrator.run_cycle_for_symbol(
            symbol=s["symbol"],
            sector=s["sector"],
            quote=s["quote"],
            macro=macro,
            fundamentals=s["fundamentals"],
            technical_inputs=s["tech"],
            enforce_timing=False # Demo mode runs regardless of clock
        )
        print(f"  • Agent 1 (Fundamental) : {result['fund_direction']} (conf: {result['fund_confidence']})")
        print(f"  • Agent 2 (Technical)   : {result['tech_direction']} (conf: {result['tech_confidence']})")
        print(f"  • Consensus Reached     : {'YES' if result['consensus_reached'] else 'NO'}")
        print(f"  • Pipeline Verdict      : {result['action']}")
        print(f"  • Rationale / Cause     : {result['reason']}")
        if result["order"]:
            print(f"  • Order Executed        : {result['order']['quantity']} units @ ₹{result['order']['average_fill_price']:,.2f}")

    print("\n--- SIMULATING MARKET MOVEMENT & TARGET HIT ---")
    if "RELIANCE" in broker.positions:
        pos = broker.positions["RELIANCE"]
        print(f"Active Position in RELIANCE: {pos.quantity} units @ ₹{pos.entry_price:,.2f}")
        print(f"Stop Loss: ₹{pos.stop_loss:,.2f} | Target: ₹{pos.target_price:,.2f}")

        # Simulate price moving to target price
        print(f"\nSimulating market price tick advancing to target: ₹{pos.target_price:,.2f}...")
        trade_record = broker.update_price_tick("RELIANCE", pos.target_price)
        if trade_record:
            print("\n>>> TRADE CLOSED OUT AT TARGET <<<")
            print(f"  • Exit Price (net slippage): ₹{trade_record.exit_price:,.2f}")
            print(f"  • Gross PnL                : ₹{trade_record.gross_pnl:,.2f}")
            print(f"  • Statutory Fees & Taxes   : ₹{trade_record.fees_and_taxes:,.2f}")
            print(f"  • Slippage Cost            : ₹{trade_record.slippage:,.2f}")
            print(f"  • Net Realized PnL         : ₹{trade_record.net_pnl:,.2f}")
            print(f"  • R-Multiple Realized      : {trade_record.r_multiple:+.2f}R")
            journal.record_trade(trade_record)

    # Print Summary from Journal
    stats = journal.get_summary_stats()
    print("\n" + "=" * 80)
    print("  SESSION EPISODIC JOURNAL & PERFORMANCE SUMMARY")
    print("=" * 80)
    print(f"  • Total Decision Cycles Evaluated : {stats['total_cycles_evaluated']}")
    print(f"  • Trades Executed                 : {stats['trades_executed']}")
    print(f"  • Abstention Rate                 : {stats['abstention_rate_pct']}% (Primary source of precision)")
    print(f"  • Total Closed Trades             : {stats.get('total_closed_trades', 0)}")
    print(f"  • Realized Win Rate               : {stats.get('win_rate_pct', 0.0)}%")
    print(f"  • Net Realized PnL                : ₹{stats.get('total_net_pnl', 0.0):,.2f}")
    print(f"  • Profit Factor                   : {stats.get('profit_factor', 0.0)}")
    print("=" * 80)

if __name__ == "__main__":
    run_demonstration()

    # If running on Render or any cloud environment, stay alive continuously (no early exit)
    is_render = os.getenv("RENDER") is not None or os.getenv("PORT") is not None or os.getenv("CONTINUOUS", "false").lower() == "true"
    
    if is_render:
        port = os.getenv("PORT")
        if port:
            # Render Web Service mode: bind to $PORT to satisfy Render's health checks
            print(f"\n>> Render Web Service detected (PORT={port}). Launching HTTP health check server...")
            try:
                import server
                server.main()
            except Exception as e:
                print(f">> Error starting server: {e}. Falling back to keep-alive loop.")
                import time
                while True:
                    time.sleep(60)
        else:
            # Render Background Worker mode: stay alive and monitor market hours
            print("\n>> Render Background Worker detected. Running 24/7 continuous market scheduler...")
            import time
            while True:
                time.sleep(60)
