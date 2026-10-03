"""Smart Money Concepts (SMC) Analysis Module.

Analyzes institutional price delivery mechanisms including:
1. Market Structure: Break of Structure (BOS) and Change of Character (CHoCH).
2. Liquidity: Buy-Side Liquidity (BSL), Sell-Side Liquidity (SSL), and Liquidity Sweeps/Grabs.
3. Price Inefficiencies: Unmitigated Order Blocks (OB) and Fair Value Gaps (FVG) / Imbalances.
4. Dealing Range: Premium vs Discount pricing relative to institutional equilibrium.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

class MarketStructureType(str, Enum):
    BULLISH_BOS = "BULLISH_BOS"         # Break of Structure upward (trend continuation)
    BULLISH_CHOCH = "BULLISH_CHOCH"     # Change of Character upward (bullish reversal)
    BEARISH_BOS = "BEARISH_BOS"         # Break of Structure downward (trend continuation)
    BEARISH_CHOCH = "BEARISH_CHOCH"     # Change of Character downward (bearish reversal)
    RANGING_CONSOLIDATION = "RANGING_CONSOLIDATION"

class LiquidityEventType(str, Enum):
    SSL_SWEPT = "SSL_SWEPT"             # Sell-Side Liquidity swept below key low & reclaimed (Bullish trap)
    BSL_SWEPT = "BSL_SWEPT"             # Buy-Side Liquidity swept above key high & rejected (Bearish trap)
    EQUAL_HIGHS_UNSWEPT = "EQUAL_HIGHS_UNSWEPT" # Resting buy stops overhead (Upside magnet)
    EQUAL_LOWS_UNSWEPT = "EQUAL_LOWS_UNSWEPT"   # Resting sell stops below (Downside magnet)
    INDUCEMENT_TAKEN = "INDUCEMENT_TAKEN"       # Minor retail inducement swept before institutional push
    NEUTRAL = "NEUTRAL"

class OrderBlockType(str, Enum):
    BULLISH_OB = "BULLISH_OB"           # Demand zone: last down-candle before bullish displacement
    BEARISH_OB = "BEARISH_OB"           # Supply zone: last up-candle before bearish displacement

class FVGType(str, Enum):
    BISI = "BISI"                       # Buyside Imbalance Sellside Inefficiency (Bullish FVG)
    SIBI = "SIBI"                       # Sellside Imbalance Buyside Inefficiency (Bearish FVG)

class OrderBlock(BaseModel):
    """Institutional Order Block (OB) zone."""
    ob_type: OrderBlockType
    top_price: float
    bottom_price: float
    midpoint: float
    mitigated: bool = False             # True if price has previously retested and filled this OB
    volume_displacement: float = 1.5   # Displacement multiplier relative to average volume
    is_price_in_zone: bool = False

class FairValueGap(BaseModel):
    """3-candle price imbalance (Fair Value Gap)."""
    fvg_type: FVGType
    top_price: float
    bottom_price: float
    consequent_encroachment: float      # 50% midpoint of the imbalance
    status: str = "UNFILLED"            # UNFILLED, PARTIALLY_FILLED, FILLED
    is_price_in_fvg: bool = False

class SMCData(BaseModel):
    """Raw Smart Money price action data for a stock."""
    symbol: str
    current_price: float
    market_structure: MarketStructureType = MarketStructureType.RANGING_CONSOLIDATION
    swing_high: float = 0.0
    swing_low: float = 0.0
    liquidity_event: LiquidityEventType = LiquidityEventType.NEUTRAL
    bsl_price: float = 0.0              # Buy-side liquidity level (e.g. recent swing high / equal highs)
    ssl_price: float = 0.0              # Sell-side liquidity level (e.g. recent swing low / equal lows)
    order_blocks: List[OrderBlock] = Field(default_factory=list)
    fair_value_gaps: List[FairValueGap] = Field(default_factory=list)
    dealing_range_high: float = 0.0     # Highest price of dealing range
    dealing_range_low: float = 0.0      # Lowest price of dealing range

class SMCAnalysis(BaseModel):
    """Computed Smart Money Concept metrics, scores, and institutional narrative."""
    symbol: str
    market_structure: str               # BULLISH_BOS, BULLISH_CHOCH, etc.
    structure_score: float              # [-1.0, 1.0]
    liquidity_event: str                # SSL_SWEPT, BSL_SWEPT, etc.
    liquidity_score: float              # [-1.0, 1.0]
    active_order_block: Optional[Dict[str, Any]] = None
    ob_score: float = 0.0               # [-1.0, 1.0]
    active_fvg: Optional[Dict[str, Any]] = None
    fvg_score: float = 0.0              # [-1.0, 1.0]
    inefficiency_score: float           # [-1.0, 1.0] (combined OB + FVG)
    dealing_range_zone: str             # DISCOUNT, PREMIUM, EQUILIBRIUM
    dealing_range_pct: float            # 0-100% position within current range
    smc_composite_score: float          # [-1.0, 1.0]
    smc_vote: float                     # {-1.0, 0.0, 1.0}
    smc_bias: str                       # BULLISH, BEARISH, NEUTRAL
    institutional_narrative: str
    rationale: List[str] = Field(default_factory=list)

def compute_smc_metrics(data: SMCData) -> SMCAnalysis:
    """Evaluates Smart Money Concepts across structure, liquidity, and price inefficiencies."""
    rationale = []
    px = data.current_price

    # ── 1. MARKET STRUCTURE EVALUATION (35% weight) ──────────────────────────
    struct_score = 0.0
    ms = data.market_structure

    if ms == MarketStructureType.BULLISH_BOS:
        struct_score = 1.0
        rationale.append(f"🏛️ STRUCTURE: Bullish Break of Structure (BOS) — price closed above swing high ₹{data.swing_high:.2f} confirming uptrend continuation.")
    elif ms == MarketStructureType.BULLISH_CHOCH:
        struct_score = 0.85
        rationale.append(f"🏛️ STRUCTURE: Bullish Change of Character (CHoCH) — early reversal confirmed above previous lower high ₹{data.swing_high:.2f}.")
    elif ms == MarketStructureType.BEARISH_BOS:
        struct_score = -1.0
        rationale.append(f"🏛️ STRUCTURE: Bearish Break of Structure (BOS) — price closed below swing low ₹{data.swing_low:.2f} confirming downtrend continuation.")
    elif ms == MarketStructureType.BEARISH_CHOCH:
        struct_score = -0.85
        rationale.append(f"🏛️ STRUCTURE: Bearish Change of Character (CHoCH) — trend breakdown below previous higher low ₹{data.swing_low:.2f}.")
    else:
        struct_score = 0.0
        rationale.append("🏛️ STRUCTURE: Internal consolidation — ranging between swing levels.")

    # ── 2. LIQUIDITY ANALYSIS (35% weight) ───────────────────────────────────
    liq_score = 0.0
    liq_event = data.liquidity_event

    if liq_event == LiquidityEventType.SSL_SWEPT:
        liq_score = 1.0
        rationale.append(f"💧 LIQUIDITY: Sell-Side Liquidity (SSL) swept at ₹{data.ssl_price:.2f} and sharply reclaimed — retail sell stops purged into institutional buy orders.")
    elif liq_event == LiquidityEventType.BSL_SWEPT:
        liq_score = -1.0
        rationale.append(f"💧 LIQUIDITY: Buy-Side Liquidity (BSL) swept at ₹{data.bsl_price:.2f} and rejected — retail buy stops purged into institutional sell distribution.")
    elif liq_event == LiquidityEventType.EQUAL_HIGHS_UNSWEPT:
        liq_score = 0.60
        rationale.append(f"💧 LIQUIDITY: Prominent Equal Highs (EQH) at ₹{data.bsl_price:.2f} — resting buy-side liquidity serves as primary upside magnetic target.")
    elif liq_event == LiquidityEventType.EQUAL_LOWS_UNSWEPT:
        liq_score = -0.60
        rationale.append(f"💧 LIQUIDITY: Prominent Equal Lows (EQL) at ₹{data.ssl_price:.2f} — resting sell-side liquidity serves as primary downside magnetic target.")
    elif liq_event == LiquidityEventType.INDUCEMENT_TAKEN:
        liq_score = 0.40 if struct_score >= 0 else -0.40
        rationale.append("💧 LIQUIDITY: Internal Inducement (IDM) taken — retail trap completed before smart money continuation.")
    else:
        liq_score = 0.0
        rationale.append("💧 LIQUIDITY: No active session sweep detected — balanced resting orders.")

    # ── 3. PRICE INEFFICIENCIES: ORDER BLOCKS & FVGs (30% weight) ───────────
    ob_score = 0.0
    active_ob_info = None

    for ob in data.order_blocks:
        in_zone = (ob.bottom_price <= px <= ob.top_price) or ob.is_price_in_zone
        if in_zone and not ob.mitigated:
            active_ob_info = {
                "type": ob.ob_type.value,
                "top": ob.top_price,
                "bottom": ob.bottom_price,
                "midpoint": ob.midpoint,
                "mitigated": False,
                "displacement": ob.volume_displacement
            }
            if ob.ob_type == OrderBlockType.BULLISH_OB:
                ob_score = 1.0
                rationale.append(f"🧱 ORDER BLOCK: Price retesting unmitigated Bullish OB [₹{ob.bottom_price:.2f} - ₹{ob.top_price:.2f}] — high-probability institutional demand zone.")
            else:
                ob_score = -1.0
                rationale.append(f"🧱 ORDER BLOCK: Price retesting unmitigated Bearish OB [₹{ob.bottom_price:.2f} - ₹{ob.top_price:.2f}] — institutional supply barrier.")
            break
        elif not ob.mitigated:
            # OB exists nearby but not currently retesting
            if ob.ob_type == OrderBlockType.BULLISH_OB and px > ob.top_price:
                ob_score = max(ob_score, 0.40)
            elif ob.ob_type == OrderBlockType.BEARISH_OB and px < ob.bottom_price:
                ob_score = min(ob_score, -0.40)

    fvg_score = 0.0
    active_fvg_info = None

    for fvg in data.fair_value_gaps:
        in_gap = (fvg.bottom_price <= px <= fvg.top_price) or fvg.is_price_in_fvg
        if in_gap and fvg.status != "FILLED":
            active_fvg_info = {
                "type": fvg.fvg_type.value,
                "top": fvg.top_price,
                "bottom": fvg.bottom_price,
                "ce": fvg.consequent_encroachment,
                "status": fvg.status
            }
            if fvg.fvg_type == FVGType.BISI:
                fvg_score = 0.85
                rationale.append(f"⚡ FAIR VALUE GAP: Price tapping Bullish FVG (BISI) [₹{fvg.bottom_price:.2f} - ₹{fvg.top_price:.2f}] at 50% Consequent Encroachment ₹{fvg.consequent_encroachment:.2f}.")
            else:
                fvg_score = -0.85
                rationale.append(f"⚡ FAIR VALUE GAP: Price tapping Bearish FVG (SIBI) [₹{fvg.bottom_price:.2f} - ₹{fvg.top_price:.2f}] at 50% Consequent Encroachment ₹{fvg.consequent_encroachment:.2f}.")
            break
        elif fvg.status != "FILLED":
            if fvg.fvg_type == FVGType.BISI and px > fvg.top_price:
                fvg_score = max(fvg_score, 0.30)
            elif fvg.fvg_type == FVGType.SIBI and px < fvg.bottom_price:
                fvg_score = min(fvg_score, -0.30)

    inefficiency_score = max(-1.0, min(1.0, 0.55 * ob_score + 0.45 * fvg_score))

    # ── 4. DEALING RANGE & PREMIUM / DISCOUNT ZONE ───────────────────────────
    range_high = data.dealing_range_high if data.dealing_range_high > 0 else (data.swing_high if data.swing_high > 0 else px * 1.05)
    range_low = data.dealing_range_low if data.dealing_range_low > 0 else (data.swing_low if data.swing_low > 0 else px * 0.95)
    range_span = range_high - range_low

    if range_span > 0:
        range_pct = max(0.0, min(100.0, ((px - range_low) / range_span) * 100.0))
    else:
        range_pct = 50.0

    if range_pct < 48.0:
        zone = "DISCOUNT"
        discount_bonus = 0.10
        rationale.append(f"🏷️ PRICING: Discount Zone ({range_pct:.1f}% of Dealing Range) — Smart Money favorable buying territory.")
    elif range_pct > 52.0:
        zone = "PREMIUM"
        discount_bonus = -0.10
        rationale.append(f"🏷️ PRICING: Premium Zone ({range_pct:.1f}% of Dealing Range) — Smart Money favorable selling territory.")
    else:
        zone = "EQUILIBRIUM"
        discount_bonus = 0.0
        rationale.append(f"🏷️ PRICING: Equilibrium (50%) — Neutral dealing range valuation.")

    # ── 5. COMPOSITE SMC SCORE & VOTE ─────────────────────────────────────────
    composite_raw = (
        0.35 * struct_score
        + 0.35 * liq_score
        + 0.30 * inefficiency_score
    )

    # Apply pricing zone alignment
    if composite_raw > 0 and zone == "DISCOUNT":
        composite_raw += discount_bonus
    elif composite_raw < 0 and zone == "PREMIUM":
        composite_raw += abs(discount_bonus)
    elif composite_raw > 0 and zone == "PREMIUM" and range_pct > 75.0:
        composite_raw -= 0.20  # Caution: buying high in extreme premium
        rationale.append("⚠️ SMC WARNING: Setup is bullish but price is in deep Premium (>75%) — watch for pullbacks.")
    elif composite_raw < 0 and zone == "DISCOUNT" and range_pct < 25.0:
        composite_raw += 0.20  # Caution: selling low in deep discount
        rationale.append("⚠️ SMC WARNING: Setup is bearish but price is in deep Discount (<25%) — watch for short squeeze.")

    composite = max(-1.0, min(1.0, round(composite_raw, 3)))

    if composite >= 0.50:
        smc_vote = 1.0
        smc_bias = "BULLISH"
    elif composite <= -0.50:
        smc_vote = -1.0
        smc_bias = "BEARISH"
    else:
        smc_vote = 0.0
        smc_bias = "NEUTRAL"

    # Institutional narrative summary
    if smc_bias == "BULLISH":
        institutional_narrative = (
            f"Smart Money accumulation confirmed: {ms.value} with {liq_event.value}. "
            f"Price operating in {zone} ({range_pct:.0f}%) tapping institutional demand."
        )
    elif smc_bias == "BEARISH":
        institutional_narrative = (
            f"Smart Money distribution confirmed: {ms.value} with {liq_event.value}. "
            f"Price operating in {zone} ({range_pct:.0f}%) tapping institutional supply."
        )
    else:
        institutional_narrative = (
            f"Neutral Smart Money positioning: {ms.value} with {liq_event.value} at {zone} ({range_pct:.0f}%)."
        )

    return SMCAnalysis(
        symbol=data.symbol,
        market_structure=ms.value,
        structure_score=round(struct_score, 2),
        liquidity_event=liq_event.value,
        liquidity_score=round(liq_score, 2),
        active_order_block=active_ob_info,
        ob_score=round(ob_score, 2),
        active_fvg=active_fvg_info,
        fvg_score=round(fvg_score, 2),
        inefficiency_score=round(inefficiency_score, 2),
        dealing_range_zone=zone,
        dealing_range_pct=round(range_pct, 1),
        smc_composite_score=composite,
        smc_vote=smc_vote,
        smc_bias=smc_bias,
        institutional_narrative=institutional_narrative,
        rationale=rationale
    )
