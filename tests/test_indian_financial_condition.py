"""Tests for Indian Stock Market Financial Condition Fundamental Analysis and Automated Trade Execution.

Validates:
1. MacroContext Indian financial condition indicators (10Y G-Sec yield, Repo Rate, Banking Liquidity, CPI, PMI, Nifty PE, etc.)
2. Agent 1 IFCI calculation, regime classification (EXPANSIONARY / BALANCED / RESTRICTIVE), and multi-timeframe integration.
3. DailyDataManager dynamic daily rollover of Indian stock market financial conditions.
4. Auto-execution taking decisions from Agent 1 and Agent 2, selecting the single #1 top profit trade, and placing order with 5x broker margin.
"""

import pytest
from datetime import datetime, date
from src.data.feed import MacroContext, CompanyFundamentals, Quote
from src.agents.agent1_fundamental import FundamentalAnalystAgent
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.agents.agent3_execution import ExecutionAgent
from src.risk.engine import DeterministicRiskEngine
from src.broker.paper import PaperBroker
from src.memory.journal import TradeJournal
from src.orchestrator.pipeline import TradingOrchestrator
from src.data.daily_updater import DailyDataManager
from server import execute_single_best_trade, run_symbol_cycle
import server

@pytest.fixture
def macro_context():
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
        usd_inr=83.85,
        gsec_10y_yield=6.92,
        repo_rate=6.50,
        cpi_inflation=4.60,
        manufacturing_pmi=58.4,
        banking_system_liquidity_cr=45000.0,
        forex_reserves_usd_bn=692.0,
        nifty_pe=22.4,
        nifty_pe_5y_avg=21.8,
        gst_collection_cr=187000.0
    )

@pytest.fixture
def fundamentals():
    return CompanyFundamentals(
        symbol="RELIANCE",
        sector="ENERGY",
        pe_ratio=24.5,
        sector_pe=22.0,
        pb_ratio=2.8,
        roe_percent=14.2,
        roce_percent=16.8,
        debt_to_equity=0.45,
        revenue_growth_yoy=11.5,
        pat_growth_yoy=13.2,
        promoter_holding_percent=50.3,
        promoter_pledge_percent=0.0,
        is_results_due_in_24h=False,
        is_fo_ban=False
    )

