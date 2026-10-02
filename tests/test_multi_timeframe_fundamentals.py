"""Test suite for Multi-Timeframe Fundamental Analysis (Daily, Monthly, Yearly)."""

import pytest
from datetime import datetime
from src.core.constants import SignalDirection
from src.data.universe import NIFTY50_UNIVERSE
from src.data.fundamentals_timeframe import DAILY_DATA, MONTHLY_DATA, YEARLY_DATA
from src.data.feed import MacroContext, CompanyFundamentals
from src.agents.agent1_fundamental import FundamentalAnalystAgent


@pytest.fixture
def agent():
    return FundamentalAnalystAgent()


@pytest.fixture
def macro():
    return MacroContext(
        timestamp=datetime.now(),
        nifty50_close=25450.0,
        nifty50_1w_return=1.45,
        nifty50_1m_return=3.80,
        india_vix=13.4,
        advance_decline_ratio=1.65,
        fii_net_flow_5d_cr=4500.0,
        dii_net_flow_5d_cr=3200.0,
        crude_oil_brent=74.5,
        usd_inr=83.85
    )


def test_timeframe_data_completeness():
    """All 50 Nifty universe companies must have Daily, Monthly, and Yearly data."""
    assert len(NIFTY50_UNIVERSE) == 50
    for symbol in NIFTY50_UNIVERSE.keys():
        assert symbol in DAILY_DATA, f"{symbol} missing from DAILY_DATA"
        assert symbol in MONTHLY_DATA, f"{symbol} missing from MONTHLY_DATA"
        assert symbol in YEARLY_DATA, f"{symbol} missing from YEARLY_DATA"


def test_timeframe_weights(agent):
    """Timeframe weights must sum to 1.0 (30% Daily, 40% Monthly, 30% Yearly)."""
    assert agent.DAILY_WEIGHT == 0.30
    assert agent.MONTHLY_WEIGHT == 0.40
    assert agent.YEARLY_WEIGHT == 0.30
    assert pytest.approx(agent.DAILY_WEIGHT + agent.MONTHLY_WEIGHT + agent.YEARLY_WEIGHT) == 1.0


def test_daily_scoring_factors(agent, macro):
    """Daily layer evaluates intraday change, volume surge, FII/DII flow, delivery %, PCR."""
    score, reasons = agent._score_daily("RELIANCE", macro)
    assert 0.0 <= score <= 100.0
    assert isinstance(reasons, list)
    assert len(reasons) > 0


def test_monthly_scoring_factors(agent):
    """Monthly layer evaluates QoQ PAT/revenue, EPS trend, FII 1M flow, sector rotation."""
    score, reasons = agent._score_monthly("RELIANCE")
    assert 0.0 <= score <= 100.0
    assert isinstance(reasons, list)
    assert len(reasons) > 0


def test_yearly_scoring_factors(agent):
    """Yearly layer evaluates 3Y CAGRs, average ROE, debt reduction, FCF, ESG."""
    fundamentals = CompanyFundamentals(
        symbol="RELIANCE", sector="Energy", pe_ratio=24.5, sector_pe=22.0,
        pb_ratio=2.4, roe_percent=9.8, roce_percent=11.2, debt_to_equity=0.42,
        revenue_growth_yoy=8.5, pat_growth_yoy=12.0, promoter_holding_percent=50.3,
        promoter_pledge_percent=0.0
    )
    score, reasons = agent._score_yearly("RELIANCE", fundamentals)
    assert 0.0 <= score <= 100.0
    assert isinstance(reasons, list)
    assert len(reasons) > 0


def test_multi_timeframe_breakdown(agent, macro):
    """get_multi_timeframe_breakdown must return all 3 timeframes and composite score."""
    breakdown = agent.get_multi_timeframe_breakdown("TATAMOTORS", macro=macro)
    assert breakdown["symbol"] == "TATAMOTORS"
    assert "daily" in breakdown
    assert "monthly" in breakdown
    assert "yearly" in breakdown
    assert "composite_score" in breakdown
    assert "direction" in breakdown
    assert "weights" in breakdown

    assert breakdown["daily"]["bias"] in ["BULLISH", "BEARISH", "NEUTRAL"]
    assert breakdown["monthly"]["bias"] in ["BULLISH", "BEARISH", "NEUTRAL"]
    assert breakdown["yearly"]["bias"] in ["BULLISH", "BEARISH", "NEUTRAL"]

    assert 0.0 <= breakdown["daily"]["score"] <= 100.0
    assert 0.0 <= breakdown["monthly"]["score"] <= 100.0
    assert 0.0 <= breakdown["yearly"]["score"] <= 100.0


def test_analyze_multi_timeframe_features(agent, macro):
    """analyze method must expose per-timeframe scores in the features dictionary."""
    fundamentals = CompanyFundamentals(
        symbol="RELIANCE", sector="Energy", pe_ratio=24.5, sector_pe=22.0,
        pb_ratio=2.4, roe_percent=9.8, roce_percent=11.2, debt_to_equity=0.42,
        revenue_growth_yoy=8.5, pat_growth_yoy=12.0, promoter_holding_percent=50.3,
        promoter_pledge_percent=0.0
    )
    signal = agent.analyze("RELIANCE", macro=macro, fundamentals=fundamentals)
    assert signal.symbol == "RELIANCE"
    assert "daily_score" in signal.features
    assert "monthly_score" in signal.features
    assert "yearly_score" in signal.features
    assert "fund_score" in signal.features

    # Check rationale includes labels from each timeframe
    rationale_text = " ".join(signal.rationale)
    assert "[DAILY]" in rationale_text
    assert "[MONTHLY]" in rationale_text
    assert "[YEARLY]" in rationale_text


def test_event_risk_veto(agent, macro):
    """Event risk must veto trading regardless of timeframe scores."""
    fundamentals = CompanyFundamentals(
        symbol="INFY", sector="IT", pe_ratio=27.0, sector_pe=28.0,
        pb_ratio=8.5, roe_percent=32.0, roce_percent=40.0, debt_to_equity=0.03,
        revenue_growth_yoy=6.5, pat_growth_yoy=8.0, promoter_holding_percent=14.8,
        promoter_pledge_percent=0.0, is_results_due_in_24h=True
    )
    signal = agent.analyze("INFY", macro=macro, fundamentals=fundamentals)
    assert signal.direction == SignalDirection.NEUTRAL
    assert signal.confidence == 0.0
    assert signal.features.get("event_risk_veto") is True
