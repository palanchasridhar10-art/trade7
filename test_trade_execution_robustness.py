import sys
sys.path.insert(0, '.')
import json
from src.broker.paper import PaperBroker
from src.broker.angel_one import AngelOneAdapter
from src.data.angel_tokens import get_angel_token, get_angel_tradingsymbol
from server import run_symbol_cycle, execute_single_best_trade, init_orchestrator
import server

def test_paper_execution():
    print("Testing Paper Broker execution...")
    broker = PaperBroker(initial_capital=1_000_000.0)
    order = broker.submit_bracket_order(
        symbol="TATAMOTORS",
        side="BUY",
        quantity=500,
        entry_price=427.0,
        stop_loss=405.0,
        target_price=503.0,
        sector="AUTO"
    )
    assert order is not None, "Order should not be None"
    assert order.symbol == "TATAMOTORS"
    assert order.quantity == 500
    print("  Paper execution passed!")

def test_angel_one_tokens_and_order():
    print("Testing Angel One tokens & order formatting...")
    adapter = AngelOneAdapter(client_code="DEMO", pin="1234", totp_secret="JBSWY3DPEHPK3PXP")
    assert get_angel_token("RELIANCE") == "2885"
    assert get_angel_token("TATAMOTORS") == "759782"
    assert get_angel_token("LTI") == "17818"
    assert get_angel_tradingsymbol("TATAMOTORS") == "TMCV-EQ"
    assert get_angel_tradingsymbol("LTI") == "LTM-EQ"

    # Test submitting bracket order (offline representation)
    order = adapter.submit_bracket_order(
        symbol="TATAMOTORS",
        side="BUY",
        quantity=250,
        entry_price=427.0,
        stop_loss=405.0,
        target_price=503.0,
        sector="AUTO"
    )
    assert order is not None
    assert order.symbol == "TATAMOTORS"
    assert order.quantity == 250
    print("  Angel One tokens and order passed!")

def test_orchestrator_execution():
    print("Testing full orchestrator execution...")
    broker = PaperBroker(initial_capital=1_000_000.0)
    server.active_broker = broker
    orch = init_orchestrator(broker)
    
    # Test execute_single_best_trade on fresh broker
    res = execute_single_best_trade(orch, force=True)
    assert res is not None
    assert res.get("status") == "success"
    # Verify JSON serializability of res
    serialized = json.dumps(res, default=str)
    assert len(serialized) > 100
    print(f"  Single best trade auto-execution passed: status={res.get('status')}")

    # Check portfolio state has exactly 1 position
    port = broker.get_portfolio_state()
    assert len(port.open_positions) == 1
    print("  Portfolio holds exactly 1 active trade position:", list(port.open_positions.keys()))

if __name__ == "__main__":
    test_paper_execution()
    test_angel_one_tokens_and_order()
    test_orchestrator_execution()
    print("\nALL TRADE EXECUTION CHECKS PASSED WITH ZERO ERRORS!")
