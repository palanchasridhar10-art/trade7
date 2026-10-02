"""Unit tests verifying all deterministic invariants of the RiskEngine."""

from datetime import datetime
import pytest
from src.core.constants import RiskAction, OrderSide, ProductType
from src.core.models import TradeProposal, PortfolioState, Position
from src.risk.engine import DeterministicRiskEngine

@pytest.fixture
def risk_engine():
    return DeterministicRiskEngine({
        "max_risk_per_trade_percent": 1.0,
        "hard_risk_cap_percent": 2.0,
        "max_open_positions": 5,
        "max_sector_exposure_percent": 25.0,
        "max_single_stock_exposure_percent": 10.0,
        "daily_loss_limit_percent": 2.0,
        "weekly_loss_limit_percent": 5.0,
        "max_drawdown_limit_percent": 12.0,
        "min_expected_gain_to_cost_ratio": 3.0
    })

@pytest.fixture
def base_portfolio():
    return PortfolioState(
        total_capital=1_000_000.0,
        available_cash=1_000_000.0,
        utilized_margin=0.0,
        realized_daily_pnl=0.0,
        unrealized_daily_pnl=0.0,
        weekly_realized_pnl=0.0,
        peak_capital=1_000_000.0,
        open_positions={},
        sector_exposure={},
        trades_count_today=0
    )

def test_risk_engine_vetoes_when_kill_switch_active(risk_engine, base_portfolio):
    base_portfolio.is_kill_switch_active = True
    base_portfolio.kill_switch_reason = "Manual emergency halt triggered"

    proposal = TradeProposal(
        proposal_id="PROP-01",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        entry_price=2800.0,
        stop_loss=2770.0,
        target_price=2860.0,
        suggested_quantity=50,
        suggested_risk_amount=1500.0,
        kelly_fraction=0.03,
        calibrated_win_prob=0.62,
        payoff_ratio=2.0,
        timestamp=datetime.now()
    )

    verdict = risk_engine.evaluate_proposal(proposal, base_portfolio, enforce_timing=False)
    assert verdict.action == RiskAction.VETOED
    assert "KILL_SWITCH_ACTIVE" in verdict.rules_triggered

def test_risk_engine_vetoes_when_daily_loss_exceeded(risk_engine, base_portfolio):
    # Daily loss threshold is 2% of 1,000,000 = ₹20,000
    base_portfolio.realized_daily_pnl = -21000.0

    proposal = TradeProposal(
        proposal_id="PROP-02",
        symbol="TCS",
        side=OrderSide.BUY,
        entry_price=4000.0,
        stop_loss=3960.0,
        target_price=4080.0,
        suggested_quantity=20,
        suggested_risk_amount=800.0,
        kelly_fraction=0.02,
        calibrated_win_prob=0.60,
        payoff_ratio=2.0,
        timestamp=datetime.now()
    )

    verdict = risk_engine.evaluate_proposal(proposal, base_portfolio, enforce_timing=False)
    assert verdict.action == RiskAction.VETOED
    assert "DAILY_LOSS_LIMIT_BREACHED" in verdict.rules_triggered

def test_risk_engine_vetoes_when_max_positions_reached(risk_engine, base_portfolio):
    # Populate with 5 dummy open positions
    now = datetime.now()
    for i in range(5):
        sym = f"STOCK_{i}"
        base_portfolio.open_positions[sym] = Position(
            position_id=f"POS_{i}",
            symbol=sym,
            sector="GENERAL",
            side=OrderSide.BUY,
            product_type=ProductType.MIS,
            quantity=10,
            entry_price=100.0,
            current_price=100.0,
            stop_loss=95.0,
            target_price=110.0,
            trailing_stop=95.0,
            opened_at=now,
            last_updated_at=now
        )

    proposal = TradeProposal(
        proposal_id="PROP-03",
        symbol="INFY",
        side=OrderSide.BUY,
        entry_price=1800.0,
        stop_loss=1780.0,
        target_price=1840.0,
        suggested_quantity=20,
        suggested_risk_amount=400.0,
        kelly_fraction=0.02,
        calibrated_win_prob=0.60,
        payoff_ratio=2.0,
        timestamp=datetime.now()
    )

    verdict = risk_engine.evaluate_proposal(proposal, base_portfolio, enforce_timing=False)
    assert verdict.action == RiskAction.VETOED
    assert "MAX_POSITIONS_REACHED" in verdict.rules_triggered

