"""Unit and Integration Tests for Indian Stock Market Pre-Market Session Analysis in Agent 2."""

import pytest
from datetime import datetime
from src.core.constants import SignalDirection
from src.data.feed import Quote, CompanyFundamentals, MacroContext
from src.data.pre_market import (
    PreMarketData,
    PreMarketAnalysis,
    PreMarketGapType,
    PreMarketRegime,
    compute_pre_market_metrics,
)
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.data.universe import PRE_MARKET_PROFILES, NIFTY50_UNIVERSE
from src.data.daily_updater import DailyDataManager
from src.orchestrator.pipeline import TradingOrchestrator
from src.broker.paper import PaperBroker
from src.memory.journal import TradeJournal
from src.agents.agent1_fundamental import FundamentalAnalystAgent
from src.agents.agent3_execution import ExecutionAgent
from src.risk.engine import DeterministicRiskEngine


# ==============================================================================
# 1. PURE PRE-MARKET COMPUTATION TESTS
# ==============================================================================

def test_compute_pre_market_bullish_runaway():
    """Test BULLISH_RUNAWAY regime with strong gap up, buy imbalance and volume surge."""
    data = PreMarketData(
        symbol="RELIANCE",
        prev_close=2950.0,
        iep_price=2985.0,  # +1.19% gap up
        iep_volume=45000,
        avg_pre_market_volume_20d=25000,  # 1.8x surge
        total_buy_qty=120000,
        total_sell_qty=50000,             # +0.41 imbalance
        gift_nifty_change_pct=0.45
    )
    analysis = compute_pre_market_metrics(data)
    assert analysis.symbol == "RELIANCE"
    assert analysis.gap_pct == pytest.approx(1.19, abs=0.01)
    assert analysis.gap_type == PreMarketGapType.MODERATE_GAP_UP
    assert analysis.pre_market_regime == PreMarketRegime.BULLISH_RUNAWAY
    assert analysis.order_imbalance_ratio > 0.35
    assert analysis.volume_surge_ratio == 1.8
    assert analysis.pre_market_score >= 0.70
    assert analysis.pre_market_vote == 1.0
    assert analysis.gift_nifty_alignment == 1.0
    assert "RUNAWAY" in analysis.rationale[0] or "CONVICTION" in analysis.rationale[1]


def test_compute_pre_market_gap_up_profit_taking():
    """Test GAP_UP_PROFIT_TAKING regime: gap up met with heavy ask depth (fade gap)."""
    data = PreMarketData(
        symbol="INFY",
        prev_close=1800.0,
        iep_price=1820.0,  # +1.11% gap up
        iep_volume=20000,
        avg_pre_market_volume_20d=20000,
        total_buy_qty=30000,
        total_sell_qty=85000,             # -0.478 sell imbalance
        gift_nifty_change_pct=0.10
    )
    analysis = compute_pre_market_metrics(data)
    assert analysis.pre_market_regime == PreMarketRegime.GAP_UP_PROFIT_TAKING
    assert analysis.order_imbalance_ratio < -0.20
    assert analysis.pre_market_score < 0.0
    assert analysis.pre_market_vote <= 0.0
    assert analysis.institutional_sentiment == "PROFIT_TAKING"


def test_compute_pre_market_bearish_breakdown():
    """Test BEARISH_BREAKDOWN regime: gap down with heavy sell queue and volume surge."""
    data = PreMarketData(
        symbol="TCS",
        prev_close=4200.0,
        iep_price=4135.0,  # -1.55% large gap down
        iep_volume=38000,
        avg_pre_market_volume_20d=24000,  # 1.58x surge
        total_buy_qty=35000,
        total_sell_qty=110000,            # -0.517 imbalance
        gift_nifty_change_pct=-0.40
    )
    analysis = compute_pre_market_metrics(data)
    assert analysis.gap_type == PreMarketGapType.LARGE_GAP_DOWN
    assert analysis.pre_market_regime == PreMarketRegime.BEARISH_BREAKDOWN
    assert analysis.pre_market_score <= -0.70
    assert analysis.pre_market_vote == -1.0
    assert analysis.gift_nifty_alignment == -1.0
    assert analysis.institutional_sentiment == "AGGRESSIVE_SELLING"


