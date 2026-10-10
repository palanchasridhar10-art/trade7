"""Unit Tests for TradingView Real-Time Background Price Synchronization Engine."""

import json
import time
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.data.universe import NIFTY50_UNIVERSE
from src.data.calendar import NSECalendar
from src.data.daily_updater import DailyDataManager
from src.agents.agent1_fundamental import FundamentalAnalystAgent
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.agents.agent3_execution import ExecutionAgent
from src.risk.engine import DeterministicRiskEngine
from src.broker.paper import PaperBroker
from src.data.tradingview_service import (
    TradingViewBackgroundService,
    symbol_to_tv_ticker,
    tv_ticker_to_symbol,
    TV_TICKER_OVERRIDES,
    TV_REVERSE_MAP
)


@pytest.fixture
def service_setup():
    agent1 = FundamentalAnalystAgent()
    agent2 = TechnicalAnalystAgent()
    risk_engine = DeterministicRiskEngine()
    agent3 = ExecutionAgent(risk_engine=risk_engine)
    broker = PaperBroker(initial_capital=1_000_000.0)
    daily_mgr = DailyDataManager(
        agent1=agent1, agent2=agent2, agent3=agent3,
        risk_engine=risk_engine, broker=broker
    )
    tv = TradingViewBackgroundService(daily_manager=daily_mgr, broker=broker, sync_interval=5)
    return {
        "tv": tv,
        "daily_mgr": daily_mgr,
        "broker": broker,
        "agent1": agent1,
        "agent2": agent2,
        "agent3": agent3
    }


def test_symbol_ticker_conversions():
    """Verify standard and custom ticker conversions between system symbols and TradingView tickers."""
    # Test overrides
    assert symbol_to_tv_ticker("TATAMOTORS") == "NSE:TMCV"
    assert symbol_to_tv_ticker("LTI") == "NSE:LTM"
    assert symbol_to_tv_ticker("M&M") == "NSE:M&M"
    assert symbol_to_tv_ticker("BAJAJ-AUTO") == "NSE:BAJAJ_AUTO"

    # Test standard symbols
    assert symbol_to_tv_ticker("RELIANCE") == "NSE:RELIANCE"
    assert symbol_to_tv_ticker("TCS") == "NSE:TCS"
    assert symbol_to_tv_ticker("INFY") == "NSE:INFY"
    assert symbol_to_tv_ticker("HDFCBANK") == "NSE:HDFCBANK"

    # Test reverse conversions
    assert tv_ticker_to_symbol("NSE:TMCV") == "TATAMOTORS"
    assert tv_ticker_to_symbol("NSE:LTM") == "LTI"
    assert tv_ticker_to_symbol("NSE:M&M") == "M&M"
    assert tv_ticker_to_symbol("NSE:BAJAJ_AUTO") == "BAJAJ-AUTO"
    assert tv_ticker_to_symbol("NSE:RELIANCE") == "RELIANCE"


def test_tradingview_service_initialization(service_setup):
    """Verify service ticker coverage (50 constituent stocks + Nifty 50 + India VIX)."""
    tv = service_setup["tv"]
    assert len(tv.tickers) == 52
    assert "NSE:NIFTY" in tv.tickers
    assert "NSE:INDIAVIX" in tv.tickers
    assert "NSE:RELIANCE" in tv.tickers
    assert tv.sync_interval == 5
    assert not tv.is_running


