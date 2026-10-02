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

def test_risk_engine_allocates_90_percent_capital(risk_engine, base_portfolio):
    # 90% of ₹10,00,000 = ₹9,00,000
    # At ₹2,500/share, 90% allocation is 360 shares
    proposal = TradeProposal(
        proposal_id="PROP-90PCT",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        entry_price=2500.0,
        stop_loss=2375.0, # 5% stop loss (2500 * 0.95 = 2375)
        target_price=2950.0, # 18% profit target (2500 * 1.18 = 2950)
        suggested_quantity=360,
        suggested_risk_amount=45000.0,
        kelly_fraction=0.05,
        calibrated_win_prob=0.64,
        payoff_ratio=3.6,
        timestamp=datetime.now()
    )

    verdict = risk_engine.evaluate_proposal(proposal, base_portfolio, enforce_timing=False)
    assert verdict.action == RiskAction.APPROVED
    assert verdict.approved_quantity == 360
    assert verdict.approved_risk_amount == 360 * 125.0

def test_quantity_scales_with_portfolio_capital(risk_engine):
    # Test that a portfolio with half the capital receives half the 90% allocation
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
        stop_loss=3800.0, # 5% loss (4000 * 0.95 = 3800)
        target_price=4720.0, # 18% profit (4000 * 1.18 = 4720)
        suggested_quantity=500,
        suggested_risk_amount=100000.0,
        kelly_fraction=0.05,
        calibrated_win_prob=0.64,
        payoff_ratio=3.6,
        timestamp=datetime.now()
    )

    verdict_large = risk_engine.evaluate_proposal(proposal, port_large, enforce_timing=False)
    verdict_small = risk_engine.evaluate_proposal(proposal, port_small, enforce_timing=False)

    # 90% of 1,000,000 = 900,000 / 4000 = 225 shares
    # 90% of 500,000 = 450,000 / 4000 = 112 shares
    assert verdict_large.approved_quantity == 225
    assert verdict_small.approved_quantity == 112

def test_quantity_vetoed_on_insufficient_available_cash(risk_engine, base_portfolio):
    # Set available cash to only ₹200 (less than required margin for a ₹2,500 share = ₹500)
    base_portfolio.available_cash = 200.0

    proposal = TradeProposal(
        proposal_id="PROP-CASH",
        symbol="RELIANCE",
        side=OrderSide.BUY,
        entry_price=2500.0,
        stop_loss=2375.0, # 5% loss
        target_price=2950.0, # 18% target
        suggested_quantity=10,
        suggested_risk_amount=1250.0,
        kelly_fraction=0.05,
        calibrated_win_prob=0.64,
        payoff_ratio=3.6,
        timestamp=datetime.now()
    )

    verdict = risk_engine.evaluate_proposal(proposal, base_portfolio, enforce_timing=False)
    assert verdict.action == RiskAction.VETOED
    assert "INSUFFICIENT_AVAILABLE_CASH" in verdict.rules_triggered

def test_short_sell_quantity_constrained_by_90_percent_capital(risk_engine, base_portfolio):
    # For a SELL (short) order in intraday MIS, quantity deploys up to 90% capital
    proposal_short = TradeProposal(
        proposal_id="PROP-SHORT",
        symbol="SBIN",
        side=OrderSide.SELL,
        entry_price=800.0,
        stop_loss=840.0, # 5% loss against short
        target_price=656.0, # 18% profit on short
        suggested_quantity=1500,
        suggested_risk_amount=60000.0,
        kelly_fraction=0.05,
        calibrated_win_prob=0.64,
        payoff_ratio=3.6,
        timestamp=datetime.now()
    )

    verdict = risk_engine.evaluate_proposal(proposal_short, base_portfolio, enforce_timing=False)
    assert verdict.action in [RiskAction.APPROVED, RiskAction.DOWNSIZED]
    assert verdict.approved_quantity > 0
    # 90% of 1M = 900,000 / 800 = 1,125 shares
    assert verdict.approved_quantity == 1125