def test_macro_context_indian_financial_conditions_defaults():
    """Verify that MacroContext initializes with valid Indian stock market financial conditions."""
    m = MacroContext(
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
    assert m.gsec_10y_yield == 6.92
    assert m.repo_rate == 6.50
    assert m.cpi_inflation == 4.60
    assert m.manufacturing_pmi == 58.4
    assert m.banking_system_liquidity_cr == 45000.0
    assert m.forex_reserves_usd_bn == 692.0
    assert m.nifty_pe == 22.4
    assert m.nifty_pe_5y_avg == 21.8
    assert m.gst_collection_cr == 187000.0

def test_agent1_ifci_scoring(macro_context):
    """Verify Agent 1 computes IFCI score, regime classification, and reasons."""
    agent1 = FundamentalAnalystAgent()
    score, reasons, indicators = agent1._score_indian_financial_conditions(macro_context)

    assert 0.0 <= score <= 100.0
    # With benign yield (6.92%), surplus liquidity (45,000 Cr), high PMI (58.4), score should be expansionary
    assert score >= 65.0
    assert indicators["gsec_10y_yield"] == 6.92
    assert indicators["manufacturing_pmi"] == 58.4
    assert indicators["banking_system_liquidity_cr"] == 45000.0
    assert len(reasons) >= 3

def test_agent1_ifci_regime_classification():
    """Verify IFCI classifies into EXPANSIONARY, BALANCED, and RESTRICTIVE regimes accurately."""
    agent1 = FundamentalAnalystAgent()

    # Expansionary macro
    exp_macro = MacroContext(
        timestamp=datetime.now(),
        nifty50_close=25450.0,
        nifty50_1w_return=1.45,
        nifty50_1m_return=3.80,
        advance_decline_ratio=1.65,
        crude_oil_brent=74.5,
        usd_inr=83.85,
        gsec_10y_yield=6.75,
        banking_system_liquidity_cr=80000.0,
        cpi_inflation=4.1,
        manufacturing_pmi=60.0,
        nifty_pe=19.5,
        india_vix=11.5,
        fii_net_flow_5d_cr=12000.0,
        dii_net_flow_5d_cr=8000.0
    )
    score_exp, _, _ = agent1._score_indian_financial_conditions(exp_macro)
    assert score_exp >= 65.0

    # Restrictive macro (High G-Sec yield, liquidity deficit, high inflation, contractionary PMI)
    rest_macro = MacroContext(
        timestamp=datetime.now(),
        nifty50_close=25450.0,
        nifty50_1w_return=-2.5,
        nifty50_1m_return=-5.0,
        advance_decline_ratio=0.5,
        crude_oil_brent=92.0,
        usd_inr=85.50,
        gsec_10y_yield=7.65,
        banking_system_liquidity_cr=-50000.0,
        cpi_inflation=6.8,
        manufacturing_pmi=48.2,
        nifty_pe=28.5,
        india_vix=22.0,
        fii_net_flow_5d_cr=-15000.0,
        dii_net_flow_5d_cr=-3000.0
    )
    score_rest, _, _ = agent1._score_indian_financial_conditions(rest_macro)
    assert score_rest < 45.0

def test_agent1_analyze_includes_indian_financial_conditions(macro_context, fundamentals):
    """Verify that agent1.analyze() incorporates IFCI in rationale and features."""
    agent1 = FundamentalAnalystAgent()
    signal = agent1.analyze(symbol="RELIANCE", fundamentals=fundamentals, macro=macro_context)

    assert "indian_financial_condition" in signal.features
    ifci = signal.features["indian_financial_condition"]
    assert "ifci_score" in ifci
    assert "ifci_status" in ifci
    assert ifci["ifci_status"] in ["EXPANSIONARY", "BALANCED", "RESTRICTIVE"]
    assert any("INDIAN MACRO" in r for r in signal.rationale)

def test_agent1_multi_timeframe_breakdown_includes_indian_financial_conditions(macro_context):
    """Verify get_multi_timeframe_breakdown() outputs indian_financial_condition object."""
    agent1 = FundamentalAnalystAgent()
    breakdown = agent1.get_multi_timeframe_breakdown("RELIANCE", macro=macro_context)

    assert "indian_financial_condition" in breakdown
    ifc = breakdown["indian_financial_condition"]
    assert "ifci_score" in ifc
    assert "ifci_status" in ifc
    assert "reasons" in ifc
    assert "gsec_10y_yield" in ifc
    assert ifc["gsec_10y_yield"] == 6.92

def test_daily_data_manager_indian_financial_conditions():
    """Verify DailyDataManager stores, updates, and rolls over Indian financial conditions."""
    mgr = DailyDataManager()
    ifci = mgr.get_indian_financial_conditions()

    assert "ifci_score" in ifci
    assert "ifci_status" in ifci
    assert "gsec_10y_yield" in ifci
    assert ifci["gsec_10y_yield"] == 6.92

    # Perform daily rollover with BULLISH bias
    res_bull = mgr.perform_daily_rollover(force=True, market_bias="BULLISH")
    assert res_bull["status"] == "SUCCESS"
    assert mgr.macro_context.gsec_10y_yield <= 6.95

    # Check that status includes indian_financial_conditions
    status = mgr.get_status()
    assert "macro_snapshot" in status
    assert status["macro_snapshot"]["gsec_10y_yield"] <= 6.95

def test_auto_execution_takes_decisions_from_agents_and_executes():
    """Verify execute_single_best_trade evaluates all stocks with Agent 1 and Agent 2 decisions
    and executes the #1 pick with 5x margin MIS on the broker.
    """
    broker = PaperBroker(initial_capital=1_000_000.0)
    journal = TradeJournal(db_path=":memory:")
    agent1 = FundamentalAnalystAgent()
    agent2 = TechnicalAnalystAgent()
    risk_engine = DeterministicRiskEngine({
        "max_risk_per_trade_percent": 1.0,
        "hard_risk_cap_percent": 2.0,
        "max_open_positions": 1,
        "max_sector_exposure_percent": 90.0,
        "max_single_stock_exposure_percent": 90.0,
        "daily_loss_limit_percent": 2.0
    })
    agent3 = ExecutionAgent(risk_engine=risk_engine)

    orch = TradingOrchestrator(
        agent1=agent1,
        agent2=agent2,
        agent3=agent3,
        risk_engine=risk_engine,
        broker=broker,
        journal=journal
    )

    # Set up global server active broker
    server.active_broker = broker
    server.is_broker_connected = True
    server.orchestrator = orch

    # Execute single best trade
    res = execute_single_best_trade(orch, scan_count=1, force=True)

    assert res["status"] in ["success", "no_trade"]
    if res["status"] == "success":
        assert "symbol" in res
        assert "agent1_decision" in res
        assert "agent2_decision" in res
        assert "consensus" in res
        assert res["consensus"] is True
        assert res["agent1_decision"]["score"] >= 60.0
        assert "indian_financial_conditions" in res["agent1_decision"]

        # Check broker position
        portfolio = broker.get_portfolio_state()
        assert len(portfolio.open_positions) == 1
        top_sym = res["symbol"]
        assert top_sym in portfolio.open_positions

        pos = portfolio.open_positions[top_sym]
        assert pos.quantity > 0
        assert pos.stop_loss > 0
        assert pos.target_price > pos.entry_price

        # Second execution without force should be skipped due to Single Trade Policy
        res_skip = execute_single_best_trade(orch, scan_count=2, force=False)
        assert res_skip["status"] == "already_active"
