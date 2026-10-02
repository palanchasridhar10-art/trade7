"""Render Deployment Entrypoint: Health Check Web Server & Background Trading Scheduler.

Binds to Render's dynamic $PORT to satisfy Web Service health checks,
while running the autonomous trading cycle scheduler in the background.
"""

import os
import sys
import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Ensure unbuffered real-time logs
sys.stdout.reconfigure(encoding="utf-8")

from src.data.feed import Quote, CompanyFundamentals, MacroContext
from src.data.calendar import NSECalendar
from src.agents.agent1_fundamental import FundamentalAnalystAgent
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.agents.agent3_execution import ExecutionAgent
from src.risk.engine import DeterministicRiskEngine
from src.broker.paper import PaperBroker
from src.memory.journal import TradeJournal
from src.orchestrator.pipeline import TradingOrchestrator

# Global subsystem singletons
journal = TradeJournal(db_path="trade_journal.db")
broker = PaperBroker(initial_capital=float(os.getenv("INITIAL_CAPITAL", 1_000_000.0)), slippage_pct=0.08)
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

orchestrator = TradingOrchestrator(
    agent1=agent1,
    agent2=agent2,
    agent3=agent3,
    risk_engine=risk_engine,
    broker=broker,
    journal=journal
)

system_start_time = datetime.now()

class RenderHealthHandler(BaseHTTPRequestHandler):
    """HTTP request handler satisfying Render port binding and health check requirements."""

    def do_GET(self):
        if self.path in ["/", "/health", "/healthz"]:
            portfolio = broker.get_portfolio_state()
            stats = journal.get_summary_stats()
            ist_now = NSECalendar.get_ist_now()

            response_data = {
                "status": "healthy",
                "system": "Autonomous 3-Agent Trading System (NSE/BSE)",
                "environment": os.getenv("SYSTEM_ENVIRONMENT", "paper"),
                "ist_time": ist_now.strftime("%Y-%m-%d %H:%M:%S IST"),
                "is_trading_day": NSECalendar.is_trading_day(ist_now),
                "is_market_open": NSECalendar.is_market_open(ist_now),
                "is_trade_window_open": NSECalendar.is_trade_window_open(ist_now),
                "portfolio": {
                    "total_capital": portfolio.total_capital,
                    "available_cash": portfolio.available_cash,
                    "daily_realized_pnl": portfolio.realized_daily_pnl,
                    "open_positions_count": len(portfolio.open_positions)
                },
                "journal_stats": stats,
                "uptime_seconds": int((datetime.now() - system_start_time).total_seconds())
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, indent=2).encode("utf-8"))

        elif self.path == "/portfolio":
            portfolio = broker.get_portfolio_state()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(portfolio.model_dump(), default=str, indent=2).encode("utf-8"))

        elif self.path == "/journal":
            stats = journal.get_summary_stats()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(stats, indent=2).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not Found"}')

    def log_message(self, format, *args):
        # Suppress routine health check log clutter
        pass

def run_trading_worker_loop():
    """Background scheduler thread executing periodic decision cycles during market hours."""
    print(">> Background Trading Scheduler thread initialized.")
    while True:
        try:
            ist_now = NSECalendar.get_ist_now()
            
            # Check for 15:15 IST automated MIS square-off
            if NSECalendar.should_square_off_mis(ist_now) and broker.positions:
                print(f"[{ist_now.strftime('%H:%M:%S IST')}] Triggering mandatory 15:15 MIS auto square-off...")
                broker.square_off_all_mis(reason="15:15_MIS_SQUAREOFF")

            # Check if within safe execution window (09:30 - 15:00 IST)
            if NSECalendar.is_trade_window_open(ist_now):
                print(f"[{ist_now.strftime('%H:%M:%S IST')}] Active algorithmic trade window open.")
                # Decision cycle logic executes here on scheduled tick
            time.sleep(60)
        except Exception as e:
            print(f"[Error in worker loop]: {e}", file=sys.stderr)
            time.sleep(10)

def main():
    port = int(os.getenv("PORT", 10000))
    host = "0.0.0.0"

    print("=" * 70)
    print(f"  Starting Autonomous Trading System on Render")
    print(f"  Listening for health checks on http://{host}:{port}")
    print("=" * 70)

    # Start background scheduler thread
    worker_thread = threading.Thread(target=run_trading_worker_loop, daemon=True)
    worker_thread.start()

    # Start HTTP server on Render's dynamic port
    server = HTTPServer((host, port), RenderHealthHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down server gracefully...")
        server.server_close()

if __name__ == "__main__":
    main()
