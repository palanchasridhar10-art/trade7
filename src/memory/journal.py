"""Episodic Trade Journal and Audit Trail (SQLite / PostgreSQL)."""

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.core.models import (
    FundamentalSignal,
    TechnicalSignal,
    RiskVerdict,
    TradeRecord
)

class TradeJournal:
    """Persistent SQLite trade journal tracking every decision and executed trade."""

    def __init__(self, db_path: str = "trade_journal.db"):
        self.db_path = db_path
        self._persistent_conn = None  # Keep alive for :memory: DBs
        if db_path == ":memory:":
            self._persistent_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._persistent_conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._persistent_conn is not None:
            return self._persistent_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                cycle_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                exchange TEXT NOT NULL,
                fund_signal TEXT NOT NULL,
                tech_signal TEXT NOT NULL,
                consensus INTEGER NOT NULL,
                risk_check TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                decision_id TEXT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                stop_price REAL NOT NULL,
                target_price REAL NOT NULL,
                exit_price REAL,
                exit_reason TEXT,
                gross_pnl REAL,
                net_pnl REAL,
                fees_and_taxes REAL,
                slippage REAL,
                r_multiple REAL,
                opened_at TEXT NOT NULL,
                closed_at TEXT
            );
            """)
            conn.commit()

    def record_decision(
        self,
        decision_id: str,
        cycle_id: str,
        symbol: str,
        fund_signal: FundamentalSignal,
        tech_signal: TechnicalSignal,
        consensus_reached: bool,
        risk_verdict: Optional[RiskVerdict],
        action: str,
        reason: str
    ) -> None:
        """Persist every evaluation cycle trace for 100% auditability."""
        risk_dict = risk_verdict.model_dump() if risk_verdict else {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO decisions (
                id, cycle_id, timestamp, symbol, exchange,
                fund_signal, tech_signal, consensus, risk_check, action, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision_id,
                cycle_id,
                datetime.now().isoformat(),
                symbol,
                fund_signal.exchange,
                fund_signal.model_dump_json(),
                tech_signal.model_dump_json(),
                1 if consensus_reached else 0,
                json.dumps(risk_dict),
                action,
                reason
            ))
            conn.commit()

    def record_trade(self, trade: TradeRecord) -> None:
        """Record completed trade performance and financial metrics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO trades (
                id, decision_id, symbol, side, quantity,
                entry_price, stop_price, target_price, exit_price,
                exit_reason, gross_pnl, net_pnl, fees_and_taxes,
                slippage, r_multiple, opened_at, closed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.trade_id,
                trade.decision_id,
                trade.symbol,
                trade.side.value,
                trade.quantity,
                trade.entry_price,
                trade.stop_price,
                trade.target_price,
                trade.exit_price,
                trade.exit_reason.value if trade.exit_reason else None,
                trade.gross_pnl,
                trade.net_pnl,
                trade.fees_and_taxes,
                trade.slippage,
                trade.r_multiple,
                trade.opened_at.isoformat(),
                trade.closed_at.isoformat() if trade.closed_at else None
            ))
            conn.commit()

    def get_summary_stats(self) -> Dict[str, Any]:
        """Compute aggregate performance metrics from recorded trades."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM decisions")
            total_decisions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM decisions WHERE action = 'TRADE'")
            executed_decisions = cursor.fetchone()[0]

            cursor.execute("SELECT * FROM trades WHERE closed_at IS NOT NULL")
            rows = cursor.fetchall()

            if not rows:
                return {
                    "total_cycles_evaluated": total_decisions,
                    "trades_executed": executed_decisions,
                    "abstention_rate_pct": round(((total_decisions - executed_decisions) / total_decisions * 100), 1) if total_decisions > 0 else 0.0,
                    "total_trades": 0,
                    "win_rate_pct": 0.0,
                    "total_net_pnl": 0.0,
                    "profit_factor": 0.0
                }

            wins = [r["net_pnl"] for r in rows if r["net_pnl"] > 0]
            losses = [abs(r["net_pnl"]) for r in rows if r["net_pnl"] <= 0]
            total_net_pnl = sum(r["net_pnl"] for r in rows)
            gross_win = sum(wins)
            gross_loss = sum(losses)
            profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (gross_win if gross_win > 0 else 0.0)

            return {
                "total_cycles_evaluated": total_decisions,
                "trades_executed": executed_decisions,
                "abstention_rate_pct": round(((total_decisions - executed_decisions) / total_decisions * 100), 1) if total_decisions > 0 else 0.0,
                "total_closed_trades": len(rows),
                "win_rate_pct": round((len(wins) / len(rows)) * 100.0, 1),
                "total_net_pnl": round(total_net_pnl, 2),
                "profit_factor": round(profit_factor, 2),
                "avg_r_multiple": round(sum(r["r_multiple"] for r in rows) / len(rows), 2)
            }
