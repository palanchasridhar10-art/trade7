"""Unit tests for Agent 2's Order Flow and Market Microstructure feature."""

import pytest
from datetime import datetime
from src.data.orderflow import OrderFlowData, compute_orderflow_metrics
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.core.constants import SignalDirection

@pytest.fixture
def tech_agent():
    return TechnicalAnalystAgent()

def test_orderflow_bullish_accumulation():
    data = OrderFlowData(
        symbol="RELIANCE",
        bid_depth_qty=350_000,
        ask_depth_qty=200_000,
        buy_volume=1_200_000,
        sell_volume=800_000,
        cumulative_delta=400_000,
        total_volume=2_000_000,
        institutional_block_buys=60_000,
        institutional_block_sells=15_000
    )
    result = compute_orderflow_metrics(data)
    assert result.flow_regime == "ACCUMULATION"
    assert result.order_book_imbalance > 0.20
    assert result.delta_ratio > 0.15
    assert result.institutional_bias > 0.50
    assert result.orderflow_score >= 0.25
    assert result.orderflow_vote == 1.0
    assert any("Accumulation" in r for r in result.rationale)

def test_orderflow_bearish_distribution():
    data = OrderFlowData(
        symbol="TCS",
        bid_depth_qty=150_000,
        ask_depth_qty=300_000,
        buy_volume=400_000,
        sell_volume=700_000,
        cumulative_delta=-300_000,
        total_volume=1_100_000,
        institutional_block_buys=5_000,
        institutional_block_sells=40_000
    )
    result = compute_orderflow_metrics(data)
    assert result.flow_regime == "DISTRIBUTION"
    assert result.order_book_imbalance < -0.20
    assert result.delta_ratio < -0.15
    assert result.institutional_bias < -0.50
    assert result.orderflow_score <= -0.25
    assert result.orderflow_vote == -1.0
    assert any("Distribution" in r for r in result.rationale)

def test_orderflow_bullish_absorption_detection():
    # Selling pressure absorbed by heavy passive institutional bids at support
    data = OrderFlowData(
        symbol="SBIN",
        bid_depth_qty=400_000,
        ask_depth_qty=200_000,
        buy_volume=300_000,
        sell_volume=500_000,
        cumulative_delta=-200_000,
        total_volume=800_000,
        institutional_block_buys=30_000,
        institutional_block_sells=10_000,
        is_at_support_or_resistance=True
    )
    result = compute_orderflow_metrics(data)
    assert result.absorption_detected is True
    assert any("Absorption" in r for r in result.rationale)

def test_agent2_integrates_orderflow_into_features_and_score(tech_agent):
    orderflow_input = {
        "bid_depth_qty": 300_000,
        "ask_depth_qty": 180_000,
        "buy_volume": 1_000_000,
        "sell_volume": 600_000,
        "cumulative_delta": 400_000,
        "total_volume": 1_600_000,
        "institutional_block_buys": 50_000,
        "institutional_block_sells": 10_000
    }

    signal = tech_agent.analyze(
        symbol="RELIANCE",
        current_price=2920.0,
        ema20=2880.0,
        ema50=2840.0,
        ema200=2720.0,
        adx=34.0,          # Updated: meets new ADX ≥32 requirement
        rsi14=63.0,         # Updated: within new 57-75 long zone
        macd_hist=3.5,
        atr14=28.0,
        vwap=2905.0,
        volume_ratio=1.60,  # Updated: meets new 1.40x volume requirement
        orderflow=orderflow_input,
        portfolio_capital=1_000_000.0
    )

    assert signal.direction == SignalDirection.LONG
    assert signal.confidence >= 0.70
    # Check orderflow features are present
    assert "orderflow_score" in signal.features
    assert "order_book_imbalance" in signal.features
    assert "cumulative_volume_delta" in signal.features
    assert signal.features["cumulative_volume_delta"] == 400_000
    assert signal.features["orderflow_regime"] == "ACCUMULATION"
    assert any("Order Flow" in r or "Accumulation" in r for r in signal.rationale)

def test_agent2_bearish_orderflow_lowers_confidence(tech_agent):
    # Same price but heavy seller order book and distribution tape
    bearish_orderflow = {
        "bid_depth_qty": 120_000,
        "ask_depth_qty": 350_000,
        "buy_volume": 300_000,
        "sell_volume": 800_000,
        "cumulative_delta": -500_000,
        "total_volume": 1_100_000,
        "institutional_block_buys": 2_000,
        "institutional_block_sells": 55_000
    }

    signal_bullish = tech_agent.analyze(
        symbol="HDFCBANK",
        current_price=1650.0,
        ema20=1650.0,
        ema50=1640.0,
        ema200=1620.0,
        adx=22.0,
        rsi14=56.0,
        macd_hist=1.0,
        atr14=16.0,
        vwap=1648.0,
        volume_ratio=1.1,
        orderflow=None
    )

    signal_bearish_flow = tech_agent.analyze(
        symbol="HDFCBANK",
        current_price=1650.0,
        ema20=1650.0,
        ema50=1640.0,
        ema200=1620.0,
        adx=22.0,
        rsi14=56.0,
        macd_hist=1.0,
        atr14=16.0,
        vwap=1648.0,
        volume_ratio=1.1,
        orderflow=bearish_orderflow
    )

    # Bearish orderflow must reduce composite score
    assert signal_bearish_flow.features["tech_score"] < signal_bullish.features["tech_score"]
    assert signal_bearish_flow.features["orderflow_regime"] == "DISTRIBUTION"
