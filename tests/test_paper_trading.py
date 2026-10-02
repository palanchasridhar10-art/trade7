"""Unit tests for the PaperBroker execution simulation with Indian cost modeling."""

import pytest
from src.broker.paper import PaperBroker
from src.core.constants import OrderSide, OrderStatus, ExitReason

@pytest.fixture
def paper_broker():
    return PaperBroker(initial_capital=500_000.0, slippage_pct=0.08)

def test_paper_broker_executes_bracket_with_slippage(paper_broker):
    # BUY at 1000 with 0.08% slippage -> fill price = 1000.80
    order = paper_broker.submit_bracket_order(
        symbol="SBIN",
        side="BUY",
        quantity=50,
        entry_price=1000.0,
        stop_loss=980.0,
        target_price=1040.0,
        sector="FINANCIAL_SERVICES"
    )
    assert order.status == OrderStatus.FILLED
    assert order.average_fill_price == 1000.80
    assert "SBIN" in paper_broker.positions

def test_paper_broker_target_hit_calculates_statutory_deductions(paper_broker):
    paper_broker.submit_bracket_order(
        symbol="ITC",
        side="BUY",
        quantity=100,
        entry_price=400.0, # Fill: 400.32
        stop_loss=390.0,
        target_price=420.0,
        sector="FMCG"
    )

    # Simulate price moving to target 420.0
    trade_record = paper_broker.update_price_tick("ITC", 420.0)
    assert trade_record is not None
    assert trade_record.exit_reason == ExitReason.TARGET
    assert trade_record.gross_pnl > 0
    # Statutory fees and slippage must be explicitly accounted for
    assert trade_record.fees_and_taxes > 0
    assert trade_record.slippage > 0
    assert trade_record.net_pnl == pytest.approx(trade_record.gross_pnl - trade_record.fees_and_taxes, 0.01)
    assert "ITC" not in paper_broker.positions # Closed out
