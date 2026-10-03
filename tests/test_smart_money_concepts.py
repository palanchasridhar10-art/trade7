"""Tests for Smart Money Concepts (SMC) Analysis Engine and Agent 2 Integration.

Covers:
1. Market Structure: Break of Structure (BOS), Change of Character (CHoCH), swings.
2. Liquidity Dynamics: Sell-Side Liquidity (SSL), Buy-Side Liquidity (BSL), Sweeps/Grabs, Inducement.
3. Price Inefficiencies: Unmitigated Order Blocks (OB) and Fair Value Gaps (FVG) / Imbalances (BISI / SIBI).
4. Dealing Range: Premium vs Discount zone pricing.
5. Agent 2 Confluence & Gate 7 Validation: SMC voting, weighting, and trade blocking on counter-institutional signals.
6. Pipeline integration and Universe SMC profiling.
"""

import pytest
from src.core.constants import SignalDirection
from src.data.smc import (
    SMCData,
    SMCAnalysis,
    MarketStructureType,
    LiquidityEventType,
    OrderBlockType,
    FVGType,
    OrderBlock,
    FairValueGap,
    compute_smc_metrics,
)
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.data.universe import SMC_PROFILES, NIFTY50_UNIVERSE

@pytest.fixture
def tech_agent():
    return TechnicalAnalystAgent()

def test_market_structure_bullish_bos():
    """Verify Bullish Break of Structure (BOS) scores positively and confirms trend continuation."""
    data = SMCData(
        symbol="RELIANCE",
        current_price=2950.0,
        market_structure=MarketStructureType.BULLISH_BOS,
        swing_high=2920.0,
        swing_low=2850.0,
        dealing_range_high=3000.0,
        dealing_range_low=2800.0
    )
    analysis = compute_smc_metrics(data)
    assert analysis.structure_score == 1.0
    assert analysis.market_structure == "BULLISH_BOS"
    assert any("Break of Structure" in r for r in analysis.rationale)

def test_market_structure_bearish_bos():
    """Verify Bearish Break of Structure (BOS) scores negatively."""
    data = SMCData(
        symbol="TCS",
        current_price=4100.0,
        market_structure=MarketStructureType.BEARISH_BOS,
        swing_high=4250.0,
        swing_low=4150.0,
        dealing_range_high=4300.0,
        dealing_range_low=4000.0
    )
    analysis = compute_smc_metrics(data)
    assert analysis.structure_score == -1.0
    assert analysis.market_structure == "BEARISH_BOS"

def test_market_structure_choch_reversals():
    """Verify CHoCH signals early trend character shift."""
    bull_choch = compute_smc_metrics(SMCData(
        symbol="HDFCBANK",
        current_price=1680.0,
        market_structure=MarketStructureType.BULLISH_CHOCH,
        swing_high=1670.0
    ))
    assert bull_choch.structure_score == 0.85

    bear_choch = compute_smc_metrics(SMCData(
        symbol="INFY",
        current_price=1850.0,
        market_structure=MarketStructureType.BEARISH_CHOCH,
        swing_low=1870.0
    ))
    assert bear_choch.structure_score == -0.85

def test_liquidity_ssl_swept_bullish():
    """Verify Sell-Side Liquidity (SSL) sweep Purge scores as high-conviction institutional accumulation."""
    data = SMCData(
        symbol="SBIN",
        current_price=805.0,
        market_structure=MarketStructureType.BULLISH_BOS,
        liquidity_event=LiquidityEventType.SSL_SWEPT,
        ssl_price=790.0,
        dealing_range_high=830.0,
        dealing_range_low=785.0
    )
    analysis = compute_smc_metrics(data)
    assert analysis.liquidity_score == 1.0
    assert analysis.liquidity_event == "SSL_SWEPT"
    assert any("Sell-Side Liquidity (SSL) swept" in r for r in analysis.rationale)

