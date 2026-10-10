"""Unit tests for high-accuracy SHORT position execution across all 3 agents, risk engine, and broker."""
import pytest
from datetime import datetime
from src.core.constants import SignalDirection, OrderSide, ProductType, RiskAction, ExitReason, OrderStatus, TradingHorizon
from src.core.models import TradeProposal, PortfolioState, Position, FundamentalSignal, TechnicalSignal, ConsensusResult
from src.data.feed import Quote, CompanyFundamentals, MacroContext
from src.risk.engine import DeterministicRiskEngine
from src.broker.paper import PaperBroker
from src.agents.agent1_fundamental import FundamentalAnalystAgent
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.agents.agent3_execution import ExecutionAgent
from src.memory.journal import TradeJournal
from src.orchestrator.pipeline import TradingOrchestrator
from src.data.universe import NIFTY50_UNIVERSE, ORDER_FLOW_PROFILES, TECHNICAL_PROFILES, SMC_PROFILES

@pytest.fixture
def empty_portfolio():
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

def test_agent2_short_signal_generation_and_gate_confluence():
    """Verify that Agent 2 generates a high-confidence SHORT signal when all 8 gates confirm."""
    agent = TechnicalAnalystAgent()
    px = 3000.0

    orderflow = {
        "cumulative_volume_delta": -250000,
        "bid_depth_qty": 120000,
        "ask_depth_qty": 350000,
        "buy_volume": 400000,
        "sell_volume": 850000,
        "total_volume": 1250000,
        "institutional_block_buys": 5000,
        "institutional_block_sells": 45000
    }

    smc = {
        "symbol": "TCS",
        "current_price": px,
        "market_structure": "BEARISH_BOS",
        "swing_high": px * 1.03,
        "swing_low": px * 0.95,
        "liquidity_event": "BSL_SWEPT",
        "bsl_price": px * 1.032,
        "ssl_price": px * 0.948,
        "dealing_range_high": px * 1.04,
        "dealing_range_low": px * 0.95,
        "order_blocks": [
            {
                "ob_type": "BEARISH_OB",
                "top_price": px * 1.008,
                "bottom_price": px * 0.996,
                "midpoint": px * 1.002,
                "mitigated": False,
                "volume_displacement": 1.75,
                "is_price_in_zone": True
            }
        ],
        "fair_value_gaps": [
            {
                "fvg_type": "SIBI",
                "top_price": px * 1.004,
                "bottom_price": px * 0.994,
                "consequent_encroachment": px * 0.999,
                "status": "UNFILLED",
                "is_price_in_fvg": True
            }
        ]
    }

    pre_market = {
        "symbol": "TCS",
        "prev_close": round(px * 1.015, 2),
        "iep_price": px,
        "iep_volume": 35000,
        "avg_pre_market_volume_20d": 20000,
        "total_buy_qty": 30000,
        "total_sell_qty": 95000,
        "gift_nifty_change_pct": -0.40
    }

    sig = agent.analyze(
        symbol="TCS",
        current_price=px,
        ema20=px * 1.012,     # Price < EMA20 < EMA50 < EMA200 (Strong Bearish)
        ema50=px * 1.025,
        ema200=px * 1.060,
        adx=34.0,             # Gate 1: ADX >= 32
        rsi14=34.0,           # Gate 3: 25 <= RSI <= 43
        macd_hist=-3.5,       # Negative MACD histogram
        atr14=px * 0.015,
        vwap=px * 1.008,      # Gate 5: Price < VWAP
        volume_ratio=1.65,    # Gate 4: Volume ratio >= 1.40
        orderflow=orderflow,
        smc=smc,
        pre_market=pre_market,
        portfolio_capital=1_000_000.0
    )

    assert sig.direction == SignalDirection.SHORT
    assert sig.confidence >= 0.75
    assert sig.win_prob >= 0.78
    assert sig.features["gate_passed"] is True
    assert sig.stop_loss == round(px * 1.05, 2)  # Stop loss is above entry (+5%)
    assert sig.target == round(px * 0.82, 2)     # Target is below entry (-18%)
    assert sig.payoff_ratio >= 3.0

