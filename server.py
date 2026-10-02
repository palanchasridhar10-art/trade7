"""Render Deployment Entrypoint: Web Server with Angel One Broker Authentication Gateway.

Presents a secure Angel One broker login interface before unlocking the live 3-Agent trading console.
Supports both live Angel One SmartAPI v2 authentication and realistic paper simulation mode.
"""

import os
import sys
import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from typing import Dict, Any, Optional

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
                "recent_decisions": recent_decisions[-10:]
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
                # If use_env or fields left blank, pull from environment variables automatically
                api_key = (payload.get("api_key", "").strip() or os.getenv("ANGEL_API_KEY", "")).strip()
                client_code = (payload.get("client_code", "").strip() or os.getenv("ANGEL_CLIENT_CODE", "")).strip()
                pin = (payload.get("pin", "").strip() or os.getenv("ANGEL_PIN", "")).strip()
                totp_input = (payload.get("totp_secret", "").strip() or payload.get("otp", "").strip() or os.getenv("ANGEL_TOTP_SECRET", "")).strip()

                if not (api_key and client_code and pin and totp_input):
                    missing = []
                    if not api_key: missing.append("API Key")
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
                    self._send_json(200, {
                        "status": "success",
                        "message": f"Connected successfully to Angel One ({client_code})!",
                        "client_code": client_code,
                        "mode": "live"
                    })
                else:
                    err = adapter.last_error or "Angel One login failed. Please check your Client ID, MPIN, or OTP."
                    self._send_json(401, {
                        "status": "error",
                        "message": err
                    })

            else: # Paper Simulation Mode
                paper_code = client_code or "PAPER_DEMO"
                active_broker = PaperBroker(initial_capital=1_000_000.0, slippage_pct=0.08)
                active_client_code = paper_code
                active_mode = "paper"
                is_broker_connected = True
                orchestrator = init_orchestrator(active_broker)

                print(f">> Initialized Paper Trading Broker for client {paper_code} with ₹10,00,000 capital.")
                self._send_json(200, {
                    "status": "success",
                    "message": f"Connected in Paper Trading Simulation mode as {paper_code}.",
                    "client_code": paper_code,
                    "mode": "paper"
                })

        elif self.path == "/api/disconnect":
            if active_broker:
                active_broker.disconnect()
            active_broker = None
            active_client_code = None
            active_mode = None
            is_broker_connected = False
            self._send_json(200, {"status": "success", "message": "Broker disconnected."})

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
                "reason": result.get("reason", "")
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

        else:
            self._send_json(404, {"error": "Not Found"})

def run_symbol_cycle(symbol: str, orch: TradingOrchestrator) -> Dict[str, Any]:
    """Helper to run a realistic evaluation cycle for UI demo & live testing."""
    price_map = {
        "RELIANCE": 2920.0,
        "TCS": 4150.0,
        "INFY": 1880.0,
        "HDFCBANK": 1660.0,
        "ICICIBANK": 1240.0,
        "SBIN": 795.0
    }
    px = price_map.get(symbol, 2000.0)

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

    quote = Quote(symbol=symbol, timestamp=datetime.now(), last_price=px, bid_price=px-0.2, ask_price=px+0.2, volume=2_000_000)
    is_infy_event = (symbol == "INFY") # Demonstrate event veto

    fundamentals = CompanyFundamentals(
        symbol=symbol, sector="EQUITY", pe_ratio=26.0, sector_pe=28.0, pb_ratio=3.0,
        roe_percent=18.0, roce_percent=20.0, debt_to_equity=0.3, revenue_growth_yoy=12.0,
        pat_growth_yoy=16.0, promoter_holding_percent=50.0, promoter_pledge_percent=0.0,
        is_results_due_in_24h=is_infy_event
    )

    tech_inputs = {
        "ema20": px * 0.99, "ema50": px * 0.97, "ema200": px * 0.92,
        "adx": 30.0, "rsi14": 62.0, "macd_hist": 2.5,
        "atr14": px * 0.012, "vwap": px * 0.995, "volume_ratio": 1.4,
        "sector_rs_score": 68.0, "news_sentiment_score": 0.4
    }

    return orch.run_cycle_for_symbol(
        symbol=symbol,
        sector="EQUITY",
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
    print("=" * 75)

    server = HTTPServer((host, port), TradingSystemWebServer)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server cleanly...")
        server.server_close()

if __name__ == "__main__":
    main()