def test_liquidity_bsl_swept_bearish():
    """Verify Buy-Side Liquidity (BSL) sweep and rejection indicates institutional distribution trap."""
    data = SMCData(
        symbol="KOTAKBANK",
        current_price=1870.0,
        market_structure=MarketStructureType.BEARISH_BOS,
        liquidity_event=LiquidityEventType.BSL_SWEPT,
        bsl_price=1910.0,
        dealing_range_high=1920.0,
        dealing_range_low=1800.0
    )
    analysis = compute_smc_metrics(data)
    assert analysis.liquidity_score == -1.0
    assert analysis.liquidity_event == "BSL_SWEPT"
    assert any("Buy-Side Liquidity (BSL) swept" in r for r in analysis.rationale)

def test_price_inefficiency_order_block_and_fvg():
    """Verify unmitigated Bullish Order Block and BISI FVG detection and scoring."""
    ob = OrderBlock(
        ob_type=OrderBlockType.BULLISH_OB,
        top_price=2925.0,
        bottom_price=2900.0,
        midpoint=2912.5,
        mitigated=False,
        volume_displacement=1.9,
        is_price_in_zone=True
    )
    fvg = FairValueGap(
        fvg_type=FVGType.BISI,
        top_price=2930.0,
        bottom_price=2910.0,
        consequent_encroachment=2920.0,
        status="PARTIALLY_FILLED",
        is_price_in_fvg=True
    )
    data = SMCData(
        symbol="RELIANCE",
        current_price=2920.0,
        market_structure=MarketStructureType.BULLISH_BOS,
        liquidity_event=LiquidityEventType.SSL_SWEPT,
        order_blocks=[ob],
        fair_value_gaps=[fvg],
        dealing_range_high=3000.0,
        dealing_range_low=2850.0
    )
    analysis = compute_smc_metrics(data)
    assert analysis.ob_score == 1.0
    assert analysis.fvg_score == 0.85
    assert analysis.inefficiency_score > 0.80
    assert analysis.active_order_block is not None
    assert analysis.active_order_block["type"] == "BULLISH_OB"
    assert analysis.active_fvg is not None
    assert analysis.active_fvg["type"] == "BISI"

def test_dealing_range_discount_vs_premium():
    """Verify Discount zone provides institutional buying boost and Premium zone penalizes buying high."""
    # Price at 30% of range (Discount)
    data_discount = SMCData(
        symbol="ONGC",
        current_price=280.0,
        market_structure=MarketStructureType.BULLISH_BOS,
        dealing_range_high=310.0,
        dealing_range_low=270.0
    )
    analysis_disc = compute_smc_metrics(data_discount)
    assert analysis_disc.dealing_range_zone == "DISCOUNT"
    assert analysis_disc.dealing_range_pct < 48.0

    # Price at 80% of range (Premium)
    data_premium = SMCData(
        symbol="ONGC",
        current_price=302.0,
        market_structure=MarketStructureType.BULLISH_BOS,
        dealing_range_high=310.0,
        dealing_range_low=270.0
    )
    analysis_prem = compute_smc_metrics(data_premium)
    assert analysis_prem.dealing_range_zone == "PREMIUM"
    assert analysis_prem.dealing_range_pct > 75.0
    assert any("deep Premium" in r for r in analysis_prem.rationale)

def test_agent2_integrates_smc_into_signal(tech_agent):
    """Verify Agent 2 incorporates SMC into score, features, rationale, and directional decision."""
    smc_input = {
        "market_structure": "BULLISH_BOS",
        "swing_high": 3000.0,
        "swing_low": 2880.0,
        "liquidity_event": "SSL_SWEPT",
        "ssl_price": 2875.0,
        "dealing_range_high": 3020.0,
        "dealing_range_low": 2870.0,
        "order_blocks": [
            {
                "ob_type": "BULLISH_OB",
                "top_price": 2930.0,
                "bottom_price": 2910.0,
                "midpoint": 2920.0,
                "mitigated": False,
                "volume_displacement": 1.85,
                "is_price_in_zone": True
            }
        ],
        "fair_value_gaps": [
            {
                "fvg_type": "BISI",
                "top_price": 2935.0,
                "bottom_price": 2915.0,
                "consequent_encroachment": 2925.0,
                "status": "PARTIALLY_FILLED",
                "is_price_in_fvg": True
            }
        ]
    }

    orderflow_input = {
        "bid_depth_qty": 350_000,
        "ask_depth_qty": 200_000,
        "buy_volume": 1_200_000,
        "sell_volume": 800_000,
        "cumulative_delta": 400_000,
        "total_volume": 2_000_000,
        "institutional_block_buys": 60_000,
        "institutional_block_sells": 10_000
    }

    signal = tech_agent.analyze(
        symbol="RELIANCE",
        current_price=2925.0,
        ema20=2880.0,
        ema50=2840.0,
        ema200=2720.0,
        adx=32.0,
        rsi14=63.0,
        macd_hist=3.5,
        atr14=28.0,
        vwap=2910.0,
        volume_ratio=1.60,
        orderflow=orderflow_input,
        smc=smc_input,
        portfolio_capital=1_000_000.0
    )

    assert signal.direction == SignalDirection.LONG
    assert signal.confidence >= 0.70
    assert "smc_score" in signal.features
    assert "smc_vote" in signal.features
    assert "smc_structure" in signal.features
    assert signal.features["smc_structure"] == "BULLISH_BOS"
    assert signal.features["smc_liquidity_event"] == "SSL_SWEPT"
    assert signal.features["smc_vote"] == 1.0
    assert any("STRUCTURE" in r or "LIQUIDITY" in r or "ORDER BLOCK" in r for r in signal.rationale)

