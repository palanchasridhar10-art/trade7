"""Unit tests for Agent 2's Fractional Kelly sizing formula."""

import pytest
from src.agents.agent2_technical import TechnicalAnalystAgent

@pytest.fixture
def tech_agent():
    return TechnicalAnalystAgent({
        "kelly": {
            "multiplier": 0.25,
            "max_risk_cap": 0.015, # 1.5% cap
            "min_payoff_ratio": 1.50,
            "min_calibrated_prob": 0.55
        }
    })

def test_fractional_kelly_calculates_sensible_fraction(tech_agent):
    # Payoff ratio b = 2.0, win prob p = 0.60
    # Full Kelly f* = (2 * 0.60 - 0.40) / 2 = (1.2 - 0.4) / 2 = 0.40
    # Quarter Kelly = 0.40 * 0.25 = 0.10 -> clamped to max risk cap 0.015 (1.5%)
    result = tech_agent.compute_fractional_kelly(
        entry=100.0,
        stop_loss=95.0,  # Risk = 5
        target=110.0,    # Gain = 10 -> b = 2.0
        calibrated_p=0.60,
        portfolio_capital=1_000_000.0
    )
    assert result["payoff_ratio"] == 2.0
    assert result["kelly_fraction"] == 0.015 # Clamped by 1.5% risk cap
    assert result["suggested_risk_amount"] == 15000.0
    # Risk = 5 -> qty = 15000 / 5 = 3000 shares
    assert result["quantity"] == 3000

def test_negative_expectancy_returns_zero_sizing(tech_agent):
    # Payoff ratio b = 1.0, win prob p = 0.40 (losing proposition)
    # Full Kelly f* = (1 * 0.40 - 0.60) / 1 = -0.20 <= 0 -> 0 sizing
    result = tech_agent.compute_fractional_kelly(
        entry=100.0,
        stop_loss=95.0,
        target=105.0,
        calibrated_p=0.40,
        portfolio_capital=1_000_000.0
    )
    assert result["kelly_fraction"] == 0.0
    assert result["suggested_risk_amount"] == 0.0
    assert result["quantity"] == 0
