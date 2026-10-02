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
    "max_open_positions": int(os.getenv("MAX_OPEN_POSITIONS", 5)),
    "max_sector_exposure_percent": 25.0,
    "max_single_stock_exposure_percent": 10.0,
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

# Full Nifty 50 watchlist — ALL companies are analysed and traded
AUTO_WATCHLIST = list(NIFTY50_UNIVERSE.keys())  # 50 stocks
AUTO_SCAN_INTERVAL_SECONDS = 60   # Scan every 60 seconds

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
    """Background thread: scans watchlist every 60s and auto-places high-conviction trades.
    
    Only places trades when ALL conditions pass:
    - 4 of 5 technical indicators aligned
    - Order Flow confirms direction
    - ADX >= 28 (strong trend, no chop)
    - Win probability >= 68%
    - 90% capital allocation per position
    - 5% stop loss / 15-20% profit target auto square-off
    """
    global auto_trading_active, orchestrator, recent_decisions, auto_trade_log
    
    print("[AUTO-TRADE] Background trading loop STARTED — scanning watchlist every 60s.")
    scan_count = 0

    while auto_trading_active:
        if not is_broker_connected or not orchestrator:
            time.sleep(5)
            continue

        scan_count += 1
        print(f"[AUTO-TRADE] Scan #{scan_count} — checking {len(AUTO_WATCHLIST)} symbols...")

        trades_placed = 0
        for symbol in AUTO_WATCHLIST:
            if not auto_trading_active:
                break
            try:
                result = run_symbol_cycle(symbol, orchestrator)
                action      = result.get("action", "NO_TRADE")
                reason      = result.get("reason", "")
                order       = result.get("order")
                gate_passed = result.get("features", {}).get("gate_passed", False)
                win_prob    = result.get("tech_confidence", 0)
                tech_dir    = result.get("tech_direction", "NEUTRAL")
                fund_dir    = result.get("fund_direction", "NEUTRAL")

                # Update per-company analysis snapshot for dashboard
                cdata = NIFTY50_UNIVERSE.get(symbol, {})
                analysis_summary[symbol] = {
                    "symbol":         symbol,
                    "sector":         cdata.get("sector", "EQUITY"),
                    "price":          cdata.get("price", 0),
                    "fund_direction": fund_dir,
                    "tech_direction": tech_dir,
                    "action":         action,
                    "gate_passed":    gate_passed,
                    "win_prob":       round(win_prob, 4),
                    "consensus":      result.get("consensus_reached", False),
                    "reason":         reason,
                    "orderflow":      result.get("orderflow", {}),
                    "features":       result.get("features", {}),
                    "order":          order,
                    "scanned_at":     datetime.now().isoformat(),
                    "scan_no":        scan_count,
                }

                event = {
                    "scan":      scan_count,
                    "timestamp": datetime.now().isoformat(),
                    "symbol":    symbol,
                    "sector":    cdata.get("sector", "EQUITY"),
                    "action":    action,
                    "reason":    reason,
                    "gate_passed": gate_passed,
                    "win_prob":  win_prob,
                    "order":     order
                }
                auto_trade_log.append(event)

                # Keep last 200 auto-trade events
                if len(auto_trade_log) > 200:
                    auto_trade_log = auto_trade_log[-200:]

                recent_decisions.append({
                    "timestamp":      datetime.now().isoformat(),
                    "symbol":         symbol,
                    "fund_direction": fund_dir,
                    "tech_direction": tech_dir,
                    "consensus":      result.get("consensus_reached", False),
                    "action":         action,
                    "reason":         reason,
                    "auto":           True,
                    "orderflow":      result.get("orderflow", {})
                })

                if len(recent_decisions) > 100:
                    recent_decisions = recent_decisions[-100:]

                if action == "TRADE" and order:
                    trades_placed += 1
                    print(f"[AUTO-TRADE] PLACED: {symbol} | {reason} | Win prob: {win_prob:.1%}")
                else:
                    print(f"[AUTO-TRADE] SKIP: {symbol} | gate={gate_passed} | {reason[:55]}")

            except Exception as e:
                logger.error(f"[AUTO-TRADE] Error scanning {symbol}: {e}")


        print(f"[AUTO-TRADE] Scan #{scan_count} complete — {trades_placed} trade(s) placed. Sleeping {AUTO_SCAN_INTERVAL_SECONDS}s...")
        
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
                "analysis_summary": analysis_summary
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
            recent_decisions.append({
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "fund_direction": result.get("fund_direction", "NEUTRAL"),
                "tech_direction": result.get("tech_direction", "NEUTRAL"),
                "consensus": result.get("consensus_reached", False),
                "action": result.get("action", "NO_TRADE"),
                "reason": result.get("reason", ""),
                "orderflow": result.get("orderflow", {})
            })
            self._send_json(200, result)

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

def run_symbol_cycle(symbol: str, orch: TradingOrchestrator) -> Dict[str, Any]:
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
        enforce_timing=False
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