def test_agent2_gate7_blocks_long_on_bearish_bos_or_bsl_sweep():
    """Verify Gate 7 rejects LONG signals when SMC market structure or liquidity sweep is counter-trend."""
    # When tentative score is high enough to qualify, Gate 7 explicitly vetoes
    agent_with_gate_test = TechnicalAnalystAgent(config={"thresholds": {"long_score": 0.40}})

    smc_bearish_structure = {
        "market_structure": "BEARISH_BOS",
        "liquidity_event": "BSL_SWEPT",
        "bsl_price": 2940.0,
        "dealing_range_high": 2950.0,
        "dealing_range_low": 2800.0,
        "order_blocks": [],
        "fair_value_gaps": []
    }

    signal = agent_with_gate_test.analyze(
        symbol="RELIANCE",
        current_price=2930.0,
        ema20=2880.0,
        ema50=2840.0,
        ema200=2720.0,
        adx=32.0,
        rsi14=63.0,
        macd_hist=3.5,
        atr14=28.0,
        vwap=2910.0,
        volume_ratio=1.60,
        orderflow={
            "cumulative_delta": 300_000,
            "buy_volume": 1_000_000,
            "sell_volume": 700_000,
            "bid_depth_qty": 350_000,
            "ask_depth_qty": 200_000,
            "total_volume": 1_700_000,
            "institutional_block_buys": 60_000,
            "institutional_block_sells": 10_000
        },
        smc=smc_bearish_structure
    )

    # Gate 7 must block trade
    assert signal.direction == SignalDirection.NEUTRAL
    assert signal.features["gate_passed"] is False
    assert any("SMC Gate" in r for r in signal.rationale)

def test_agent2_gate7_blocks_short_on_bullish_bos_or_ssl_sweep():
    """Verify Gate 7 rejects SHORT signals when SMC shows Bullish BOS or SSL swept."""
    agent_with_gate_test = TechnicalAnalystAgent(config={"thresholds": {"short_score": -0.40}})

    smc_bullish_structure = {
        "market_structure": "BULLISH_BOS",
        "liquidity_event": "SSL_SWEPT",
        "ssl_price": 1620.0,
        "dealing_range_high": 1700.0,
        "dealing_range_low": 1600.0,
        "order_blocks": [],
        "fair_value_gaps": []
    }

    signal = agent_with_gate_test.analyze(
        symbol="HDFCBANK",
        current_price=1640.0,
        ema20=1660.0,
        ema50=1680.0,
        ema200=1720.0,
        adx=30.0,
        rsi14=38.0,
        macd_hist=-2.5,
        atr14=16.0,
        vwap=1655.0,
        volume_ratio=1.50,
        orderflow={
            "cumulative_delta": -300_000,
            "buy_volume": 600_000,
            "sell_volume": 900_000,
            "bid_depth_qty": 180_000,
            "ask_depth_qty": 320_000,
            "total_volume": 1_500_000,
            "institutional_block_buys": 5_000,
            "institutional_block_sells": 50_000
        },
        smc=smc_bullish_structure
    )

    # Gate 7 must block trade
    assert signal.direction == SignalDirection.NEUTRAL
    assert signal.features["gate_passed"] is False
    assert any("SMC Gate" in r for r in signal.rationale)