def test_risk_engine_clamps_single_stock_exposure(risk_engine, base_portfolio):
    # 10% max single stock of ₹10,00,000 = ₹1,00,000
    # At ₹2,500/share, max units allowed = 40 shares
    # If proposal suggests 100 shares, it must be downsized to 40
    proposal = TradeProposal(
        proposal_id="PROP-04",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        entry_price=2500.0,
        stop_loss=2480.0,
        target_price=2560.0, # risk per unit = 20, gain per unit = 60
        suggested_quantity=100,
        suggested_risk_amount=2000.0,
        kelly_fraction=0.02,
        calibrated_win_prob=0.62,
        payoff_ratio=3.0,
        timestamp=datetime.now()
    )

    verdict = risk_engine.evaluate_proposal(proposal, base_portfolio, enforce_timing=False)
    assert verdict.action == RiskAction.DOWNSIZED
    assert verdict.approved_quantity <= 40
    assert "QUANTITY_DOWNSIZED_FOR_SAFETY" in verdict.rules_triggered

def test_quantity_scales_with_portfolio_capital(risk_engine):
    # Test that a portfolio with half the capital receives half the quantity
    capital_large = 1_000_000.0
    capital_small = 500_000.0

    port_large = PortfolioState(
        total_capital=capital_large,
        available_cash=capital_large,
        peak_capital=capital_large
    )
    port_small = PortfolioState(
        total_capital=capital_small,
        available_cash=capital_small,
        peak_capital=capital_small
    )

    proposal = TradeProposal(
        proposal_id="PROP-SCALE",
        symbol="TCS",
        side=OrderSide.BUY,
        entry_price=4000.0,
        stop_loss=3950.0, # risk per unit = 50
        target_price=4150.0,
        suggested_quantity=500,
        suggested_risk_amount=25000.0,
        kelly_fraction=0.01,
        calibrated_win_prob=0.60,
        payoff_ratio=3.0,
        timestamp=datetime.now()
    )

    verdict_large = risk_engine.evaluate_proposal(proposal, port_large, enforce_timing=False)
    verdict_small = risk_engine.evaluate_proposal(proposal, port_small, enforce_timing=False)

    # Risk budget: 1% of 1,000,000 = 10,000 -> 10,000 / 50 = 200 units (capped by single stock: 100k / 4000 = 25 units)
    # Risk budget: 1% of 500,000 = 5,000 -> 5,000 / 50 = 100 units (capped by single stock: 50k / 4000 = 12 units)
    assert verdict_large.approved_quantity == 25
    assert verdict_small.approved_quantity == 12

def test_quantity_vetoed_on_insufficient_available_cash(risk_engine, base_portfolio):
    # Set available cash to only ₹200 (less than 20% margin for a ₹2,500 share = ₹500)
    base_portfolio.available_cash = 200.0

    proposal = TradeProposal(
        proposal_id="PROP-CASH",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        entry_price=2500.0,
        stop_loss=2480.0,
        target_price=2560.0,
        suggested_quantity=10,
        suggested_risk_amount=200.0,
        kelly_fraction=0.01,
        calibrated_win_prob=0.60,
        payoff_ratio=3.0,
        timestamp=datetime.now()
    )

    verdict = risk_engine.evaluate_proposal(proposal, base_portfolio, enforce_timing=False)
    assert verdict.action == RiskAction.VETOED
    assert "INSUFFICIENT_AVAILABLE_CASH" in verdict.rules_triggered

def test_short_sell_quantity_constrained_by_capital_and_margin(risk_engine, base_portfolio):
    # For a SELL (short) order in intraday MIS, quantity must also be constrained by capital
    proposal_short = TradeProposal(
        proposal_id="PROP-SHORT",
        symbol="SBIN",
        side=OrderSide.SELL,
        entry_price=800.0,
        stop_loss=815.0, # risk per unit = 15
        target_price=760.0,
        suggested_quantity=500,
        suggested_risk_amount=7500.0,
        kelly_fraction=0.01,
        calibrated_win_prob=0.60,
        payoff_ratio=2.67,
        timestamp=datetime.now()
    )

    verdict = risk_engine.evaluate_proposal(proposal_short, base_portfolio, enforce_timing=False)
    assert verdict.action in [RiskAction.APPROVED, RiskAction.DOWNSIZED]
    assert verdict.approved_quantity > 0
    # Must not exceed single stock cap (10% of 1M = 100k / 800 = 125 shares)
    assert verdict.approved_quantity <= 125