def test_compute_pre_market_gap_down_accumulation():
    """Test GAP_DOWN_ACCUMULATION: price gaps down but institutional bids absorb panic."""
    data = PreMarketData(
        symbol="SUNPHARMA",
        prev_close=1750.0,
        iep_price=1730.0,  # -1.14% gap down
        iep_volume=22000,
        avg_pre_market_volume_20d=20000,
        total_buy_qty=95000,
        total_sell_qty=40000,             # +0.407 buy imbalance
        gift_nifty_change_pct=0.10
    )
    analysis = compute_pre_market_metrics(data)
    assert analysis.pre_market_regime == PreMarketRegime.GAP_DOWN_ACCUMULATION
    assert analysis.pre_market_score > 0.30
    assert analysis.institutional_sentiment == "ACCUMULATION"


def test_compute_pre_market_balanced_open():
    """Test BALANCED_OPEN: flat opening within ±0.30% with balanced order book."""
    data = PreMarketData(
        symbol="HDFCBANK",
        prev_close=1650.0,
        iep_price=1652.0,  # +0.12% flat
        iep_volume=18000,
        avg_pre_market_volume_20d=18000,
        total_buy_qty=60000,
        total_sell_qty=58000,
        gift_nifty_change_pct=0.05
    )
    analysis = compute_pre_market_metrics(data)
    assert analysis.gap_type == PreMarketGapType.FLAT
    assert analysis.pre_market_regime == PreMarketRegime.BALANCED_OPEN
    assert -0.20 <= analysis.pre_market_score <= 0.20
    assert analysis.pre_market_vote == 0.0


# ==============================================================================
# 2. AGENT 2 TECHNICAL ANALYST INTEGRATION TESTS
# ==============================================================================

def test_agent2_weights_include_pre_market():
    """Verify Agent 2 analytical weights sum to 1.00 and include pre_market."""
    agent = TechnicalAnalystAgent()
    assert hasattr(agent, "w_pre_market")
    assert agent.w_pre_market == 0.15
    total_weights = (
        agent.w_trend
        + agent.w_momentum
        + agent.w_volume
        + agent.w_structure
        + agent.w_volatility
        + agent.w_orderflow
        + agent.w_smc
        + agent.w_pre_market
    )
    assert total_weights == pytest.approx(1.00, abs=0.001)


def test_agent2_gate8_blocks_long_on_bearish_pre_market_breakdown():
    """Test Gate 8: Reject LONG trade when pre-market regime is BEARISH_BREAKDOWN."""
    agent = TechnicalAnalystAgent(config={"thresholds": {"long_score": 0.40}})

    # Pre-market breakdown data
    pm_breakdown = {
        "prev_close": 3000.0,
        "iep_price": 2940.0,  # -2.0% gap down
        "iep_volume": 40000,
        "avg_pre_market_volume_20d": 20000,
        "total_buy_qty": 20000,
        "total_sell_qty": 90000,
        "gift_nifty_change_pct": -0.50
    }

    # High bullish technical parameters (ordinarily passes)
    signal = agent.analyze(
        symbol="RELIANCE",
        current_price=2940.0,
        ema20=2900.0,
        ema50=2850.0,
        ema200=2750.0,
        adx=32.0,
        rsi14=62.0,
        macd_hist=1.2,
        atr14=30.0,
        vwap=2930.0,
        volume_ratio=1.65,
        pre_market=pm_breakdown
    )

    # Must be VETOED by Gate 8
    assert signal.direction == SignalDirection.NEUTRAL
    assert signal.features["gate_passed"] is False
    assert any("Pre-Market Gate" in r for r in signal.rationale)


def test_agent2_gate8_blocks_short_on_bullish_runaway():
    """Test Gate 8: Reject SHORT trade when pre-market regime is BULLISH_RUNAWAY."""
    agent = TechnicalAnalystAgent(config={"thresholds": {"short_score": -0.40}})

    pm_runaway = {
        "prev_close": 2900.0,
        "iep_price": 2950.0,  # +1.72% runaway gap
        "iep_volume": 45000,
        "avg_pre_market_volume_20d": 20000,
        "total_buy_qty": 110000,
        "total_sell_qty": 35000,
        "gift_nifty_change_pct": 0.60
    }

    # Bearish technical parameters
    signal = agent.analyze(
        symbol="TCS",
        current_price=2950.0,
        ema20=3000.0,
        ema50=3050.0,
        ema200=3150.0,
        adx=34.0,
        rsi14=32.0,
        macd_hist=-1.5,
        atr14=35.0,
        vwap=2960.0,
        volume_ratio=1.60,
        pre_market=pm_runaway
    )

    assert signal.direction == SignalDirection.NEUTRAL
    assert signal.features["gate_passed"] is False
    assert any("Pre-Market Gate" in r for r in signal.rationale)


