"""Unit tests for Single Company Trade of the Day selection and 5x margin execution."""
import pytest
from datetime import datetime
from src.core.constants import OrderSide, ProductType, RiskAction
from src.core.models import TradeProposal, PortfolioState, Position
from src.data.feed import Quote, CompanyFundamentals, MacroContext
from src.risk.engine import DeterministicRiskEngine
from src.broker.paper import PaperBroker
from src.agents.agent1_fundamental import FundamentalAnalystAgent
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.agents.agent3_execution import ExecutionAgent
from src.memory.journal import TradeJournal
from src.orchestrator.pipeline import TradingOrchestrator
from src.data.universe import NIFTY50_UNIVERSE, ORDER_FLOW_PROFILES, TECHNICAL_PROFILES

@pytest.fixture
def risk_engine_single():
    return DeterministicRiskEngine()  # Default max_open_positions = 1

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

def test_risk_engine_enforces_single_open_position_default(risk_engine_single, empty_portfolio):
    """Verify that default RiskEngine allows only 1 concurrent position and rejects a 2nd trade."""
    assert risk_engine_single.max_open_positions == 1

    # First trade proposal
    prop1 = TradeProposal(
        proposal_id="PROP-01", symbol="TATAMOTORS", side=OrderSide.BUY,
        entry_price=1000.0, stop_loss=950.0, target_price=1180.0,
        suggested_quantity=900, suggested_risk_amount=45000.0,
        kelly_fraction=0.05, calibrated_win_prob=0.975, payoff_ratio=3.6,
        product_type=ProductType.MIS, timestamp=datetime.now()
    )

    verdict1 = risk_engine_single.evaluate_proposal(prop1, empty_portfolio, enforce_timing=False)
    assert verdict1.action in [RiskAction.APPROVED, RiskAction.DOWNSIZED]
    assert verdict1.approved_quantity > 0

    # Add 1 position to portfolio
    empty_portfolio.open_positions["TATAMOTORS"] = Position(
        position_id="POS-01", symbol="TATAMOTORS", sector="Auto",
        side=OrderSide.BUY, product_type=ProductType.MIS, quantity=verdict1.approved_quantity,
        entry_price=1000.0, current_price=1000.0, stop_loss=950.0,
        target_price=1180.0, trailing_stop=950.0, opened_at=datetime.now(),
        last_updated_at=datetime.now()
    )

    # Second trade proposal must be vetoed
    prop2 = TradeProposal(
        proposal_id="PROP-02", symbol="RELIANCE", side=OrderSide.BUY,
        entry_price=2900.0, stop_loss=2755.0, target_price=3422.0,
        suggested_quantity=300, suggested_risk_amount=43500.0,
        kelly_fraction=0.05, calibrated_win_prob=0.975, payoff_ratio=3.6,
        product_type=ProductType.MIS, timestamp=datetime.now()
    )

    verdict2 = risk_engine_single.evaluate_proposal(prop2, empty_portfolio, enforce_timing=False)
    assert verdict2.action == RiskAction.VETOED
    assert "MAX_POSITIONS_REACHED" in verdict2.rules_triggered
    assert "Single Company Trade Policy" in verdict2.reason

def test_compute_day_profit_potential_calculation():
    """Verify that profit potential score accounts for win prob, 5x leverage, fundamentals, and order flow."""
    orch = TradingOrchestrator(
        agent1=FundamentalAnalystAgent(),
        agent2=TechnicalAnalystAgent(),
        agent3=ExecutionAgent(risk_engine=DeterministicRiskEngine()),
        risk_engine=DeterministicRiskEngine(),
        broker=PaperBroker(),
        journal=TradeJournal(db_path=":memory:")
    )

    orderflow_strong = {
        "cumulative_volume_delta": 350000,
        "bid_depth_qty": 400000,
        "ask_depth_qty": 200000
    }

    metrics = orch.compute_day_profit_potential(
        win_prob=0.975,
        fund_score=85.0,
        adx=32.0,
        volume_ratio=1.8,
        orderflow=orderflow_strong,
        target_pct=18.0,
        stop_pct=5.0
    )

    # EV = 0.975 * 18 - 0.025 * 5 = 17.55 - 0.125 = 17.425
    assert metrics["expected_profit_pct"] == 17.42 or abs(metrics["expected_profit_pct"] - 17.43) < 0.1
    # 5x leverage EV = 17.43 * 5 = ~87.1%
    assert abs(metrics["leveraged_expected_profit_pct"] - 87.1) < 1.0
    assert metrics["day_profit_potential_score"] > 50.0
    assert metrics["fund_factor"] > 1.0
    assert metrics["momentum_factor"] > 1.0
    assert metrics["orderflow_factor"] > 1.0

