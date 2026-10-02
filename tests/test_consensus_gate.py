"""Unit tests for Agent 3's strict Consensus Gate."""

from datetime import datetime
import pytest
from src.core.constants import SignalDirection, TradingHorizon
from src.core.models import FundamentalSignal, TechnicalSignal
from src.agents.agent3_execution import ExecutionAgent
from src.risk.engine import DeterministicRiskEngine

@pytest.fixture
def execution_agent():
    risk_engine = DeterministicRiskEngine()
    return ExecutionAgent(risk_engine=risk_engine)

def test_consensus_rejects_directional_conflict(execution_agent):
    now = datetime.now()
    fund = FundamentalSignal(
        symbol="RELIANCE",
        timestamp=now,
        direction=SignalDirection.LONG,
        confidence=0.80,
        horizon=TradingHorizon.INTRADAY
    )
    tech = TechnicalSignal(
        symbol="RELIANCE",
        timestamp=now,
        direction=SignalDirection.SHORT,
        confidence=0.75,
        horizon=TradingHorizon.INTRADAY,
        entry=2800.0,
        stop_loss=2830.0,
        target=2740.0,
        win_prob=0.62,
        payoff_ratio=2.0,
        kelly_fraction=0.04,
        suggested_position_value=50000.0
    )
    result = execution_agent.evaluate_consensus(fund, tech)
    assert result.consensus_reached is False
    assert "conflict" in result.reason.lower()

def test_consensus_rejects_neutral_analyst(execution_agent):
    now = datetime.now()
    fund = FundamentalSignal(
        symbol="TCS",
        timestamp=now,
        direction=SignalDirection.NEUTRAL,
        confidence=0.20,
        horizon=TradingHorizon.INTRADAY
    )
    tech = TechnicalSignal(
        symbol="TCS",
        timestamp=now,
        direction=SignalDirection.LONG,
        confidence=0.85,
        horizon=TradingHorizon.INTRADAY,
        entry=4100.0,
        stop_loss=4060.0,
        target=4180.0,
        win_prob=0.65,
        payoff_ratio=2.0,
        kelly_fraction=0.05,
        suggested_position_value=60000.0
    )
    result = execution_agent.evaluate_consensus(fund, tech)
    assert result.consensus_reached is False
    assert "neutral" in result.reason.lower()

def test_consensus_rejects_low_technical_confidence(execution_agent):
    now = datetime.now()
    fund = FundamentalSignal(
        symbol="INFY",
        timestamp=now,
        direction=SignalDirection.LONG,
        confidence=0.80,
        horizon=TradingHorizon.INTRADAY
    )
    tech = TechnicalSignal(
        symbol="INFY",
        timestamp=now,
        direction=SignalDirection.LONG,
        confidence=0.45, # Below required 0.60
        horizon=TradingHorizon.INTRADAY,
        entry=1850.0,
        stop_loss=1830.0,
        target=1890.0,
        win_prob=0.58,
        payoff_ratio=2.0,
        kelly_fraction=0.03,
        suggested_position_value=30000.0
    )
    result = execution_agent.evaluate_consensus(fund, tech)
    assert result.consensus_reached is False
    assert "below minimum" in result.reason.lower()

def test_consensus_passes_on_high_conviction_agreement(execution_agent):
    now = datetime.now()
    fund = FundamentalSignal(
        symbol="HDFCBANK",
        timestamp=now,
        direction=SignalDirection.LONG,
        confidence=0.75,
        horizon=TradingHorizon.INTRADAY
    )
    tech = TechnicalSignal(
        symbol="HDFCBANK",
        timestamp=now,
        direction=SignalDirection.LONG,
        confidence=0.80,
        horizon=TradingHorizon.INTRADAY,
        entry=1650.0,
        stop_loss=1635.0,
        target=1680.0,
        win_prob=0.64,
        payoff_ratio=2.0,
        kelly_fraction=0.05,
        suggested_position_value=75000.0
    )
    result = execution_agent.evaluate_consensus(fund, tech)
    assert result.consensus_reached is True
    assert result.direction == SignalDirection.LONG
    assert result.combined_conviction >= 0.65