def test_agent2_passes_gate8_with_aligned_bullish_pre_market():
    """Test Agent 2 emits HIGH WIN-RATE LONG when all 8 gates (including Pre-Market) align."""
    agent = TechnicalAnalystAgent()

    pm_bullish = {
        "prev_close": 2950.0,
        "iep_price": 2985.0,  # +1.19% gap up
        "iep_volume": 42000,
        "avg_pre_market_volume_20d": 24000,
        "total_buy_qty": 120000,
        "total_sell_qty": 48000,
        "gift_nifty_change_pct": 0.40
    }

    signal = agent.analyze(
        symbol="RELIANCE",
        current_price=2985.0,
        ema20=2940.0,
        ema50=2900.0,
        ema200=2800.0,
        adx=34.0,
        rsi14=64.0,
        macd_hist=1.8,
        atr14=32.0,
        vwap=2965.0,
        volume_ratio=1.70,
        pre_market=pm_bullish
    )

    assert signal.direction == SignalDirection.LONG
    assert signal.features["gate_passed"] is True
    assert signal.features["pre_market_regime"] == PreMarketRegime.BULLISH_RUNAWAY.value
    assert signal.features["pre_market_vote"] == 1.0
    assert signal.confidence >= 0.70
    assert signal.win_prob >= 0.85
    assert any("8 confirmation layers" in r for r in signal.rationale)


def test_agent2_daily_pre_market_update():
    """Test Agent 2 caching and updating daily pre-market profiles."""
    agent = TechnicalAnalystAgent()
    agent.update_daily_technicals(
        symbol="TATAMOTORS",
        tech_dict={"adx": 30.0, "rsi14": 60.0},
        pre_market_dict={"gap_pct": 1.25, "pre_market_regime": "BULLISH_RUNAWAY"}
    )
    profile = agent.get_daily_profile("TATAMOTORS")
    assert "pre_market" in profile
    assert profile["pre_market"]["gap_pct"] == 1.25


# ==============================================================================
# 3. DAILY DATA MANAGER & UNIVERSE PROFILES TESTS
# ==============================================================================

def test_universe_pre_market_profiles_defined():
    """Verify all 50 Nifty stocks have baseline pre-market profiles defined."""
    assert len(PRE_MARKET_PROFILES) >= 50
    for sym in ["RELIANCE", "TCS", "INFY", "TATAMOTORS", "HDFCBANK"]:
        assert sym in PRE_MARKET_PROFILES
        prof = PRE_MARKET_PROFILES[sym]
        assert "iep_price" in prof
        assert "prev_close" in prof
        assert "total_buy_qty" in prof
        assert "total_sell_qty" in prof


def test_daily_data_manager_initializes_pre_market():
    """Verify DailyDataManager tracks daily_pre_market for all symbols."""
    ddm = DailyDataManager()
    assert len(ddm.daily_pre_market) >= 50
    rel = ddm.get_pre_market_data("RELIANCE")
    assert rel["symbol"] == "RELIANCE"
    assert "gap_pct" in rel
    assert "pre_market_regime" in rel
    assert "order_imbalance_ratio" in rel


def test_daily_data_manager_rollover_updates_pre_market():
    """Verify perform_daily_rollover evolves pre-market metrics for all stocks."""
    ddm = DailyDataManager()
    initial_iep = ddm.daily_pre_market["RELIANCE"]["iep_price"]
    res = ddm.perform_daily_rollover(force=True, market_bias="BULLISH")
    assert res["status"] == "SUCCESS"
    assert len(ddm.daily_pre_market) >= 50
    status = ddm.get_status()
    assert "total_pre_market_synced" in status
    assert status["total_pre_market_synced"] >= 50


# ==============================================================================
# 4. ORCHESTRATOR & DAY PROFIT POTENTIAL INTEGRATION
# ==============================================================================