def test_full_pipeline_selects_and_executes_single_best_trade():
    """Verify end-to-end that across candidates, only the #1 top profit candidate is traded."""
    broker = PaperBroker(initial_capital=1_000_000.0)
    broker.connect()
    risk_engine = DeterministicRiskEngine()
    orch = TradingOrchestrator(
        agent1=FundamentalAnalystAgent(),
        agent2=TechnicalAnalystAgent(),
        agent3=ExecutionAgent(risk_engine=risk_engine),
        risk_engine=risk_engine,
        broker=broker,
        journal=TradeJournal(db_path=":memory:")
    )

    macro = MacroContext(
        timestamp=datetime.now(), nifty50_close=25450.0,
        nifty50_1w_return=1.45, nifty50_1m_return=3.80, india_vix=13.4,
        advance_decline_ratio=1.65, fii_net_flow_5d_cr=4500.0,
        dii_net_flow_5d_cr=3200.0, crude_oil_brent=74.5, usd_inr=83.85
    )

    # Evaluate 3 candidates
    candidates = ["TATAMOTORS", "COALINDIA", "TCS"]
    results = []

    for sym in candidates:
        cdata = NIFTY50_UNIVERSE[sym]
        px = cdata["price"]
        tp = TECHNICAL_PROFILES.get(sym, {})
        quote = Quote(symbol=sym, timestamp=datetime.now(), last_price=px, bid_price=px-0.2, ask_price=px+0.2, volume=2_000_000)
        funds = CompanyFundamentals(
            symbol=sym, sector=cdata.get("sector", "EQUITY"),
            pe_ratio=cdata.get("pe", 25.0), sector_pe=cdata.get("sector_pe", 25.0),
            pb_ratio=cdata.get("pb", 3.0), roe_percent=cdata.get("roe", 15.0),
            roce_percent=cdata.get("roce", 18.0), debt_to_equity=cdata.get("de", 0.5),
            revenue_growth_yoy=cdata.get("rev_g", 10.0), pat_growth_yoy=cdata.get("pat_g", 12.0),
            promoter_holding_percent=cdata.get("promoter", 50.0), promoter_pledge_percent=cdata.get("pledge", 0.0),
            is_results_due_in_24h=cdata.get("event", False)
        )
        tech_inputs = {
            "ema20": px * tp.get("ema20_r", 0.995), "ema50": px * tp.get("ema50_r", 0.980),
            "ema200": px * tp.get("ema200_r", 0.940), "adx": tp.get("adx", 22.0),
            "rsi14": tp.get("rsi14", 50.0), "macd_hist": tp.get("macd_hist", 0.5),
            "atr14": px * 0.012, "vwap": px, "volume_ratio": tp.get("volume_ratio", 1.0),
            "sector_rs_score": 65.0, "news_sentiment_score": 0.3,
            "orderflow": ORDER_FLOW_PROFILES.get(sym, {})
        }
        res = orch.run_cycle_for_symbol(
            symbol=sym, sector=cdata.get("sector", "EQUITY"),
            quote=quote, macro=macro, fundamentals=funds,
            technical_inputs=tech_inputs, enforce_timing=False,
            execute_order=False
        )
        results.append(res)

    # Filter qualified and rank
    qualified = [r for r in results if r.get("consensus_reached") and r.get("risk_verdict") and r.get("risk_verdict").approved_quantity > 0]
    assert len(qualified) >= 2, "Expected at least 2 candidates to qualify"

    qualified.sort(key=lambda x: x["profit_metrics"]["day_profit_potential_score"], reverse=True)
    top_pick = qualified[0]

    # Execute trade for ONLY the top pick
    order = orch.execute_approved_trade(
        symbol=top_pick["symbol"],
        sector=top_pick["sector"],
        proposal=top_pick["proposal"],
        risk_verdict=top_pick["risk_verdict"],
        fund_signal=top_pick["fund_signal"],
        tech_signal=top_pick["tech_signal"],
        cycle_id=top_pick["cycle_id"],
        decision_id=top_pick["decision_id"]
    )

    assert order is not None
    assert len(broker.positions) == 1
    assert top_pick["symbol"] in broker.positions

    # Verify 5x margin: blocked margin deducted from capital is 20%
    pos = broker.positions[top_pick["symbol"]]
    expected_margin_cash = pos.entry_price * pos.quantity * 0.20
    blocked_cash = 1_000_000.0 - broker.capital
    assert abs(blocked_cash - expected_margin_cash) < 1.0