def test_universe_smc_profiles_completeness():
    """Verify all 50 stocks in NIFTY 50 have valid Smart Money Concepts profiles."""
    assert len(SMC_PROFILES) >= 50
    for sym in NIFTY50_UNIVERSE.keys():
        assert sym in SMC_PROFILES
        prof = SMC_PROFILES[sym]
        assert "market_structure" in prof
        assert "liquidity_event" in prof
        assert "dealing_range_high" in prof
        assert "dealing_range_low" in prof

def test_orchestrator_pipeline_integrates_smc():
    """Verify TradingOrchestrator runs the cycle with SMC and returns the structured smc dict."""
    from datetime import datetime
    from src.agents.agent1_fundamental import FundamentalAnalystAgent
    from src.agents.agent3_execution import ExecutionAgent
    from src.risk.engine import DeterministicRiskEngine
    from src.broker.paper import PaperBroker
    from src.memory.journal import TradeJournal
    from src.orchestrator.pipeline import TradingOrchestrator
    from src.data.feed import Quote, MacroContext, CompanyFundamentals

    risk_engine = DeterministicRiskEngine({
        "max_risk_per_trade_percent": 1.0,
        "max_open_positions": 1
    })
    orch = TradingOrchestrator(
        agent1=FundamentalAnalystAgent(),
        agent2=TechnicalAnalystAgent(),
        agent3=ExecutionAgent(risk_engine=risk_engine),
        risk_engine=risk_engine,
        broker=PaperBroker(),
        journal=TradeJournal(db_path=":memory:")
    )

    quote = Quote(symbol="RELIANCE", timestamp=datetime.now(), last_price=2925.0, bid_price=2924.8, ask_price=2925.2, volume=2_000_000)
    macro = MacroContext(
        timestamp=datetime.now(), nifty50_close=25400.0, nifty50_1w_return=1.2,
        nifty50_1m_return=3.5, india_vix=13.2, advance_decline_ratio=1.6,
        fii_net_flow_5d_cr=3500.0, dii_net_flow_5d_cr=2800.0, crude_oil_brent=74.0, usd_inr=83.8
    )
    fundamentals = CompanyFundamentals(
        symbol="RELIANCE", sector="Energy", pe_ratio=24.0, sector_pe=22.0,
        pb_ratio=2.4, roe_percent=10.0, roce_percent=12.0, debt_to_equity=0.4,
        revenue_growth_yoy=9.0, pat_growth_yoy=13.0, promoter_holding_percent=50.3,
        promoter_pledge_percent=0.0
    )

    tech_inputs = {
        "ema20": 2880.0,
        "ema50": 2840.0,
        "ema200": 2720.0,
        "adx": 32.0,
        "rsi14": 63.0,
        "macd_hist": 3.5,
        "atr14": 28.0,
        "vwap": 2910.0,
        "volume_ratio": 1.6,
        "orderflow": {
            "cumulative_delta": 400_000,
            "buy_volume": 1_200_000,
            "sell_volume": 800_000,
            "bid_depth_qty": 350_000,
            "ask_depth_qty": 200_000,
            "total_volume": 2_000_000,
            "institutional_block_buys": 60_000,
            "institutional_block_sells": 10_000
        },
        "smc": SMC_PROFILES.get("RELIANCE", {})
    }

    result = orch.run_cycle_for_symbol(
        symbol="RELIANCE",
        sector="Energy",
        quote=quote,
        macro=macro,
        fundamentals=fundamentals,
        technical_inputs=tech_inputs,
        enforce_timing=False,
        execute_order=False
    )

    assert "smc" in result
    assert "smc_score" in result["smc"]
    assert "market_structure" in result["smc"]
    assert result["smc"]["market_structure"] == "BULLISH_BOS"
    assert "liquidity_event" in result["smc"]
    assert result["smc"]["liquidity_event"] == "SSL_SWEPT"
    assert "dealing_range_zone" in result["smc"]
    assert "profit_metrics" in result
    assert "smc_factor" in result["profit_metrics"]
    assert result["profit_metrics"]["smc_factor"] >= 1.0

