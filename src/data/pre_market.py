"""Pre-Market Session Analysis Module for Indian Stock Markets (NSE / BSE 09:00 - 09:15 IST).

Analyzes institutional price discovery, order book imbalance, indicative equilibrium price (IEP),
volume surge, and early morning macro alignment during the pre-open auction session:
1. Indicative Equilibrium Price (IEP) discovery vs Previous Close (Gap % & Gap Type).
2. Pre-Open Order Book Depth & Imbalance Ratio (Total Buy Qty vs Total Sell Qty).
3. Pre-Market Volume Surge Ratio (IEP Volume vs 20-Day Average Pre-Open Volume).
4. Early Morning Macro Cue Correlation (GIFT Nifty futures change % alignment).
5. Indicative Auction Volatility Spread (IEP High vs Low during 09:00-09:08 order accumulation).
6. Pre-Market Session Regime Classification (BULLISH_RUNAWAY, GAP_UP_PROFIT_TAKING, BALANCED_OPEN,
   BEARISH_BREAKDOWN, GAP_DOWN_ACCUMULATION).
7. Quantitative Pre-Market Score [-1.0, 1.0] and Directional Pillar Vote {-1.0, 0.0, 1.0}.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field


class PreMarketGapType(str, Enum):
    LARGE_GAP_UP = "LARGE_GAP_UP"           # Gap >= +1.5%
    MODERATE_GAP_UP = "MODERATE_GAP_UP"     # +0.3% <= Gap < +1.5%
    FLAT = "FLAT"                           # -0.3% < Gap < +0.3%
    MODERATE_GAP_DOWN = "MODERATE_GAP_DOWN" # -1.5% < Gap <= -0.3%
    LARGE_GAP_DOWN = "LARGE_GAP_DOWN"       # Gap <= -1.5%


class PreMarketRegime(str, Enum):
    BULLISH_RUNAWAY = "BULLISH_RUNAWAY"               # Strong gap up + buy imbalance + volume surge
    GAP_UP_PROFIT_TAKING = "GAP_UP_PROFIT_TAKING"     # Gap up but sell imbalance (fade gap)
    BALANCED_OPEN = "BALANCED_OPEN"                   # Orderly equilibrium open near prev close
    BEARISH_BREAKDOWN = "BEARISH_BREAKDOWN"           # Heavy gap down + sell imbalance + volume surge
    GAP_DOWN_ACCUMULATION = "GAP_DOWN_ACCUMULATION"   # Gap down absorbed by strong institutional buy queue


class PreMarketData(BaseModel):
    """Raw pre-market auction session data (09:00 - 09:15 IST)."""
    symbol: str
    prev_close: float
    iep_price: float                                    # Indicative Equilibrium Price discovered at 09:08 IST
    iep_volume: int = 15000                             # Matched volume at equilibrium price
    avg_pre_market_volume_20d: int = 15000              # 20-day historical average pre-market volume
    total_buy_qty: int = 60000                          # Unexecuted cumulative buy depth at IEP
    total_sell_qty: int = 50000                         # Unexecuted cumulative sell depth at IEP
    iep_high: Optional[float] = None                    # Highest indicative price in 09:00-09:08 auction
    iep_low: Optional[float] = None                     # Lowest indicative price in 09:00-09:08 auction
    gift_nifty_change_pct: float = 0.0                  # Early morning GIFT Nifty change % (macro cue)
    timestamp: Optional[datetime] = None


class PreMarketAnalysis(BaseModel):
    """Computed pre-market session metrics, regime classification, and directional score."""
    symbol: str
    prev_close: float
    iep_price: float
    gap_pct: float                                      # Percentage gap relative to previous close
    gap_type: PreMarketGapType
    order_imbalance_ratio: float                        # Range [-1.0, 1.0] -> (Buy - Sell) / (Buy + Sell)
    volume_surge_ratio: float                           # IEP Volume / 20d Average Pre-market Volume
    gift_nifty_alignment: float                         # Range [-1.0, 1.0] -> Macro gap alignment
    volatility_spread_pct: float                        # (IEP High - IEP Low) / IEP Price * 100
    pre_market_regime: PreMarketRegime
    pre_market_score: float                             # Composite pre-market score in range [-1.0, 1.0]
    pre_market_vote: float                              # Directional vote: +1.0 (Bullish), -1.0 (Bearish), 0.0 (Neutral)
    institutional_sentiment: str                        # AGGRESSIVE_BUYING, PROFIT_TAKING, BALANCED, AGGRESSIVE_SELLING, ACCUMULATION
    rationale: List[str] = Field(default_factory=list)


def compute_pre_market_metrics(data_input: Union[PreMarketData, Dict[str, Any]]) -> PreMarketAnalysis:
    """Computes quantitative pre-market session indicators, regime, and directional vote.
    
    Evaluates:
      1. Gap % vs Previous Close: Categorized into 5 gap brackets.
      2. Pre-Open Order Book Imbalance: Unmatched institutional bids vs asks.
      3. Pre-Market Volume Surge: Institutional participation strength.
      4. GIFT Nifty Macro Cue Alignment: Sympathy with morning index momentum.
      5. Pre-Open Spread Volatility: Measure of auction price stabilization.
    """
    if isinstance(data_input, dict):
        data = PreMarketData(**data_input)
    else:
        data = data_input

    rationale: List[str] = []
    symbol = data.symbol
    prev_close = max(0.01, float(data.prev_close))
    iep_price = float(data.iep_price)

    # 1. GAP ANALYSIS
    gap_pct = round(((iep_price - prev_close) / prev_close) * 100.0, 2)
    if gap_pct >= 1.50:
        gap_type = PreMarketGapType.LARGE_GAP_UP
    elif gap_pct >= 0.30:
        gap_type = PreMarketGapType.MODERATE_GAP_UP
    elif gap_pct <= -1.50:
        gap_type = PreMarketGapType.LARGE_GAP_DOWN
    elif gap_pct <= -0.30:
        gap_type = PreMarketGapType.MODERATE_GAP_DOWN
    else:
        gap_type = PreMarketGapType.FLAT

    # 2. ORDER BOOK DEPTH & IMBALANCE
    buy_qty = max(0, int(data.total_buy_qty))
    sell_qty = max(0, int(data.total_sell_qty))
    total_depth = buy_qty + sell_qty
    if total_depth > 0:
        order_imbalance_ratio = round((buy_qty - sell_qty) / total_depth, 3)
    else:
        order_imbalance_ratio = 0.0

    # 3. VOLUME SURGE
    iep_volume = max(0, int(data.iep_volume))
    avg_vol = max(1, int(data.avg_pre_market_volume_20d))
    volume_surge_ratio = round(iep_volume / avg_vol, 2)

    # 4. GIFT NIFTY ALIGNMENT
    # If stock gaps up and GIFT Nifty is positive -> strong confirmation (+1.0)
    # If stock gaps down and GIFT Nifty is negative -> strong confirmation (-1.0)
    # If diverging -> -0.5 to 0.0
    gn = data.gift_nifty_change_pct
    if abs(gap_pct) < 0.20:
        gift_nifty_alignment = 0.0
    elif (gap_pct > 0 and gn > 0.10) or (gap_pct < 0 and gn < -0.10):
        gift_nifty_alignment = 1.0 if gap_pct > 0 else -1.0
    elif (gap_pct > 0 and gn < -0.20) or (gap_pct < 0 and gn > 0.20):
        gift_nifty_alignment = -0.50 if gap_pct > 0 else 0.50
    else:
        gift_nifty_alignment = 0.0

    # 5. VOLATILITY SPREAD
    iep_h = float(data.iep_high) if data.iep_high is not None else iep_price * 1.003
    iep_l = float(data.iep_low) if data.iep_low is not None else iep_price * 0.997
    volatility_spread_pct = round(((iep_h - iep_l) / iep_price) * 100.0, 2)

    # 6. REGIME CLASSIFICATION & INSTITUTIONAL SENTIMENT
    if gap_pct >= 0.70 and order_imbalance_ratio >= 0.15 and volume_surge_ratio >= 1.05:
        regime = PreMarketRegime.BULLISH_RUNAWAY
        sentiment = "AGGRESSIVE_BUYING"
        base_score = 0.75 + min(0.25, (gap_pct - 0.70) * 0.1)
    elif gap_pct >= 0.80 and order_imbalance_ratio <= -0.15:
        regime = PreMarketRegime.GAP_UP_PROFIT_TAKING
        sentiment = "PROFIT_TAKING"
        base_score = -0.35 + min(0.20, order_imbalance_ratio * 0.5)  # Fade the gap
    elif gap_pct <= -0.70 and order_imbalance_ratio <= -0.15 and volume_surge_ratio >= 1.05:
        regime = PreMarketRegime.BEARISH_BREAKDOWN
        sentiment = "AGGRESSIVE_SELLING"
        base_score = -0.75 - min(0.25, abs(gap_pct + 0.70) * 0.1)
    elif gap_pct <= -0.80 and order_imbalance_ratio >= 0.15:
        regime = PreMarketRegime.GAP_DOWN_ACCUMULATION
        sentiment = "ACCUMULATION"
        base_score = 0.40 + min(0.25, order_imbalance_ratio * 0.5)   # Smart money absorption
    else:
        regime = PreMarketRegime.BALANCED_OPEN
        sentiment = "BALANCED"
        # Balanced open score driven moderately by imbalance and minor gap
        base_score = (gap_pct * 0.20) + (order_imbalance_ratio * 0.40)

    # Add macro cue adjustments to score
    composite_score = base_score + (gift_nifty_alignment * 0.10)
    composite_score = round(max(-1.0, min(1.0, composite_score)), 3)

    # Directional vote
    if composite_score >= 0.35:
        pre_market_vote = 1.0
    elif composite_score <= -0.35:
        pre_market_vote = -1.0
    else:
        pre_market_vote = 0.0

    # 7. RATIONALE GENERATION
    icon = "🟢" if pre_market_vote > 0 else ("🔴" if pre_market_vote < 0 else "⚪")
    rationale.append(
        f"{icon} PRE-MARKET: IEP ₹{iep_price:,.2f} ({gap_pct:+.2f}% {gap_type.value}) | "
        f"Imbalance {order_imbalance_ratio:+.2f} (Buy: {buy_qty:,} vs Sell: {sell_qty:,}) | "
        f"Vol Surge {volume_surge_ratio:.2f}x → Regime: {regime.value}."
    )

    if regime == PreMarketRegime.BULLISH_RUNAWAY:
        rationale.append("✅ PRE-MARKET CONVICTION: Institutional buyers dominating pre-open call auction; runaway gap supported by volume.")
    elif regime == PreMarketRegime.GAP_UP_PROFIT_TAKING:
        rationale.append("⚠️ PRE-MARKET CAUTION: Gap up met with heavy pre-open ask depth (profit taking). Risk of opening fade.")
    elif regime == PreMarketRegime.BEARISH_BREAKDOWN:
        rationale.append("🛑 PRE-MARKET SELLOFF: Large gap down accompanied by heavy institutional supply dump and sell imbalance.")
    elif regime == PreMarketRegime.GAP_DOWN_ACCUMULATION:
        rationale.append("💎 PRE-MARKET ABSORPTION: Institutional bids absorbing retail panic sell orders at discounted equilibrium price.")
    else:
        rationale.append("ℹ️ PRE-MARKET EQUILIBRIUM: Orderly price discovery near previous close with balanced book depth.")

    if gift_nifty_alignment > 0:
        rationale.append(f"🌐 MACRO ALIGNMENT: Morning GIFT Nifty cue ({gn:+.2f}%) confirms pre-market gap direction.")
    elif gift_nifty_alignment < 0:
        rationale.append(f"⚠️ MACRO DIVERGENCE: Morning GIFT Nifty cue ({gn:+.2f}%) diverges from pre-market gap direction.")

    return PreMarketAnalysis(
        symbol=symbol,
        prev_close=prev_close,
        iep_price=iep_price,
        gap_pct=gap_pct,
        gap_type=gap_type,
        order_imbalance_ratio=order_imbalance_ratio,
        volume_surge_ratio=volume_surge_ratio,
        gift_nifty_alignment=gift_nifty_alignment,
        volatility_spread_pct=volatility_spread_pct,
        pre_market_regime=regime,
        pre_market_score=composite_score,
        pre_market_vote=pre_market_vote,
        institutional_sentiment=sentiment,
        rationale=rationale
    )
