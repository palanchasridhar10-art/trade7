"""Order Flow and Market Microstructure Analysis Module.

Analyzes real-time Level 2 Order Book depth, Cumulative Volume Delta (CVD),
Aggressive Buyer vs Seller trades, and Institutional Block order activity.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class OrderFlowData(BaseModel):
    """Raw market microstructure and tick tape data for a stock."""
    symbol: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Level-2 Market Depth (Top 5 Bids and Asks)
    bid_depth_qty: int = 0
    ask_depth_qty: int = 0
    
    # Aggressive Volume Execution (Market Orders)
    buy_volume: int = 0       # Buyer-initiated aggressive market buys (hitting the Ask)
    sell_volume: int = 0      # Seller-initiated aggressive market sells (hitting the Bid)
    cumulative_delta: int = 0 # Net cumulative volume delta (buy_volume - sell_volume)
    total_volume: int = 0     # Total traded volume today
    
    # Institutional Block / Large Trade Flow (>= 10,000 units or >= Rs 25 Lakhs)
    institutional_block_buys: int = 0
    institutional_block_sells: int = 0
    
    # Tape Microstructure Signals
    vwap_deviation_pct: float = 0.0 # Price deviation from VWAP
    is_at_support_or_resistance: bool = False

class OrderFlowAnalysis(BaseModel):
    """Computed order flow indicators and regime classification."""
    symbol: str
    order_book_imbalance: float   # [-1.0, 1.0] (bid_qty - ask_qty) / (bid_qty + ask_qty)
    delta_ratio: float            # [-1.0, 1.0] CVD / Total Volume
    institutional_bias: float     # [-1.0, 1.0] (block_buys - block_sells) / (block_buys + block_sells)
    absorption_detected: bool     # True if high volume absorbed without price moving against it
    flow_regime: str              # ACCUMULATION, DISTRIBUTION, ABSORPTION, BALANCED
    orderflow_score: float        # Composite score [-1.0, 1.0]
    orderflow_vote: float         # Discrete signal vote {-1.0, 0.0, +1.0}
    rationale: List[str] = Field(default_factory=list)

def compute_orderflow_metrics(data: OrderFlowData) -> OrderFlowAnalysis:
    """Analyze order book imbalance, volume delta, and institutional tape flow."""
    rationale = []

    # 1. Order Book Imbalance (OBI)
    total_depth = data.bid_depth_qty + data.ask_depth_qty
    if total_depth > 0:
        obi = (data.bid_depth_qty - data.ask_depth_qty) / float(total_depth)
    else:
        obi = 0.0
    obi = max(-1.0, min(1.0, obi))

    # 2. Cumulative Volume Delta (CVD) and Delta Ratio
    vol = data.total_volume if data.total_volume > 0 else (data.buy_volume + data.sell_volume)
    delta = data.cumulative_delta if data.cumulative_delta != 0 else (data.buy_volume - data.sell_volume)
    if vol > 0:
        delta_ratio = delta / float(vol)
    else:
        delta_ratio = 0.0
    delta_ratio = max(-1.0, min(1.0, delta_ratio))

    # 3. Institutional Block Flow (Smart Money)
    total_blocks = data.institutional_block_buys + data.institutional_block_sells
    if total_blocks > 0:
        inst_bias = (data.institutional_block_buys - data.institutional_block_sells) / float(total_blocks)
    else:
        inst_bias = 0.0
    inst_bias = max(-1.0, min(1.0, inst_bias))

    # 4. Absorption Detection
    # Absorption occurs when aggressive volume is high (delta extreme) but price fails to break support/resistance
    absorption = False
    if data.is_at_support_or_resistance:
        if delta < 0 and obi > 0.15: # Heavy selling absorbed by strong passive bids
            absorption = True
            rationale.append("Bullish Absorption: Aggressive market sells absorbed by heavy passive institutional bids.")
        elif delta > 0 and obi < -0.15: # Heavy buying absorbed by passive offers
            absorption = True
            rationale.append("Bearish Absorption: Aggressive market buys absorbed by heavy passive institutional asks.")

    # 5. Flow Regime Classification
    if obi > 0.20 and delta_ratio > 0.10:
        regime = "ACCUMULATION"
        rationale.append(f"Institutional Accumulation: Bid depth leads by {obi*100:.1f}%, CVD +{delta:,} shares.")
    elif obi < -0.20 and delta_ratio < -0.10:
        regime = "DISTRIBUTION"
        rationale.append(f"Institutional Distribution: Ask depth leads by {abs(obi)*100:.1f}%, CVD {delta:,} shares.")
    elif absorption:
        regime = "ABSORPTION"
    else:
        regime = "BALANCED"
        rationale.append(f"Balanced Order Flow: OBI at {obi*100:+.1f}%, Delta Ratio at {delta_ratio*100:+.1f}%.")

    if inst_bias > 0.25:
        rationale.append(f"Institutional Block Flow: Smart money net buy bias ({inst_bias*100:+.1f}%).")
    elif inst_bias < -0.25:
        rationale.append(f"Institutional Block Flow: Smart money net sell bias ({inst_bias*100:+.1f}%).")

    # 6. Composite Order Flow Score [-1.0, +1.0]
    # Weights: OBI (35%), Delta Ratio (35%), Institutional Block Flow (30%)
    score = (0.35 * obi) + (0.35 * delta_ratio) + (0.30 * inst_bias)
    
    # Adjust for absorption if detected
    if absorption:
        if obi > 0.15:
            score += 0.15 # Bullish absorption boost
        elif obi < -0.15:
            score -= 0.15 # Bearish absorption drag

    score = max(-1.0, min(1.0, round(score, 3)))

    # 7. Discrete Order Flow Signal Vote
    if score >= 0.25:
        vote = 1.0 # Bullish order flow confirmation
    elif score <= -0.25:
        vote = -1.0 # Bearish order flow confirmation
    else:
        vote = 0.0 # Neutral

    return OrderFlowAnalysis(
        symbol=data.symbol,
        order_book_imbalance=round(obi, 3),
        delta_ratio=round(delta_ratio, 3),
        institutional_bias=round(inst_bias, 3),
        absorption_detected=absorption,
        flow_regime=regime,
        orderflow_score=score,
        orderflow_vote=vote,
        rationale=rationale
    )
