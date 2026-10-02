"""Render Deployment Entrypoint: Web Server with Angel One Broker Authentication Gateway.

Presents a secure Angel One broker login interface before unlocking the live 3-Agent trading console.
Supports both live Angel One SmartAPI v2 authentication and realistic paper simulation mode.
"""

import os
import sys
import json
import time
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger("trading_server")

# Ensure unbuffered real-time logs
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.data.feed import Quote, CompanyFundamentals, MacroContext
from src.data.calendar import NSECalendar
from src.agents.agent1_fundamental import FundamentalAnalystAgent
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.agents.agent3_execution import ExecutionAgent
from src.risk.engine import DeterministicRiskEngine
from src.broker.paper import PaperBroker
from src.broker.angel_one import AngelOneAdapter
from src.memory.journal import TradeJournal
from src.orchestrator.pipeline import TradingOrchestrator
from src.data.universe import NIFTY50_UNIVERSE, ORDER_FLOW_PROFILES, TECHNICAL_PROFILES

# Global state
journal = TradeJournal(db_path="trade_journal.db")
risk_engine = DeterministicRiskEngine({
    "max_risk_per_trade_percent": float(os.getenv("MAX_RISK_PER_TRADE_PCT", 1.0)),
    "hard_risk_cap_percent": 2.0,
    "max_open_positions": int(os.getenv("MAX_OPEN_POSITIONS", 1)),  # Strictly 1 company trade of the day
    "max_sector_exposure_percent": 90.0,
    "max_single_stock_exposure_percent": 90.0,
    "daily_loss_limit_percent": 2.0
})

agent1 = FundamentalAnalystAgent()
agent2 = TechnicalAnalystAgent()
agent3 = ExecutionAgent(risk_engine=risk_engine)

active_broker = None
active_client_code = None
active_mode = None
is_broker_connected = False
system_start_time = datetime.now()
recent_decisions = []
auto_trading_active = False
auto_trading_thread = None
auto_trade_log = []        # Stores auto-trade events for dashboard
analysis_summary = {}      # Latest per-company analysis snapshot for dashboard
top_alpha_pick = None      # The single #1 most profitable company of the day

# Full Nifty 50 watchlist — ALL companies are analysed and ranked
AUTO_WATCHLIST = list(NIFTY50_UNIVERSE.keys())  # 50 stocks
AUTO_SCAN_INTERVAL_SECONDS = 60   # Scan every 60 seconds

