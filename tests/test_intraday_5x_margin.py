"""Test suite for Intraday (MIS) mandate and 5x Broker Margin leverage."""

import pytest
from datetime import datetime, time
import pytz
from src.core.constants import OrderSide, ProductType, RiskAction, ExitReason
from src.core.models import TradeProposal, PortfolioState, Position
from src.risk.engine import DeterministicRiskEngine
from src.broker.paper import PaperBroker
from src.broker.angel_one import AngelOneAdapter
from src.data.calendar import NSECalendar, IST_TZ


@pytest.fixture
def risk_engine():
    return DeterministicRiskEngine()


@pytest.fixture
def portfolio():
    return PortfolioState(
        total_capital=1_000_000.0,
        available_cash=1_000_000.0,
        peak_capital=1_000_000.0
    )


def test_risk_engine_enforces_intraday_mis_only(risk_engine, portfolio):
    """Risk engine must veto any trade that is NOT strictly Intraday MIS."""
    # CNC Delivery proposal must be vetoed
    cnc_proposal = TradeProposal(
        proposal_id="PROP-CNC",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        product_type=ProductType.CNC,  # Delivery
        entry_price=2500.0,
        stop_loss=2375.0,
        target_price=2950.0,
        suggested_quantity=100,
        suggested_risk_amount=12500.0,
        kelly_fraction=0.05,
        calibrated_win_prob=0.70,
        payoff_ratio=3.6,
        timestamp=datetime.now()
    )
    verdict_cnc = risk_engine.evaluate_proposal(cnc_proposal, portfolio, enforce_timing=False)
    assert verdict_cnc.action == RiskAction.VETOED
    assert "NON_INTRADAY_PRODUCT_REJECTED" in verdict_cnc.rules_triggered

    # NRML Positional proposal must also be vetoed
    nrml_proposal = TradeProposal(
        proposal_id="PROP-NRML",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        product_type=ProductType.NRML,  # Normal
        entry_price=2500.0,
        stop_loss=2375.0,
        target_price=2950.0,
        suggested_quantity=100,
        suggested_risk_amount=12500.0,
        kelly_fraction=0.05,
        calibrated_win_prob=0.70,
        payoff_ratio=3.6,
        timestamp=datetime.now()
    )
    verdict_nrml = risk_engine.evaluate_proposal(nrml_proposal, portfolio, enforce_timing=False)
    assert verdict_nrml.action == RiskAction.VETOED
    assert "NON_INTRADAY_PRODUCT_REJECTED" in verdict_nrml.rules_triggered

    # Intraday MIS proposal must pass check 0
    mis_proposal = TradeProposal(
        proposal_id="PROP-MIS",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        product_type=ProductType.MIS,  # Intraday
        entry_price=2500.0,
        stop_loss=2375.0,
        target_price=2950.0,
        suggested_quantity=100,
        suggested_risk_amount=12500.0,
        kelly_fraction=0.05,
        calibrated_win_prob=0.70,
        payoff_ratio=3.6,
        timestamp=datetime.now()
    )
    verdict_mis = risk_engine.evaluate_proposal(mis_proposal, portfolio, enforce_timing=False)
    assert verdict_mis.action == RiskAction.APPROVED
    assert "NON_INTRADAY_PRODUCT_REJECTED" not in verdict_mis.rules_triggered


def test_paper_broker_deducts_only_20_percent_margin_5x_leverage():
    """Broker must block only 20% margin for intraday MIS (5x leverage)."""
    broker = PaperBroker(initial_capital=500_000.0, slippage_pct=0.0)
    broker.connect()

    # Place order for 1,000 units @ ₹500 (Trade Value: ₹5,00,000)
    # With 5x broker margin, only ₹1,00,000 (20%) should be blocked from cash
    order = broker.submit_bracket_order(
        symbol="TATAMOTORS",
        side="BUY",
        quantity=1000,
        entry_price=500.0,
        stop_loss=475.0,
        target_price=590.0
    )
    assert order.product_type == ProductType.MIS
    assert order.quantity == 1000

    # Capital remaining must be ~₹4,00,000 (₹5,00,000 - ₹1,00,000 margin)
    assert pytest.approx(broker.capital, abs=500.0) == 400_000.0
    assert "TATAMOTORS" in broker.positions
    assert broker.positions["TATAMOTORS"].product_type == ProductType.MIS


def test_paper_broker_refunds_20_percent_margin_on_squareoff():
    """When an intraday MIS trade is squared off, the 20% margin is refunded."""
    broker = PaperBroker(initial_capital=500_000.0, slippage_pct=0.0)
    broker.connect()

    # Enter trade: 1,000 units @ ₹500 (margin: ₹1,00,000)
    broker.submit_bracket_order(
        symbol="TATAMOTORS",
        side="BUY",
        quantity=1000,
        entry_price=500.0,
        stop_loss=475.0,
        target_price=590.0
    )
    assert pytest.approx(broker.capital, abs=500.0) == 400_000.0

    # Square off at ₹550 (+10% gain)
    record = broker.update_price_tick("TATAMOTORS", 550.0)
    # If not triggered by tick limit, close via square_off_all_mis
    if not record:
        closed = broker.square_off_all_mis(reason="TEST_CLOSE")
        assert len(closed) == 1

    # After close, the ₹1,00,000 margin is refunded back to capital (+ PnL - statutory fees)
    assert broker.capital > 490_000.0
    assert len(broker.positions) == 0


def test_angel_one_uses_intraday_producttype():
    """Angel One adapter must construct order payloads with producttype='INTRADAY'."""
    adapter = AngelOneAdapter()
    order = adapter.submit_bracket_order(
        symbol="RELIANCE",
        side="BUY",
        quantity=100,
        entry_price=2900.0,
        stop_loss=2755.0,
        target_price=3422.0
    )
    assert order.product_type == ProductType.MIS


def test_eod_squareoff_timing():
    """NSE calendar must trigger should_square_off_mis at or after 15:15 IST on trading days."""
    # 15:14 IST should NOT trigger square-off
    dt_before = datetime(2026, 10, 1, 15, 14, 0, tzinfo=IST_TZ)
    assert not NSECalendar.should_square_off_mis(dt_before)

    # 15:15 IST MUST trigger square-off
    dt_at = datetime(2026, 10, 1, 15, 15, 0, tzinfo=IST_TZ)
    assert NSECalendar.should_square_off_mis(dt_at)

    # 15:20 IST MUST trigger square-off
    dt_after = datetime(2026, 10, 1, 15, 20, 0, tzinfo=IST_TZ)
    assert NSECalendar.should_square_off_mis(dt_after)
