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
