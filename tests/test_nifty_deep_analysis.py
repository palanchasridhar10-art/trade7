"""
Unit tests for Nifty 50 Deep Quantitative Analysis Engine and REST Endpoints.
Validates all 8 institutional analysis components:
1. Smart Money Concepts (SMC) & Market Structure
2. Fair Value Gaps (FVG) & Order Blocks (OB)
3. Present Financial Conditions (IFCI Macro)
4. Constituent Stock & Sector Heatmap
5. Liquidity Pools & Order Flow Radar
6. Multi-Agent Verification & Strategy Decision Flowchart
7. Real-Time Limit Orders Price Ladder & Bracket Display
8. Top Alpha Trade Selection
"""

import pytest
from server import get_nifty_deep_analysis_payload


def test_nifty_deep_analysis_payload_structure():
    """Verify top-level payload structure and mandatory analysis keys."""
    payload = get_nifty_deep_analysis_payload("NIFTY")
    assert payload["status"] == "success"
    assert "timestamp" in payload
    assert "ist_time" in payload
    assert payload["focus_symbol"] == "NIFTY"
    
    # 8 Key components verification
    assert "nifty_chart_smc" in payload
    assert "focus_stock_smc" in payload
    assert "financial_market_conditions" in payload
    assert "heatmap" in payload
    assert "sectors" in payload
    assert "liquidity" in payload
    assert "flowchart" in payload
    assert "limit_orders" in payload
    assert "top_pick" in payload


def test_nifty_chart_smc_and_dealing_range():
    """Verify Nifty 50 Smart Money Concepts, dealing range, and order blocks."""
    payload = get_nifty_deep_analysis_payload("NIFTY")
    smc = payload["nifty_chart_smc"]
    
    assert smc["symbol"] == "NIFTY 50"
    assert smc["price"] > 20000.0
    assert smc["swing_high"] > smc["swing_low"]
    assert smc["range_high"] > smc["range_low"]
    assert smc["equilibrium_price"] == round((smc["range_high"] + smc["range_low"]) / 2.0, 2)
    assert 0.0 <= smc["dealing_range_pct"] <= 100.0
    assert smc["dealing_range_zone"] in ["DISCOUNT", "PREMIUM", "EQUILIBRIUM"]
    assert "BOS" in smc["market_structure"] or "CHoCH" in smc["market_structure"] or "RANGING" in smc["market_structure"]
    
    # Order Blocks verification
    assert len(smc["order_blocks"]) >= 2
    for ob in smc["order_blocks"]:
        assert ob["type"] in ["BULLISH_OB", "BEARISH_OB"]
        assert ob["top"] >= ob["bottom"]
        assert ob["displacement"] >= 1.0
        assert ob["mitigated"] is False
        
    # Fair Value Gaps verification
    assert len(smc["fvgs"]) >= 2
    for fvg in smc["fvgs"]:
        assert fvg["type"] in ["BISI", "SIBI"]
        assert fvg["top"] >= fvg["bottom"]
        assert fvg["ce"] == round((fvg["top"] + fvg["bottom"]) / 2.0, 2)
        assert fvg["filled"] is False


def test_focus_stock_smc_custom_symbol():
    """Verify custom focus stock analysis (e.g. RELIANCE or TATASTEEL)."""
    payload = get_nifty_deep_analysis_payload("RELIANCE")
    assert payload["focus_symbol"] == "RELIANCE"
    stock_smc = payload["focus_stock_smc"]
    assert stock_smc["symbol"] == "RELIANCE"
    assert stock_smc["price"] > 0
    assert len(stock_smc["order_blocks"]) >= 2
    assert len(stock_smc["fvgs"]) >= 2


def test_ifci_financial_market_conditions():
    """Verify Indian Financial Conditions Index macro indicators."""
    payload = get_nifty_deep_analysis_payload("NIFTY")
    ifci = payload["financial_market_conditions"]
    
    assert 0.0 <= ifci["ifci_score"] <= 100.0
    assert ifci["ifci_status"] in ["EXPANSIONARY", "NEUTRAL", "RESTRICTIVE"]
    
    ind = ifci["indicators"]
    assert 5.0 <= ind["gsec_10y_yield"] <= 9.0
    assert 5.0 <= ind["repo_rate"] <= 8.0
    assert ind["manufacturing_pmi"] > 40.0
    assert ind["cpi_inflation"] > 0.0
    assert ind["nifty_pe"] > 10.0
    assert ind["india_vix"] > 0.0
    assert ind["advance_decline_ratio"] > 0.0
    assert len(ifci["reasons"]) >= 1