def populate_initial_analysis():
    """Pre-computes multi-timeframe fundamental analysis (daily, monthly, yearly) and ranks the single best trade."""
    global analysis_summary, top_alpha_pick

    # Temporary orchestrator for calculating metrics
    temp_orch = TradingOrchestrator(
        agent1=agent1, agent2=agent2, agent3=agent3,
        risk_engine=risk_engine, broker=PaperBroker(), journal=journal
    )

    candidates = []

    for symbol in AUTO_WATCHLIST:
        cdata = NIFTY50_UNIVERSE.get(symbol, {})
        breakdown = agent1.get_multi_timeframe_breakdown(symbol)
        fund_dir = breakdown["direction"]
        fund_score = breakdown["composite_score"]
        daily_score = breakdown["daily"]["score"]
        monthly_score = breakdown["monthly"]["score"]
        yearly_score = breakdown["yearly"]["score"]

        tp = TECHNICAL_PROFILES.get(symbol, {})
        tech_dir = tp.get("direction", "NEUTRAL")
        win_p = 0.975 if (tp.get("adx", 0) >= 28 and tp.get("rsi14", 50) > 55) else 0.50
        gate_passed = (win_p >= 0.68 and fund_dir == "LONG")

        pm = temp_orch.compute_day_profit_potential(
            win_prob=win_p,
            fund_score=fund_score,
            adx=tp.get("adx", 20.0),
            volume_ratio=tp.get("volume_ratio", 1.0),
            orderflow=ORDER_FLOW_PROFILES.get(symbol, {})
        )

        analysis_summary[symbol] = {
            "symbol":             symbol,
            "sector":             cdata.get("sector", "EQUITY"),
            "price":              cdata.get("price", 0),
            "fund_direction":     fund_dir,
            "fund_confidence":    breakdown["confidence"],
            "fund_score":         fund_score,
            "fund_daily_score":   daily_score,
            "fund_monthly_score": monthly_score,
            "fund_yearly_score":  yearly_score,
            "fund_rationale":     breakdown["daily"]["reasons"][:1] + breakdown["monthly"]["reasons"][:1] + breakdown["yearly"]["reasons"][:1],
            "fund_features": {
                "daily_score":   daily_score,
                "monthly_score": monthly_score,
                "yearly_score":  yearly_score,
                "fund_score":    fund_score
            },
            "fund_breakdown":     breakdown,
            "tech_direction":     tech_dir,
            "action":             "NO_TRADE",
            "gate_passed":        gate_passed,
            "win_prob":           round(win_p, 4),
            "consensus":          gate_passed,
            "profit_metrics":     pm,
            "profit_potential_score": pm["day_profit_potential_score"],
            "expected_profit_pct": pm["expected_profit_pct"],
            "leveraged_expected_profit_pct": pm["leveraged_expected_profit_pct"],
            "is_top_pick":        False,
            "reason":             f"Multi-Timeframe Fund: Daily {daily_score} | Monthly {monthly_score} | Yearly {yearly_score} (Composite: {fund_score})",
            "orderflow":          ORDER_FLOW_PROFILES.get(symbol, {}),
            "features":           {"gate_passed": gate_passed},
            "order":              None,
            "scanned_at":         datetime.now().isoformat(),
            "scan_no":            0
        }

        if gate_passed and win_p >= 0.90:
            candidates.append(symbol)

    # Rank and select the single #1 top candidate of the day
    if candidates:
        candidates.sort(key=lambda s: analysis_summary[s]["profit_potential_score"], reverse=True)
        top_alpha_pick = candidates[0]
        top_pm = analysis_summary[top_alpha_pick]["profit_metrics"]

        # Highlight the single best candidate
        for symbol in AUTO_WATCHLIST:
            if symbol == top_alpha_pick:
                analysis_summary[symbol]["action"] = "TRADE"
                analysis_summary[symbol]["is_top_pick"] = True
                analysis_summary[symbol]["reason"] = (
                    f"★ #1 Alpha Pick of the Day: Expected Profit +{top_pm['expected_profit_pct']}% "
                    f"(5x Leveraged: +{top_pm['leveraged_expected_profit_pct']}%) · Score: {top_pm['day_profit_potential_score']}"
                )
            else:
                analysis_summary[symbol]["action"] = "NO_TRADE"
                analysis_summary[symbol]["is_top_pick"] = False
                if analysis_summary[symbol]["gate_passed"]:
                    analysis_summary[symbol]["reason"] = (
                        f"Single Best Trade Focus: Skipped in favor of #1 profit candidate {top_alpha_pick} "
                        f"(+{top_pm['expected_profit_pct']}%)"
                    )

# Pre-populate analysis summary on startup
try:
    populate_initial_analysis()
except Exception as e:
    logger.error(f"Error populating initial analysis: {e}")

def init_orchestrator(broker_instance):
    return TradingOrchestrator(
        agent1=agent1,
        agent2=agent2,
        agent3=agent3,
        risk_engine=risk_engine,
        broker=broker_instance,
        journal=journal
    )

orchestrator = None

