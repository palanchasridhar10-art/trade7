"""Unit tests for the Angel One SmartAPI Adapter."""

import pytest
from src.broker.angel_one import AngelOneAdapter
from src.core.constants import OrderSide, OrderStatus

def test_angel_one_initializes_and_handles_offline_mode():
    adapter = AngelOneAdapter()
    assert adapter.connect() is False # No keys provided in test environment
    state = adapter.get_portfolio_state()
    assert state.total_capital > 0

def test_angel_one_constructs_valid_bracket_order():
    adapter = AngelOneAdapter()
    order = adapter.submit_bracket_order(
        symbol="RELIANCE",
        side="BUY",
        quantity=25,
        entry_price=2900.0,
        stop_loss=2870.0,
        target_price=2960.0
    )
    assert order.symbol == "RELIANCE"
    assert order.quantity == 25
    assert order.side == OrderSide.BUY
    assert "ANGEL-" in order.client_order_id

def test_angel_one_api_key_is_optional():
    # User does NOT provide api_key
    adapter = AngelOneAdapter(
        client_code="P123456",
        pin="9999",
        totp_secret="849201"
    )
    assert adapter.api_key != "" # Automatically assigned fallback default
    assert "smartapi" in adapter.api_key.lower()

    # Calling connect should attempt session generation without complaining about missing API Key
    adapter.connect()
    # If SmartApi isn't installed or mock network fails, last_error must NOT be "Missing credentials: API Key"
    if adapter.last_error:
        assert "API Key" not in adapter.last_error

def test_angel_one_get_ltp_and_market_quotes():
    """Verify Angel One adapter returns LTP and quotes for Nifty stocks."""
    adapter = AngelOneAdapter()
    
    # Test get_ltp for constituents
    rel_ltp = adapter.get_ltp("RELIANCE")
    assert rel_ltp is not None
    assert 1000.0 <= rel_ltp <= 3500.0

    tata_ltp = adapter.get_ltp("TATAMOTORS")
    assert tata_ltp is not None
    assert 300.0 <= tata_ltp <= 1200.0

    # Test get_market_quote
    quote = adapter.get_market_quote("INFY")
    assert quote is not None
    assert quote["symbol"] == "INFY"
    assert quote["price"] > 500.0
    assert "token" in quote

    # Test get_all_ltp
    batch = adapter.get_all_ltp(["RELIANCE", "TATAMOTORS", "COALINDIA"])
    assert len(batch) == 3
    assert "COALINDIA" in batch and batch["COALINDIA"] > 300.0

def test_daily_data_manager_updates_prices_from_angel_one():
    """Verify DailyDataManager synchronizes all share prices from Angel One adapter."""
    from src.data.daily_updater import DailyDataManager
    from unittest.mock import MagicMock
    from src.data.universe import NIFTY50_UNIVERSE

    adapter = AngelOneAdapter()
    # Mock live SmartConnect session
    mock_smart = MagicMock()
    mock_smart.ltpData.return_value = {
        "status": True,
        "data": {
            "symboltoken": "759782",
            "tradingsymbol": "TMCV-EQ",
            "ltp": 955.50,
            "open": 940.0,
            "high": 960.0,
            "low": 938.0,
            "close": 955.50,
            "volume": 3500000
        }
    }
    adapter.smart_api = mock_smart
    adapter.is_connected = True

    # Check direct get_ltp with mocked live connection
    live_ltp = adapter.get_ltp("TATAMOTORS")
    assert live_ltp == 955.50

    manager = DailyDataManager(broker=adapter)
    res = manager.update_prices_from_broker(adapter)
    assert res["status"] == "SUCCESS"
    assert res["symbols_synced"] == 50
    assert NIFTY50_UNIVERSE["TATAMOTORS"]["price"] == 955.50
    assert manager.daily_quotes["TATAMOTORS"]["price"] == 955.50