def test_heatmap_and_sectors():
    """Verify 50 constituent stocks heatmap grid and sector groupings."""
    payload = get_nifty_deep_analysis_payload("NIFTY")
    heatmap = payload["heatmap"]
    sectors = payload["sectors"]
    
    assert len(heatmap) == 50
    symbols = set(item["symbol"] for item in heatmap)
    assert "RELIANCE" in symbols
    assert "TCS" in symbols
    assert "HDFCBANK" in symbols
    assert "INFY" in symbols
    assert "ICICIBANK" in symbols
    
    for it in heatmap:
        assert it["price"] > 0
        assert it["smc_bias"] in ["BULLISH", "BEARISH", "NEUTRAL"]
        assert it["direction"] in ["LONG", "SHORT", "NEUTRAL"]
        assert 0.0 <= it["win_prob"] <= 1.0
        assert it["volume_surge"] > 0
        
    assert len(sectors) >= 6
    total_sector_stocks = sum(sec["count"] for sec in sectors)
    assert total_sector_stocks == 50


def test_liquidity_radar():
    """Verify Liquidity Pool Radar metrics and net CVD accumulation."""
    payload = get_nifty_deep_analysis_payload("NIFTY")
    liq = payload["liquidity"]
    
    assert liq["nifty_bsl"] > 0
    assert liq["nifty_ssl"] > 0
    assert liq["nifty_bsl"] > liq["nifty_ssl"]
    assert isinstance(liq["universe_net_cvd"], (int, float))
    assert liq["bsl_swept_stocks_count"] >= 0
    assert liq["ssl_swept_stocks_count"] >= 0
    assert liq["order_book_pressure"] in ["NET_BUYER_ABSORPTION", "NET_SELLER_DISTRIBUTION"]
    assert "institutional_blocks_today" in liq


def test_flowchart_pipeline():
    """Verify 8-stage strategy decision pipeline."""
    payload = get_nifty_deep_analysis_payload("NIFTY")
    flowchart = payload["flowchart"]
    
    assert len(flowchart) == 8
    for idx, stage in enumerate(flowchart, 1):
        assert stage["step"] == idx
        assert "name" in stage
        assert stage["status"] in ["PASSED", "EXECUTED", "CONFIRMED"]
        assert "rule" in stage
        assert "icon" in stage


def test_limit_orders_price_display():
    """Verify Limit Orders price ladder with 5% SL, 18% target, and +8% trailing rule."""
    payload = get_nifty_deep_analysis_payload("NIFTY")
    limit_orders = payload["limit_orders"]
    
    assert len(limit_orders) >= 1
    for order in limit_orders:
        assert order["rank"] >= 1
        assert order["entry_limit_price"] > 0
        assert order["stop_loss_pct"] == "5.0%"
        assert order["target_pct"] == "18.0%"
        assert order["risk_reward_ratio"] == "1 : 3.60"
        assert order["product_type"] == "MIS (5x Leverage)"
        assert order["quantity"] >= 1
        assert order["blocked_mis_margin"] > 0
        assert "Trailing" in order["trailing_stop_rule"] or "+8.0%" in order["trailing_stop_rule"]
        
        # Verify long vs short limit math
        is_short = "SHORT" in order["side"]
        if is_short:
            assert order["stop_loss_limit_price"] > order["entry_limit_price"]
            assert order["target_limit_price"] < order["entry_limit_price"]
            assert order["trailing_stop_trigger_price"] < order["entry_limit_price"]
        else:
            assert order["stop_loss_limit_price"] < order["entry_limit_price"]
            assert order["target_limit_price"] > order["entry_limit_price"]
            assert order["trailing_stop_trigger_price"] > order["entry_limit_price"]