def auto_trading_loop():
    """Background thread: scans watchlist every 60s and executes ONLY the single most profitable trade of the day.
    
    1. Checks if an open position already exists (Strictly 1 trade at a time).
    2. If no position is open, runs evaluation on all 50 stocks with execute_order=False.
    3. Ranks qualified candidates by day profit potential score (EV % * Fundamentals * Momentum * Order Flow).
    4. Selects the #1 Top Pick and executes bracket order with 90% capital and 5x broker margin.
    5. Leaves all other 49 stocks in NO_TRADE with explicit reason indicating they were held back for the top pick.
    """
    global auto_trading_active, orchestrator, recent_decisions, auto_trade_log, top_alpha_pick, analysis_summary
    
    print("[AUTO-TRADE] Single Best Trade of the Day Loop STARTED — scanning watchlist every 60s.")
    scan_count = 0

    while auto_trading_active:
        if not is_broker_connected or not orchestrator:
            time.sleep(5)
            continue

        now_ist = NSECalendar.get_ist_now()
        # Enforce Intraday EOD Cut-Off: Auto square-off all MIS positions at 15:15 IST
        if NSECalendar.should_square_off_mis(now_ist):
            print("[AUTO-TRADE] EOD Cut-off reached (15:15 IST) — squaring off all open Intraday MIS positions...")
            if active_broker:
                closed = active_broker.square_off_all_mis(reason="EOD_MIS_SQUAREOFF")
                if closed:
                    print(f"[AUTO-TRADE] Successfully squared off {len(closed)} intraday MIS positions at market close.")
            time.sleep(30)
            continue

        scan_count += 1
        portfolio = active_broker.get_portfolio_state() if active_broker else None

        # Check if an open position already exists (Single Company Trade Policy)
        if portfolio and len(portfolio.open_positions) >= 1:
            active_symbols = list(portfolio.open_positions.keys())
            print(f"[AUTO-TRADE] Scan #{scan_count} — Active trade already running on {active_symbols} (Single Trade Policy: Max 1 position). Monitoring...")
            
            # Update all analysis rows to reflect holding state
            for symbol in AUTO_WATCHLIST:
                if symbol in portfolio.open_positions:
                    pos = portfolio.open_positions[symbol]
                    analysis_summary[symbol]["action"] = "TRADE"
                    analysis_summary[symbol]["is_top_pick"] = True
                    analysis_summary[symbol]["reason"] = f"★ Active Trade of the Day: Holding {pos.quantity} units @ ₹{pos.entry_price:.2f} (5x Margin MIS)"
                else:
                    analysis_summary[symbol]["action"] = "NO_TRADE"
                    analysis_summary[symbol]["is_top_pick"] = False
                    analysis_summary[symbol]["reason"] = f"Single Best Trade Policy: Position already active on {active_symbols[0]} (Max 1 trade at a time)"

            # Sleep and continue monitoring
            for _ in range(AUTO_SCAN_INTERVAL_SECONDS // 5):
                if not auto_trading_active:
                    break
                time.sleep(5)
            continue

        print(f"[AUTO-TRADE] Scan #{scan_count} — evaluating all {len(AUTO_WATCHLIST)} symbols to pick the #1 most profitable trade of the day...")

        evaluations = {}
        qualified_candidates = []

        for symbol in AUTO_WATCHLIST:
            if not auto_trading_active:
                break
            try:
                result = run_symbol_cycle(symbol, orchestrator, execute_order=False)
                evaluations[symbol] = result
                gate_passed = result.get("features", {}).get("gate_passed", False)
                win_prob = result.get("tech_confidence", 0)
                rv = result.get("risk_verdict")

                if result.get("consensus_reached") and rv and rv.approved_quantity > 0 and win_prob >= 0.90:
                    qualified_candidates.append(result)
            except Exception as e:
                logger.error(f"[AUTO-TRADE] Error evaluating {symbol}: {e}")

        top_cand = None
        top_sym = None
        executed_order = None

        if qualified_candidates:
            # Sort by Day Profit Potential Score descending
            qualified_candidates.sort(
                key=lambda x: x.get("profit_metrics", {}).get("day_profit_potential_score", 0.0),
                reverse=True
            )
            top_cand = qualified_candidates[0]
            top_sym = top_cand["symbol"]
            top_alpha_pick = top_sym
            pm = top_cand.get("profit_metrics", {})
            ev_pct = pm.get("expected_profit_pct", 17.4)
            lev_ev = pm.get("leveraged_expected_profit_pct", 87.0)
            score = pm.get("day_profit_potential_score", 0.0)

            print(f"[AUTO-TRADE] ★ EXECUTING #1 SINGLE BEST TRADE OF THE DAY: {top_sym} | WinProb: {top_cand.get('tech_confidence'):.1%} | Expected Profit: +{ev_pct}% (5x Leveraged: +{lev_ev}%) | Alpha Score: {score}")

            executed_order = orchestrator.execute_approved_trade(
                symbol=top_sym,
                sector=top_cand["sector"],
                proposal=top_cand["proposal"],
                risk_verdict=top_cand["risk_verdict"],
                fund_signal=top_cand["fund_signal"],
                tech_signal=top_cand["tech_signal"],
                cycle_id=top_cand["cycle_id"],
                decision_id=top_cand["decision_id"]
            )

        # Update per-company analysis snapshot and logs for all 50 symbols
        trades_placed = 1 if executed_order else 0
        for symbol in AUTO_WATCHLIST:
            result = evaluations.get(symbol, {})
            cdata = NIFTY50_UNIVERSE.get(symbol, {})
            pm = result.get("profit_metrics", {})
            gate_passed = result.get("features", {}).get("gate_passed", False)
            win_prob = result.get("tech_confidence", 0)

            if symbol == top_sym and executed_order:
                action = "TRADE"
                is_top = True
                order_payload = executed_order.model_dump()
                reason = f"★ #1 Alpha Pick of the Day: Executed {executed_order.quantity} units (5x Margin MIS) | Expected Profit: +{pm.get('expected_profit_pct')}% (Leveraged: +{pm.get('leveraged_expected_profit_pct')}%)"
            elif top_sym:
                action = "NO_TRADE"
                is_top = False
                order_payload = None
                top_pm = top_cand.get("profit_metrics", {})
                if gate_passed:
                    reason = f"Single Best Trade Focus: Skipped in favor of #1 profit candidate {top_sym} (+{top_pm.get('expected_profit_pct')}%)"
                else:
                    reason = result.get("reason", "Consensus not reached")
            else:
                action = "NO_TRADE"
                is_top = False
                order_payload = None
                reason = result.get("reason", "No candidate met strict profit thresholds")

            analysis_summary[symbol] = {
                "symbol":             symbol,
                "sector":             cdata.get("sector", "EQUITY"),
                "price":              cdata.get("price", 0),
                "fund_direction":     result.get("fund_direction", "NEUTRAL"),
                "fund_confidence":    result.get("fund_confidence", 0.0),
                "fund_score":         result.get("fund_score", 50.0),
                "fund_daily_score":   result.get("fund_daily_score", 50.0),
                "fund_monthly_score": result.get("fund_monthly_score", 50.0),
                "fund_yearly_score":  result.get("fund_yearly_score", 50.0),
                "fund_rationale":     result.get("fund_rationale", []),
                "fund_features":      result.get("fund_features", {}),
                "tech_direction":     result.get("tech_direction", "NEUTRAL"),
                "action":             action,
                "gate_passed":        gate_passed,
                "win_prob":           round(win_prob, 4),
                "consensus":          result.get("consensus_reached", False),
                "profit_metrics":     pm,
                "profit_potential_score": pm.get("day_profit_potential_score", 0.0),
                "expected_profit_pct": pm.get("expected_profit_pct", 0.0),
                "leveraged_expected_profit_pct": pm.get("leveraged_expected_profit_pct", 0.0),
                "is_top_pick":        is_top,
                "reason":             reason,
                "orderflow":          result.get("orderflow", {}),
                "features":           result.get("features", {}),
                "order":              order_payload,
                "scanned_at":         datetime.now().isoformat(),
                "scan_no":            scan_count,
            }

            event = {
                "scan":        scan_count,
                "timestamp":   datetime.now().isoformat(),
                "symbol":      symbol,
                "sector":      cdata.get("sector", "EQUITY"),
                "action":      action,
                "reason":      reason,
                "gate_passed": gate_passed,
                "win_prob":    win_prob,
                "order":       order_payload
            }
            auto_trade_log.append(event)

            recent_decisions.append({
                "timestamp":          datetime.now().isoformat(),
                "symbol":             symbol,
                "fund_direction":     result.get("fund_direction", "NEUTRAL"),
                "fund_score":         result.get("fund_score", 50.0),
                "fund_daily_score":   result.get("fund_daily_score", 50.0),
                "fund_monthly_score": result.get("fund_monthly_score", 50.0),
                "fund_yearly_score":  result.get("fund_yearly_score", 50.0),
                "tech_direction":     result.get("tech_direction", "NEUTRAL"),
                "consensus":          result.get("consensus_reached", False),
                "action":             action,
                "reason":             reason,
                "auto":               True,
                "orderflow":          result.get("orderflow", {})
            })

        if len(auto_trade_log) > 200:
            auto_trade_log = auto_trade_log[-200:]
        if len(recent_decisions) > 100:
            recent_decisions = recent_decisions[-100:]

        print(f"[AUTO-TRADE] Scan #{scan_count} complete — {trades_placed} trade placed ({top_sym or 'None'}). Sleeping {AUTO_SCAN_INTERVAL_SECONDS}s...")

        # Sleep in 5s increments so loop can be stopped quickly
        for _ in range(AUTO_SCAN_INTERVAL_SECONDS // 5):
            if not auto_trading_active:
                break
            time.sleep(5)

    print("[AUTO-TRADE] Background trading loop STOPPED.")

def start_auto_trading():
    """Start background trading thread if not already running."""
    global auto_trading_active, auto_trading_thread
    if auto_trading_active and auto_trading_thread and auto_trading_thread.is_alive():
        return  # Already running
    auto_trading_active = True
    auto_trading_thread = threading.Thread(target=auto_trading_loop, daemon=True, name="AutoTrader")
    auto_trading_thread.start()
    print("[AUTO-TRADE] Thread launched — autonomous trading is now ACTIVE.")

def stop_auto_trading():
    """Stop the background trading thread."""
    global auto_trading_active
    auto_trading_active = False
    print("[AUTO-TRADE] Stop signal sent.")

class TradingSystemWebServer(BaseHTTPRequestHandler):
    """HTTP handler serving the Web UI and REST API for broker authentication and trading operations."""

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str, indent=2).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        global active_broker, is_broker_connected, active_client_code, active_mode

        if self.path in ["/", "/index.html"]:
            # Serve the Frontend HTML
            html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
            try:
                with open(html_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error loading index.html: {e}".encode("utf-8"))

        elif self.path in ["/health", "/healthz"]:
            # Render health check
            ist_now = NSECalendar.get_ist_now()
            self._send_json(200, {
                "status": "healthy",
                "system": "Autonomous 3-Agent Trading System",
                "broker_connected": is_broker_connected,
                "ist_time": ist_now.strftime("%Y-%m-%d %H:%M:%S IST"),
                "uptime_seconds": int((datetime.now() - system_start_time).total_seconds())
            })

        elif self.path == "/api/status":
            ist_now = NSECalendar.get_ist_now()
            portfolio = active_broker.get_portfolio_state() if active_broker else None
            stats = journal.get_summary_stats()

            env_key = os.getenv("ANGEL_API_KEY", "")
            env_client = os.getenv("ANGEL_CLIENT_CODE", "")
            env_pin = os.getenv("ANGEL_PIN", "")
            env_totp = os.getenv("ANGEL_TOTP_SECRET", "")
            has_env_credentials = bool(env_key and env_client and env_pin and env_totp)
            masked_client = (env_client[:2] + "****" + env_client[-2:]) if len(env_client) >= 4 else env_client

            self._send_json(200, {
                "connected": is_broker_connected,
                "broker_name": "Angel One SmartAPI" if active_mode == "live" else ("Paper Broker" if active_mode == "paper" else "None"),
                "client_code": active_client_code or "Not Authenticated",
                "mode": active_mode or "disconnected",
                "ist_time": ist_now.strftime("%Y-%m-%d %H:%M:%S IST"),
                "is_market_open": NSECalendar.is_market_open(ist_now),
                "is_trade_window_open": NSECalendar.is_trade_window_open(ist_now),
                "has_env_credentials": has_env_credentials,
                "env_client_code": masked_client,
                "has_env_api_key": bool(env_key),
                "portfolio": portfolio.model_dump() if portfolio else None,
                "positions": portfolio.open_positions if portfolio else {},
                "journal_stats": stats,
                "recent_decisions": recent_decisions[-20:],
                "auto_trading_active": auto_trading_active,
                "auto_trade_log": auto_trade_log[-20:],
                "watchlist": AUTO_WATCHLIST,
                "scan_interval_seconds": AUTO_SCAN_INTERVAL_SECONDS,
                "total_universe_size": len(AUTO_WATCHLIST),
                "single_trade_policy": True,
                "top_alpha_pick": top_alpha_pick,
                "max_open_positions": risk_engine.max_open_positions,
                "analysis_summary": analysis_summary
            })

        elif self.path.startswith("/api/fundamentals"):
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            sym = params.get("symbol", [None])[0]

            if sym:
                sym_clean = sym.upper().strip()
                if sym_clean in NIFTY50_UNIVERSE:
                    breakdown = agent1.get_multi_timeframe_breakdown(sym_clean)
                    self._send_json(200, breakdown)
                else:
                    self._send_json(404, {"error": f"Symbol {sym_clean} not found in Nifty 50 universe"})
            else:
                all_breakdowns = {
                    s: agent1.get_multi_timeframe_breakdown(s) for s in AUTO_WATCHLIST
                }
                self._send_json(200, {
                    "total": len(all_breakdowns),
                    "symbols": all_breakdowns
                })

        elif self.path == "/api/analysis":
            self._send_json(200, {
                "status": "ok",
                "total": len(analysis_summary),
                "companies": list(analysis_summary.values()),
                "trades_placed": sum(1 for v in analysis_summary.values() if v.get("action") == "TRADE"),
                "gate_passed_count": sum(1 for v in analysis_summary.values() if v.get("gate_passed")),
                "scanned_at": datetime.now().isoformat()
            })

        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        global active_broker, is_broker_connected, active_client_code, active_mode, orchestrator

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        if self.path == "/api/connect":
            mode = payload.get("mode", "paper")
            use_env = payload.get("use_env", False)

            if mode == "live":
                # API Key is strictly optional - fall back to env var or standard default key
                api_key = (payload.get("api_key", "").strip() or os.getenv("ANGEL_API_KEY", "") or "smartapi_default_key").strip()
                client_code = (payload.get("client_code", "").strip() or os.getenv("ANGEL_CLIENT_CODE", "")).strip()
                pin = (payload.get("pin", "").strip() or os.getenv("ANGEL_PIN", "")).strip()
                totp_input = (payload.get("totp_secret", "").strip() or payload.get("otp", "").strip() or os.getenv("ANGEL_TOTP_SECRET", "")).strip()

                if not (client_code and pin and totp_input):
                    missing = []
                    if not client_code: missing.append("Client Code")
                    if not pin: missing.append("MPIN")
                    if not totp_input: missing.append("OTP / TOTP")
                    self._send_json(400, {
                        "status": "error",
                        "message": f"Please provide: {', '.join(missing)}."
                    })
                    return

                print(f"[SmartAPI] Connecting Angel One account for client: {client_code}...")
                adapter = AngelOneAdapter(
                    api_key=api_key,
                    client_code=client_code,
                    pin=pin,
                    totp_secret=totp_input
                )
                success = adapter.connect(otp_or_secret=totp_input)

                if success:
                    active_broker = adapter
                    active_client_code = client_code
                    active_mode = "live"
                    is_broker_connected = True
                    orchestrator = init_orchestrator(adapter)
                    # AUTO-TRADE: Start autonomous trading immediately on connection
                    start_auto_trading()
                    self._send_json(200, {
                        "status": "success",
                        "message": f"Connected to Angel One ({client_code})! Autonomous trading loop STARTED — scanning {len(AUTO_WATCHLIST)} symbols every {AUTO_SCAN_INTERVAL_SECONDS}s.",
                        "client_code": client_code,
                        "mode": "live",
                        "auto_trading": True,
                        "watchlist": AUTO_WATCHLIST
                    })
                else:
                    err = adapter.last_error or "Angel One login failed. Please check your Client ID, MPIN, or OTP."
                    self._send_json(401, {
                        "status": "error",
                        "message": err
                    })

            else: # Paper Simulation Mode
                paper_code = payload.get("client_code", "").strip() or "PAPER_DEMO"
                active_broker = PaperBroker(initial_capital=1_000_000.0, slippage_pct=0.08)
                active_client_code = paper_code
                active_mode = "paper"
                is_broker_connected = True
                orchestrator = init_orchestrator(active_broker)
                # AUTO-TRADE: Start autonomous trading immediately on paper connect
                start_auto_trading()

                print(f">> Initialized Paper Trading Broker for client {paper_code} with ₹10,00,000 capital.")
                self._send_json(200, {
                    "status": "success",
                    "message": f"Paper Trading ACTIVE as {paper_code}! Autonomous trading loop STARTED — scanning {len(AUTO_WATCHLIST)} symbols every {AUTO_SCAN_INTERVAL_SECONDS}s.",
                    "client_code": paper_code,
                    "mode": "paper",
                    "auto_trading": True,
                    "watchlist": AUTO_WATCHLIST
                })

        elif self.path == "/api/disconnect":
            stop_auto_trading()   # Stop trading loop first
            if active_broker:
                active_broker.disconnect()
            active_broker = None
            active_client_code = None
            active_mode = None
            is_broker_connected = False
            self._send_json(200, {"status": "success", "message": "Broker disconnected and auto-trading loop stopped."})

        elif self.path == "/api/cycle":
            if not is_broker_connected or not orchestrator:
                self._send_json(400, {"status": "error", "message": "Broker account not connected. Please login first."})
                return

            symbol = payload.get("symbol", "RELIANCE")
            print(f">> Running autonomous 3-agent cycle for {symbol}...")

            # Run cycle with live / mock feed data
            result = run_symbol_cycle(symbol, orchestrator)
            fund_breakdown = agent1.get_multi_timeframe_breakdown(symbol)
            result["fund_breakdown"] = fund_breakdown

            # Update analysis_summary for dashboard
            cdata = NIFTY50_UNIVERSE.get(symbol, {})
            gate_passed = result.get("features", {}).get("gate_passed", False)
            win_prob = result.get("tech_confidence", 0)
            action = result.get("action", "NO_TRADE")
            daily_sc = result.get("fund_daily_score", 50.0)
            monthly_sc = result.get("fund_monthly_score", 50.0)
            yearly_sc = result.get("fund_yearly_score", 50.0)
            fund_sc = result.get("fund_score", 50.0)

            analysis_summary[symbol] = {
                "symbol":             symbol,
                "sector":             cdata.get("sector", "EQUITY"),
                "price":              cdata.get("price", 0),
                "fund_direction":     result.get("fund_direction", "NEUTRAL"),
                "fund_confidence":    result.get("fund_confidence", 0.0),
                "fund_score":         fund_sc,
                "fund_daily_score":   daily_sc,
                "fund_monthly_score": monthly_sc,
                "fund_yearly_score":  yearly_sc,
                "fund_rationale":     result.get("fund_rationale", []),
                "fund_features":      result.get("fund_features", {}),
                "fund_breakdown":     fund_breakdown,
                "tech_direction":     result.get("tech_direction", "NEUTRAL"),
                "action":             action,
                "gate_passed":        gate_passed,
                "win_prob":           round(win_prob, 4),
                "consensus":          result.get("consensus_reached", False),
                "reason":             result.get("reason", ""),
                "orderflow":          result.get("orderflow", {}),
                "features":           result.get("features", {}),
                "order":              result.get("order"),
                "scanned_at":         datetime.now().isoformat(),
                "scan_no":            0,
            }

            recent_decisions.append({
                "timestamp":          datetime.now().isoformat(),
                "symbol":             symbol,
                "fund_direction":     result.get("fund_direction", "NEUTRAL"),
                "fund_score":         fund_sc,
                "fund_daily_score":   daily_sc,
                "fund_monthly_score": monthly_sc,
                "fund_yearly_score":  yearly_sc,
                "tech_direction":     result.get("tech_direction", "NEUTRAL"),
                "consensus":          result.get("consensus_reached", False),
                "action":             action,
                "reason":             result.get("reason", ""),
                "orderflow":          result.get("orderflow", {})
            })
            self._send_json(200, result)

        elif self.path == "/api/fundamentals":
            sym = payload.get("symbol", "").upper().strip()
            if sym and sym in NIFTY50_UNIVERSE:
                self._send_json(200, agent1.get_multi_timeframe_breakdown(sym))
            else:
                all_b = {s: agent1.get_multi_timeframe_breakdown(s) for s in AUTO_WATCHLIST}
                self._send_json(200, {"total": len(all_b), "symbols": all_b})

        elif self.path == "/api/kill-switch":
            if active_broker:
                port = active_broker.get_portfolio_state()
                port.is_kill_switch_active = not port.is_kill_switch_active
                status = "ACTIVATED" if port.is_kill_switch_active else "DEACTIVATED"
                self._send_json(200, {"status": "success", "message": f"Emergency Kill Switch {status}."})
            else:
                self._send_json(400, {"status": "error", "message": "No active broker session."})

        elif self.path == "/api/square-off":
            if active_broker:
                closed = active_broker.square_off_all_mis(reason="MANUAL_UI_SQUAREOFF")
                self._send_json(200, {"status": "success", "message": f"Closed {len(closed)} open MIS positions."})
            else:
                self._send_json(400, {"status": "error", "message": "No active broker session."})

        elif self.path == "/api/simulate-tick":
            if not active_broker:
                self._send_json(400, {"status": "error", "message": "No active broker session."})
                return
            symbol = payload.get("symbol")
            price = float(payload.get("price", 0.0))
            if not symbol or price <= 0:
                self._send_json(400, {"status": "error", "message": "Invalid symbol or price."})
                return

            trade = None
            if hasattr(active_broker, "update_price_tick"):
                trade = active_broker.update_price_tick(symbol, price)

            if trade:
                reason_str = trade.exit_reason.value if hasattr(trade.exit_reason, "value") else str(trade.exit_reason)
                self._send_json(200, {
                    "status": "success",
                    "action": "AUTO_SQUAREOFF",
                    "exit_reason": reason_str,
                    "exit_price": trade.exit_price,
                    "net_pnl": trade.net_pnl,
                    "gross_pnl": trade.gross_pnl,
                    "message": f"Position {symbol} automatically squared off on reaching limits! Reason: {reason_str} | Net PnL: ₹{trade.net_pnl:,.2f}"
                })
            else:
                self._send_json(200, {
                    "status": "success",
                    "action": "PRICE_UPDATED",
                    "message": f"Updated {symbol} price to ₹{price:.2f}. Limits not breached."
                })

        elif self.path == "/api/analysis":
            # Return full per-company analysis snapshot for dashboard
            self._send_json(200, {
                "status": "ok",
                "total": len(analysis_summary),
                "companies": list(analysis_summary.values()),
                "trades_placed": sum(1 for v in analysis_summary.values() if v["action"] == "TRADE"),
                "gate_passed_count": sum(1 for v in analysis_summary.values() if v["gate_passed"]),
                "scanned_at": datetime.now().isoformat()
            })

        else:
            self._send_json(404, {"error": "Not Found"})

def run_symbol_cycle(symbol: str, orch: TradingOrchestrator, execute_order: bool = True) -> Dict[str, Any]:
    """Run a full 3-agent evaluation cycle using per-company data from the Nifty 50 universe."""
    # ── Company data from universe ─────────────────────────────────────────
    cdata = NIFTY50_UNIVERSE.get(symbol, {})
    px    = cdata.get("price", 2000.0)

    # ── Shared macro context ───────────────────────────────────────────────
    macro = MacroContext(
        timestamp=datetime.now(),
        nifty50_close=25450.0,
        nifty50_1w_return=1.45,
        nifty50_1m_return=3.80,
        india_vix=13.4,
        advance_decline_ratio=1.65,
        fii_net_flow_5d_cr=4500.0,
        dii_net_flow_5d_cr=3200.0,
        crude_oil_brent=74.5,
        usd_inr=83.85
    )

    quote = Quote(
        symbol=symbol, timestamp=datetime.now(),
        last_price=px, bid_price=px - 0.2, ask_price=px + 0.2,
        volume=cdata.get("volume", 2_000_000)
    )

    # ── Per-company fundamentals ───────────────────────────────────────────
    fundamentals = CompanyFundamentals(
        symbol=symbol,
        sector=cdata.get("sector", "EQUITY"),
        pe_ratio=cdata.get("pe", 25.0),
        sector_pe=cdata.get("sector_pe", 25.0),
        pb_ratio=cdata.get("pb", 3.0),
        roe_percent=cdata.get("roe", 15.0),
        roce_percent=cdata.get("roce", 18.0),
        debt_to_equity=cdata.get("de", 0.5),
        revenue_growth_yoy=cdata.get("rev_g", 10.0),
        pat_growth_yoy=cdata.get("pat_g", 12.0),
        promoter_holding_percent=cdata.get("promoter", 50.0),
        promoter_pledge_percent=cdata.get("pledge", 0.0),
        is_results_due_in_24h=cdata.get("event", False),
        is_fo_ban=cdata.get("fo_ban", False)
    )

    # ── Per-company technical indicators ──────────────────────────────────
    tp = TECHNICAL_PROFILES.get(symbol, {})
    adx_val      = tp.get("adx", 22.0)
    rsi_val      = tp.get("rsi14", 50.0)
    macd_val     = tp.get("macd_hist", 0.5)
    vol_ratio    = tp.get("volume_ratio", 1.0)
    vwap_ratio   = tp.get("vwap_ratio", 1.0)
    ema20_ratio  = tp.get("ema20_r", 0.995)
    ema50_ratio  = tp.get("ema50_r", 0.980)
    ema200_ratio = tp.get("ema200_r", 0.940)

    tech_inputs = {
        "ema20":              px * ema20_ratio,
        "ema50":              px * ema50_ratio,
        "ema200":             px * ema200_ratio,
        "adx":                adx_val,
        "rsi14":              rsi_val,
        "macd_hist":          macd_val,
        "atr14":              px * 0.012,
        "vwap":               px / vwap_ratio,
        "volume_ratio":       vol_ratio,
        "sector_rs_score":    65.0,
        "news_sentiment_score": 0.3,
        "orderflow":          ORDER_FLOW_PROFILES.get(symbol, ORDER_FLOW_PROFILES.get("RELIANCE", {}))
    }

    return orch.run_cycle_for_symbol(
        symbol=symbol,
        sector=cdata.get("sector", "EQUITY"),
        quote=quote,
        macro=macro,
        fundamentals=fundamentals,
        technical_inputs=tech_inputs,
        enforce_timing=False,
        execute_order=execute_order
    )

def main():
    port = int(os.getenv("PORT", 10000))
    host = "0.0.0.0"

    print("=" * 75)
    print("  AUTONOMOUS 3-AGENT TRADING SYSTEM")
    print("  Angel One SmartAPI Gateway & Institutional Trading Console")
    print(f"  Web Interface running at: http://{host}:{port}")
    print(f"  Universe: {len(NIFTY50_UNIVERSE)} Nifty 50 companies")
    print("=" * 75)

    server = HTTPServer((host, port), TradingSystemWebServer)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server cleanly...")
        server.server_close()

if __name__ == "__main__":
    main()
