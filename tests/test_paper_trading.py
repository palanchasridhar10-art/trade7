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
    assert "ITC" not in paper_broker.positions # Closed out

def test_auto_squareoff_on_5_percent_loss(paper_broker):
    # Buy at 1000 with 5% stop loss (950)
    paper_broker.submit_bracket_order(
        symbol="TCS",
        side="BUY",
        quantity=10,
        entry_price=1000.0,
        stop_loss=950.0, # 5% loss
        target_price=1180.0, # 18% target
        sector="IT"
    )

    # Price drops by 5% to 950.0
    trade_record = paper_broker.update_price_tick("TCS", 950.0)
    assert trade_record is not None
    assert trade_record.exit_reason == ExitReason.STOP_LOSS
    assert trade_record.gross_pnl < 0
    assert "TCS" not in paper_broker.positions # Automatically squared off

def test_auto_squareoff_on_15_to_20_percent_profit(paper_broker):
    # Buy at 1000 with 18% target (1180)
    paper_broker.submit_bracket_order(
        symbol="INFY",
        side="BUY",
        quantity=10,
        entry_price=1000.0,
        stop_loss=950.0, # 5% loss
        target_price=1180.0, # 18% target
        sector="IT"
    )

    # Price rises by 18% to 1180.0
    trade_record = paper_broker.update_price_tick("INFY", 1180.0)
    assert trade_record is not None
    assert trade_record.exit_reason == ExitReason.TARGET
    assert trade_record.gross_pnl > 0
    assert "INFY" not in paper_broker.positions # Automatically squared off

