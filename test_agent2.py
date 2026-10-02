import sys
sys.path.insert(0, '.')
from src.agents.agent2_technical import TechnicalAnalystAgent

agent2 = TechnicalAnalystAgent()
print("Agent2 loaded OK")
print("  long_threshold:", agent2.long_threshold)
print("  min_adx_for_trade:", agent2.min_adx_for_trade)
print("  min_indicator_votes:", agent2.min_indicator_votes)

# HIGH-CONFLUENCE setup - should PASS the gate
sig = agent2.analyze(
    symbol="RELIANCE", current_price=2920.0,
    ema20=2890.0, ema50=2850.0, ema200=2700.0,
    adx=32.0, rsi14=63.0, macd_hist=3.5,
    atr14=35.0, vwap=2905.0, volume_ratio=1.6,
    orderflow={
        "bid_depth_qty": 350000, "ask_depth_qty": 210000,
        "buy_volume": 1250000, "sell_volume": 850000,
        "cumulative_delta": 400000, "total_volume": 2100000,
        "institutional_block_buys": 65000, "institutional_block_sells": 15000
    },
    portfolio_capital=1000000.0
)
print("\nHigh-confluence RELIANCE signal:")
print("  direction:", sig.direction)
print("  gate_passed:", sig.features["gate_passed"])
print("  votes_aligned:", sig.features["votes_aligned"], "/ 5")
print("  win_prob:", f"{sig.win_prob:.1%}")
print("  entry:", sig.entry, " sl:", sig.stop_loss, " target:", sig.target)
print("  position_value: {:,.2f}".format(sig.suggested_position_value))

# WEAK setup - should FAIL and be NEUTRAL
sig2 = agent2.analyze(
    symbol="TCS", current_price=4150.0,
    ema20=4100.0, ema50=4200.0, ema200=4000.0,
    adx=19.0, rsi14=52.0, macd_hist=0.5,
    atr14=50.0, vwap=4160.0, volume_ratio=0.9,
    orderflow=None,
    portfolio_capital=1000000.0
)
print("\nWeak TCS signal (should be NEUTRAL):")
print("  direction:", sig2.direction)
print("  gate_passed:", sig2.features["gate_passed"])
print("  win_prob:", f"{sig2.win_prob:.1%}")

print("\nRATIONALE for RELIANCE:")
for r in sig.rationale:
    print(" ", r)