def test_agent1_and_agent2_short_consensus():
    """Verify that Agent 3 reaches high-conviction consensus on SHORT signals."""
    risk_engine = DeterministicRiskEngine()
    agent3 = ExecutionAgent(risk_engine=risk_engine)

    fund_sig = FundamentalSignal(
        symbol="TCS",
        timestamp=datetime.now(),
        direction=SignalDirection.SHORT,
        confidence=0.55,
        horizon=TradingHorizon.INTRADAY,
        rationale=["Multi-timeframe composite 32.0 -> SHORT bias"],
        features={"fund_score": 32.0}
    )

    tech_sig = TechnicalSignal(
        symbol="TCS",
        timestamp=datetime.now(),
        direction=SignalDirection.SHORT,
        confidence=0.88,
        horizon=TradingHorizon.INTRADAY,
        rationale=["High win-rate gate passed"],
        features={"gate_passed": True, "adx": 34.0},
        entry=3000.0,
        stop_loss=3150.0,
        target=2460.0,
        win_prob=0.88,
        payoff_ratio=3.6,
        kelly_fraction=0.90,
        suggested_position_value=900000.0
    )

    consensus = agent3.evaluate_consensus(fund_sig, tech_sig)
    assert consensus.consensus_reached is True
    assert consensus.direction == SignalDirection.SHORT
    assert consensus.combined_conviction >= 0.70

    # Build proposal
    portfolio = PortfolioState(
        total_capital=1_000_000.0, available_cash=1_000_000.0, utilized_margin=0.0,
        realized_daily_pnl=0.0, unrealized_daily_pnl=0.0, weekly_realized_pnl=0.0,
        peak_capital=1_000_000.0, open_positions={}, sector_exposure={}, trades_count_today=0
    )

    proposal = agent3.build_trade_proposal(consensus, tech_sig, portfolio, sector="IT")
    assert proposal is not None
    assert proposal.side == OrderSide.SELL
    assert proposal.product_type == ProductType.MIS
    assert proposal.entry_price == 3000.0
    assert proposal.stop_loss == 3150.0
    assert proposal.target_price == 2460.0
    assert proposal.suggested_quantity == 300  # 90% capital = 900,000 / 3000 = 300

def test_risk_engine_approves_short_mis_proposal(empty_portfolio):
    """Verify that DeterministicRiskEngine approves a SHORT MIS proposal with 5x leverage."""
    risk_engine = DeterministicRiskEngine()
    prop = TradeProposal(
        proposal_id="PROP-SHORT-01",
        symbol="TCS",
        sector="IT",
        side=OrderSide.SELL,
        product_type=ProductType.MIS,
        entry_price=3000.0,
        stop_loss=3150.0,
        target_price=2460.0,
        suggested_quantity=300,
        suggested_risk_amount=45000.0,
        kelly_fraction=0.90,
        calibrated_win_prob=0.88,
        payoff_ratio=3.6,
        timestamp=datetime.now()
    )

    verdict = risk_engine.evaluate_proposal(prop, empty_portfolio, enforce_timing=False)
    assert verdict.action in [RiskAction.APPROVED, RiskAction.DOWNSIZED]
    assert verdict.approved_quantity == 300
    assert verdict.approved_risk_amount == 45000.0