def test_profit_potential_factors_in_pre_market():
    """Verify compute_day_profit_potential applies boost for bullish pre-market runaway."""
    agent1 = FundamentalAnalystAgent()
    agent2 = TechnicalAnalystAgent()
    risk_engine = DeterministicRiskEngine()
    broker = PaperBroker()
    journal = TradeJournal(db_path=":memory:")
    agent3 = ExecutionAgent(risk_engine=risk_engine)
    orch = TradingOrchestrator(
        agent1=agent1, agent2=agent2, agent3=agent3,
        risk_engine=risk_engine, broker=broker, journal=journal
    )

    of = {"cumulative_volume_delta": 300000, "bid_depth_qty": 150000, "ask_depth_qty": 60000}
    smc = {"bias": "BULLISH", "liquidity_event": "SSL_SWEPT"}

    pm_bull = {"pre_market_regime": "BULLISH_RUNAWAY", "pre_market_vote": 1.0}
    pm_bear = {"pre_market_regime": "BEARISH_BREAKDOWN", "pre_market_vote": -1.0}

    res_bull = orch.compute_day_profit_potential(
        win_prob=0.90, fund_score=85.0, adx=32.0, volume_ratio=1.6,
        orderflow=of, smc=smc, pre_market=pm_bull
    )
    res_bear = orch.compute_day_profit_potential(
        win_prob=0.90, fund_score=85.0, adx=32.0, volume_ratio=1.6,
        orderflow=of, smc=smc, pre_market=pm_bear
    )

    assert res_bull["pre_market_factor"] > 1.0
    assert res_bear["pre_market_factor"] < 1.0
    assert res_bull["day_profit_potential_score"] > res_bear["day_profit_potential_score"]


def test_pipeline_run_cycle_returns_pre_market_data():
    """Test complete pipeline cycle includes pre-market analysis in output."""
    agent1 = FundamentalAnalystAgent()
    agent2 = TechnicalAnalystAgent()
    risk_engine = DeterministicRiskEngine()
    broker = PaperBroker()
    journal = TradeJournal(db_path=":memory:")
    agent3 = ExecutionAgent(risk_engine=risk_engine)
    orch = TradingOrchestrator(
        agent1=agent1, agent2=agent2, agent3=agent3,
        risk_engine=risk_engine, broker=broker, journal=journal
    )

    now = datetime.now()
    quote = Quote(
        symbol="RELIANCE",
        timestamp=now,
        last_price=2985.0,
        bid_price=2984.5,
        ask_price=2985.5,
        volume=2500000
    )
    macro = MacroContext(
        timestamp=now,
        nifty50_close=25400.0,
        nifty50_1w_return=1.2,
        nifty50_1m_return=3.5,
        india_vix=13.5,
        advance_decline_ratio=1.5,
        fii_net_flow_5d_cr=3500.0,
        dii_net_flow_5d_cr=2800.0,
        crude_oil_brent=74.0,
        usd_inr=83.9
    )
    fund = CompanyFundamentals(
        symbol="RELIANCE",
        sector="Energy",
        pe_ratio=24.0,
        sector_pe=26.0,
        pb_ratio=2.8,
        roe_percent=16.0,
        roce_percent=18.0,
        debt_to_equity=0.45,
        revenue_growth_yoy=14.0,
        pat_growth_yoy=16.0,
        promoter_holding_percent=50.3,
        promoter_pledge_percent=0.0
    )

    tech_inputs = {
        "ema20": 2940.0,
        "ema50": 2900.0,
        "ema200": 2800.0,
        "adx": 34.0,
        "rsi14": 64.0,
        "macd_hist": 1.8,
        "atr14": 32.0,
        "vwap": 2965.0,
        "volume_ratio": 1.70,
        "pre_market": PRE_MARKET_PROFILES["RELIANCE"]
    }

    result = orch.run_cycle_for_symbol(
        symbol="RELIANCE",
        sector="Energy",
        quote=quote,
        macro=macro,
        fundamentals=fund,
        technical_inputs=tech_inputs,
        enforce_timing=False,
        execute_order=False
    )

    assert "pre_market" in result
    pm = result["pre_market"]
    assert pm["pre_market_regime"] == PreMarketRegime.BULLISH_RUNAWAY.value
    assert pm["pre_market_vote"] == 1.0
    assert "iep_price" in pm
    assert "volume_surge_ratio" in pm