def test_fetch_live_data_mock(service_setup):
    """Verify parsing of TradingView scanner response."""
    tv = service_setup["tv"]

    sample_response = {
        "totalCount": 2,
        "data": [
            {
                "s": "NSE:RELIANCE",
                "d": [3050.50, 3020.00, 3065.00, 3015.00, 4500000, 1.45, 0.45, 64.2, 3010.0, 2980.0, 2850.0, 3040.0]
            },
            {
                "s": "NSE:NIFTY",
                "d": [25250.75, 25150.00, 25290.00, 25120.00, 0, 0.65, 0.50, 58.5, 25050.0, 24800.0, 24100.0, 25210.0]
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(sample_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = tv.fetch_live_data()
        assert "NSE:RELIANCE" in res
        rel = res["NSE:RELIANCE"]
        assert rel["close"] == 3050.50
        assert rel["open"] == 3020.00
        assert rel["high"] == 3065.00
        assert rel["low"] == 3015.00
        assert rel["volume"] == 4500000
        assert rel["change_pct"] == 1.45
        assert rel["rsi"] == 64.2
        assert rel["ema20"] == 3010.0
        assert rel["vwap"] == 3040.0

        assert "NSE:NIFTY" in res
        nifty = res["NSE:NIFTY"]
        assert nifty["close"] == 25250.75


def test_sync_system_prices_updates_universe_and_agents(service_setup):
    """Verify that sync_system_prices propagates updates to DailyDataManager, MacroContext, and universe."""
    tv = service_setup["tv"]
    dm = service_setup["daily_mgr"]
    broker = service_setup["broker"]

    sample_response = {
        "totalCount": 3,
        "data": [
            {
                "s": "NSE:RELIANCE",
                "d": [3100.00, 3050.00, 3120.00, 3040.00, 5000000, 2.00, 0.60, 68.0, 3040.0, 2990.0, 2870.0, 3080.0]
            },
            {
                "s": "NSE:NIFTY",
                "d": [25300.00, 25180.00, 25350.00, 25150.00, 0, 0.85, 0.55, 62.0, 25100.0, 24850.0, 24200.0, 25240.0]
            },
            {
                "s": "NSE:INDIAVIX",
                "d": [12.80, 13.10, 13.20, 12.60, 0, -2.50, -0.20, 42.0, 13.0, 13.5, 14.2, 12.9]
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(sample_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        sync_res = tv.sync_system_prices(daily_manager=dm, broker=broker)

        assert sync_res["status"] == "SUCCESS"
        assert sync_res["nifty50_close"] == 25300.00
        assert sync_res["india_vix"] == 12.80
        assert NIFTY50_UNIVERSE["RELIANCE"]["price"] == 3100.00

        # Verify daily quotes
        q = dm.daily_quotes["RELIANCE"]
        assert q["price"] == 3100.00
        assert q["change_pct"] == 2.00
        assert q["source"] == "TRADINGVIEW_LIVE"

        # Verify technicals
        t = dm.daily_technicals["RELIANCE"]
        assert t["rsi14"] == 68.0
        assert t["ema20"] == 3040.0
        assert t["vwap"] == 3080.0

        # Verify macro context close
        assert dm.macro_context.nifty50_close == 25300.00
        assert dm.macro_context.india_vix == 12.80


def test_background_worker_lifecycle(service_setup):
    """Verify background worker thread startup, status reporting, and clean shutdown."""
    tv = service_setup["tv"]

    sample_response = {
        "totalCount": 1,
        "data": [
            {
                "s": "NSE:NIFTY",
                "d": [25200.00, 25100.00, 25250.00, 25080.00, 0, 0.40, 0.20, 55.0, 25000.0, 24700.0, 24000.0, 25150.0]
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(sample_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        tv.start(interval_seconds=1)
        assert tv.is_running
        assert tv._thread is not None
        assert tv._thread.is_alive()

        # Check status
        status = tv.get_status()
        assert status["is_running"] is True
        assert status["sync_interval_seconds"] == 1
        assert status["source"] == "TRADINGVIEW_SCANNER_INDIA"

        # Stop
        tv.stop()
        assert tv.is_running is False
        assert not tv._thread.is_alive()


def test_tradingview_service_1_second_interval(service_setup):
    """Verify that TradingViewBackgroundService allows and enforces 1-second interval."""
    tv = TradingViewBackgroundService(sync_interval=1)
    assert tv.sync_interval == 1

    sample_response = {
        "totalCount": 1,
        "data": [
            {
                "s": "NSE:RELIANCE",
                "d": [3080.0, 3050.0, 3100.0, 3040.0, 2000000, 1.0, 0.3, 60.0, 3050.0, 3000.0, 2900.0, 3060.0]
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(sample_response).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        tv.start(interval_seconds=1)
        time.sleep(1.2)
        assert tv.total_sync_cycles >= 1
        assert tv.get_status()["sync_interval_seconds"] == 1
        tv.stop()