def test_paper_broker_short_bracket_execution_and_profit_target():
    """Verify that PaperBroker executes SHORT order and books profit when price drops to target."""
    broker = PaperBroker(initial_capital=1_000_000.0, slippage_pct=0.0)
    broker.connect()

    # Submit SHORT bracket order
    order = broker.submit_bracket_order(
        symbol="TCS",
        side="SELL",
        quantity=300,
        entry_price=3000.0,
        stop_loss=3150.0,
        target_price=2460.0,
        sector="IT"
    )

    assert order.status == OrderStatus.FILLED
    assert order.side == OrderSide.SELL
    assert "TCS" in broker.positions
    pos = broker.positions["TCS"]
    assert pos.side == OrderSide.SELL
    assert pos.entry_price == 3000.0
    assert pos.quantity == 300

    # Margin check: 20% of 900,000 = 180,000 deducted
    assert abs(broker.capital - 820_000.0) < 1.0

    # Tick 1: Price drops to 2760 (-8%), trailing stop ratchets downward to +4% above 2760 = 2870.4
    broker.update_price_tick("TCS", 2760.0)
    pos = broker.positions["TCS"]
    assert pos.unrealized_pnl == (3000.0 - 2760.0) * 300  # +72,000
    assert pos.trailing_stop <= 2871.0

    # Tick 2: Price hits target price 2460 (-18% drop) -> Position closes with profit!
    record = broker.update_price_tick("TCS", 2460.0)
    assert record is not None
    assert record.exit_reason == ExitReason.TARGET
    assert "TCS" not in broker.positions
    assert record.gross_pnl == (3000.0 - 2460.0) * 300  # +162,000
    assert record.net_pnl > 161_000.0
    assert len(broker.completed_trades) == 1
    # Capital should be initial + net_pnl
    assert broker.capital > 1_160_000.0

def test_paper_broker_short_stop_loss_trigger():
    """Verify that PaperBroker exits SHORT position with controlled loss when price rises to stop loss."""
    broker = PaperBroker(initial_capital=1_000_000.0, slippage_pct=0.0)
    broker.connect()

    broker.submit_bracket_order(
        symbol="BAJFINANCE",
        side="SELL",
        quantity=100,
        entry_price=7000.0,
        stop_loss=7350.0,     # +5% SL
        target_price=5740.0,   # -18% Target
        sector="NBFC"
    )

    assert "BAJFINANCE" in broker.positions

    # Price spikes to 7350 (+5% rise) -> Hit stop loss
    record = broker.update_price_tick("BAJFINANCE", 7350.0)
    assert record is not None
    assert record.exit_reason == ExitReason.STOP_LOSS
    assert "BAJFINANCE" not in broker.positions
    assert record.gross_pnl == (7000.0 - 7350.0) * 100  # -35,000
    assert broker.daily_realized_pnl < 0.0

def test_day_profit_potential_symmetric_for_short():
    """Verify compute_day_profit_potential gives high alpha score for strong SHORT setups."""
    orch = TradingOrchestrator(
        agent1=FundamentalAnalystAgent(),
        agent2=TechnicalAnalystAgent(),
        agent3=ExecutionAgent(risk_engine=DeterministicRiskEngine()),
        risk_engine=DeterministicRiskEngine(),
        broker=PaperBroker(),
        journal=TradeJournal(db_path=":memory:")
    )

    of_bearish = {
        "cumulative_volume_delta": -350000,
        "bid_depth_qty": 150000,
        "ask_depth_qty": 400000
    }
    smc_bearish = {
        "bias": "BEARISH",
        "liquidity_event": "BSL_SWEPT"
    }
    pm_bearish = {
        "pre_market_regime": "BEARISH_BREAKDOWN",
        "pre_market_vote": -1.0
    }

    metrics = orch.compute_day_profit_potential(
        win_prob=0.95,
        fund_score=25.0,  # Weak fundamentals = strong conviction for SHORT
        adx=35.0,
        volume_ratio=1.75,
        orderflow=of_bearish,
        smc=smc_bearish,
        pre_market=pm_bearish,
        direction=SignalDirection.SHORT,
        target_pct=18.0,
        stop_pct=5.0
    )

    assert metrics["direction"] == "SHORT"
    assert metrics["day_profit_potential_score"] > 50.0
    assert metrics["fund_factor"] > 1.0
    assert metrics["orderflow_factor"] > 1.0
    assert metrics["smc_factor"] > 1.0
    assert metrics["pre_market_factor"] > 1.0
