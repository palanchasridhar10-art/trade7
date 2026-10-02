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

