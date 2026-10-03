"""Tests for Daily Data Update, Synchronization, and Rollover across Agents."""

import pytest
from datetime import datetime, date, timedelta
from src.core.constants import SignalDirection
from src.data.calendar import NSECalendar
from src.data.feed import MacroContext, CompanyFundamentals, Quote
from src.data.universe import NIFTY50_UNIVERSE
from src.data.fundamentals_timeframe import DAILY_DATA
from src.data.daily_updater import DailyDataManager
from src.agents.agent1_fundamental import FundamentalAnalystAgent
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.agents.agent3_execution import ExecutionAgent
from src.risk.engine import DeterministicRiskEngine
from src.broker.paper import PaperBroker
from src.memory.journal import TradeJournal
from src.orchestrator.pipeline import TradingOrchestrator


@pytest.fixture
def test_setup():
    agent1 = FundamentalAnalystAgent()
    agent2 = TechnicalAnalystAgent()
    risk_engine = DeterministicRiskEngine()
    agent3 = ExecutionAgent(risk_engine=risk_engine)
    broker = PaperBroker(initial_capital=1_000_000.0)
    journal = TradeJournal(db_path=":memory:")
    orch = TradingOrchestrator(
        agent1=agent1, agent2=agent2, agent3=agent3,
        risk_engine=risk_engine, broker=broker, journal=journal
    )
    daily_mgr = DailyDataManager(
        agent1=agent1, agent2=agent2, agent3=agent3,
        risk_engine=risk_engine, broker=broker
    )
    return {
        "agent1": agent1,
        "agent2": agent2,
        "agent3": agent3,
        "risk_engine": risk_engine,
        "broker": broker,
        "orch": orch,
        "daily_mgr": daily_mgr
    }


def test_daily_manager_initialization(test_setup):
    """DailyDataManager must initialize all 50 stocks with fundamentals, technicals, quotes, and SMC."""
    mgr = test_setup["daily_mgr"]
    assert len(mgr.daily_fundamentals) == 50
    assert len(mgr.daily_technicals) == 50
    assert len(mgr.daily_smc) == 50
    assert len(mgr.daily_orderflow) == 50
    assert len(mgr.daily_quotes) == 50
    assert mgr.active_market_date == NSECalendar.get_ist_now().date()
    assert mgr.macro_context is not None


def test_agent1_daily_update_dynamic_score(test_setup):
    """Updating daily fundamentals dynamically changes Agent 1 daily score and rationale."""
    agent1 = test_setup["agent1"]
    mgr = test_setup["daily_mgr"]
    macro = mgr.macro_context

    initial_score, _ = agent1._score_daily("RELIANCE", macro)

    # Ingest a huge institutional bullish day for RELIANCE
    mgr.update_symbol_daily(
        "RELIANCE",
        daily_fund={
            "pct_change": 3.8,
            "vol_ratio": 2.5,
            "fii_net_cr": 550.0,
            "dii_net_cr": 250.0,
            "news_sentiment": 0.85,
            "delivery_pct": 72.0,
            "put_call_ratio": 0.55
        }
    )

    new_score, reasons = agent1._score_daily("RELIANCE", macro)
    assert new_score > initial_score
    assert any("Strong +3.8% move today" in r for r in reasons)
    assert any("Heavy institutional buying" in r for r in reasons)

    # Verify agent1.get_daily_metrics()
    metrics = agent1.get_daily_metrics("RELIANCE")
    assert metrics["pct_change"] == 3.8
    assert metrics["vol_ratio"] == 2.5


def test_agent2_daily_update_technicals_smc(test_setup):
    """Updating daily technicals and SMC dynamically reflects in Agent 2 profiles."""
    agent2 = test_setup["agent2"]
    mgr = test_setup["daily_mgr"]

    mgr.update_symbol_daily(
        "TATASTEEL",
        technical={
            "direction": "LONG",
            "adx": 36.5,
            "rsi14": 71.0,
            "volume_ratio": 2.1,
            "ema20": 165.0,
            "ema50": 158.0,
            "ema200": 140.0
        },
        smc={
            "market_structure": "BULLISH_BOS",
            "liquidity_event": "SSL_SWEPT",
            "bias": "BULLISH"
        }
    )

    profile = agent2.get_daily_profile("TATASTEEL")
    assert profile["technicals"]["adx"] == 36.5
    assert profile["technicals"]["rsi14"] == 71.0
    assert profile["smc"]["bias"] == "BULLISH"
    assert profile["last_updated"] is not None


def test_risk_engine_and_paper_broker_daily_reset(test_setup):
    """Daily rollover resets Paper Broker daily realized P&L and updates Risk Engine reset timestamp."""
    broker = test_setup["broker"]
    mgr = test_setup["daily_mgr"]

    # Simulate some daily realized P&L on broker
    broker.daily_realized_pnl = 15400.0
    assert broker.daily_realized_pnl == 15400.0

    # Perform daily rollover
    res = mgr.perform_daily_rollover(force=True)
    assert res["status"] == "SUCCESS"
    assert broker.daily_realized_pnl == 0.0
    assert test_setup["risk_engine"].last_daily_reset is not None


def test_daily_rollover_price_and_structure_continuity(test_setup):
    """Daily rollover rolls date forward, evolves prices, updates EMAs, and updates history."""
    mgr = test_setup["daily_mgr"]
    old_date = mgr.active_market_date
    target_date = old_date + timedelta(days=1)

    old_reliance_price = mgr.daily_quotes["RELIANCE"]["price"]

    result = mgr.perform_daily_rollover(target_date=target_date, force=True, market_bias="BULLISH")
    assert result["status"] == "SUCCESS"
    assert mgr.active_market_date == target_date
    assert result["symbols_updated"] == 50

    new_reliance_quote = mgr.daily_quotes["RELIANCE"]
    assert new_reliance_quote["previous_close"] == old_reliance_price
    assert new_reliance_quote["price"] > 0
    assert len(mgr.update_history) >= 1
    assert mgr.update_history[-1]["new_date"] == target_date.isoformat()


def test_orchestrator_on_daily_rollover(test_setup):
    """TradingOrchestrator coordinates daily rollover through DailyDataManager."""
    orch = test_setup["orch"]
    mgr = test_setup["daily_mgr"]

    result = orch.on_daily_rollover(daily_manager=mgr)
    assert result["status"] == "SUCCESS"


def test_daily_status_api_format(test_setup):
    """DailyDataManager.get_status() returns all required fields for REST API and dashboard."""
    mgr = test_setup["daily_mgr"]
    status = mgr.get_status()

    assert "status" in status
    assert "active_market_date" in status
    assert "last_updated_at" in status
    assert "total_symbols_synced" in status
    assert status["total_symbols_synced"] == 50
    assert "macro_snapshot" in status
    assert "india_vix" in status["macro_snapshot"]
    assert "nifty50_close" in status["macro_snapshot"]


def test_symbol_daily_data_api(test_setup):
    """DailyDataManager.get_symbol_daily_data() returns complete multi-agent daily snapshot."""
    mgr = test_setup["daily_mgr"]
    data = mgr.get_symbol_daily_data("RELIANCE")

    assert data["symbol"] == "RELIANCE"
    assert "fundamentals" in data
    assert "technicals" in data
    assert "smc" in data
    assert "orderflow" in data
    assert "quote" in data
