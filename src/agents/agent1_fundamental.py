"""Agent 1: Multi-Timeframe Fundamental & Market-Condition Analyst.

Performs THREE independent analysis layers per company:

  DAILY   (30% weight) — Intraday price action, FII/DII flow today, news sentiment,
                          delivery volume, put/call ratio. Fast-moving signal.

  MONTHLY (40% weight) — Quarterly earnings QoQ, EPS trend, analyst upgrades/downgrades,
                          sector rotation score, management guidance. Medium-term signal.

  YEARLY  (30% weight) — 3-year revenue/PAT CAGR, ROE average, debt reduction,
                          FCF yield, ESG governance score, market share trend. Structural quality.

The three scores are combined into a single weighted composite score that drives
the LONG / SHORT / NEUTRAL direction and confidence passed to Agent 3.
"""

from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from src.core.constants import SignalDirection, TradingHorizon
from src.core.models import FundamentalSignal
from src.data.feed import MacroContext, CompanyFundamentals
from src.data.fundamentals_timeframe import DAILY_DATA, MONTHLY_DATA, YEARLY_DATA


class FundamentalAnalystAgent:
    """Agent 1: Multi-Timeframe Macro, Sector, and Corporate Fundamentals Evaluator."""

    # Timeframe weights — monthly is most relevant for intraday swing setups
    DAILY_WEIGHT   = 0.30
    MONTHLY_WEIGHT = 0.40
    YEARLY_WEIGHT  = 0.30

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self.long_threshold  = cfg.get("long_threshold",  62.0)
        self.short_threshold = cfg.get("short_threshold", 38.0)

    # ──────────────────────────────────────────────────────────────────────
    #  DAILY SCORE  (0 – 100)
    #  Factors: today's % change, volume surge, FII+DII net inflow,
    #           news sentiment, delivery %, put/call ratio.
    # ──────────────────────────────────────────────────────────────────────
    def _score_daily(self, symbol: str, macro: MacroContext) -> Tuple[float, list]:
        d = DAILY_DATA.get(symbol, {})
        score = 50.0
        reasons = []

        pct   = d.get("pct_change", 0.0)
        vr    = d.get("vol_ratio", 1.0)
        fii   = d.get("fii_net_cr", 0.0)
        dii   = d.get("dii_net_cr", 0.0)
        news  = d.get("news_sentiment", 0.0)
        deliv = d.get("delivery_pct", 50.0)
        pcr   = d.get("put_call_ratio", 1.0)

        # 1. Today's price change
        if pct >= 1.5:
            score += 12.0; reasons.append(f"Strong +{pct:.1f}% move today")
        elif pct >= 0.5:
            score += 6.0;  reasons.append(f"Positive +{pct:.1f}% day")
        elif pct <= -1.5:
            score -= 12.0; reasons.append(f"Weak {pct:.1f}% selloff today")
        elif pct < -0.5:
            score -= 6.0;  reasons.append(f"Negative {pct:.1f}% day")

        # 2. Volume surge (higher conviction of move)
        if vr >= 1.8:
            score += 10.0; reasons.append(f"Volume surge {vr:.1f}x avg")
        elif vr >= 1.3:
            score += 5.0;  reasons.append(f"Above-avg volume {vr:.1f}x")
        elif vr < 0.8:
            score -= 5.0;  reasons.append(f"Low volume {vr:.1f}x avg")

        # 3. FII + DII institutional net flows today
        net_flow = fii + dii
        if net_flow >= 300:
            score += 12.0; reasons.append(f"Heavy institutional buying ₹{net_flow:.0f}Cr today")
        elif net_flow >= 100:
            score += 6.0;  reasons.append(f"Institutional inflow ₹{net_flow:.0f}Cr today")
        elif net_flow <= -200:
            score -= 10.0; reasons.append(f"Institutional selling ₹{net_flow:.0f}Cr today")
        elif net_flow < 0:
            score -= 4.0;  reasons.append(f"Net outflow ₹{net_flow:.0f}Cr today")

        # 4. News sentiment [-1 to +1]
        if news >= 0.5:
            score += 8.0;  reasons.append(f"Strongly positive news ({news:.2f})")
        elif news >= 0.2:
            score += 4.0;  reasons.append(f"Positive news ({news:.2f})")
        elif news <= -0.5:
            score -= 8.0;  reasons.append(f"Strongly negative news ({news:.2f})")
        elif news < -0.2:
            score -= 4.0;  reasons.append(f"Negative news ({news:.2f})")

        # 5. Delivery volume % — high = institutional conviction
        if deliv >= 65:
            score += 6.0;  reasons.append(f"High delivery {deliv:.0f}% (institutional conviction)")
        elif deliv < 35:
            score -= 6.0;  reasons.append(f"Low delivery {deliv:.0f}% (speculative intraday)")

        # 6. Put/Call Ratio — low PCR = bullish, high = bearish
        if pcr <= 0.7:
            score += 8.0;  reasons.append(f"Bullish options positioning (PCR={pcr:.2f})")
        elif pcr >= 1.1:
            score -= 8.0;  reasons.append(f"Bearish options positioning (PCR={pcr:.2f})")

        # 7. Market VIX penalty
        if macro.india_vix > 18.0:
            score -= 8.0;  reasons.append(f"India VIX elevated at {macro.india_vix:.1f}")
        elif macro.india_vix < 13.0:
            score += 4.0;  reasons.append(f"India VIX low at {macro.india_vix:.1f}")

        return max(0.0, min(100.0, score)), reasons

    # ──────────────────────────────────────────────────────────────────────
    #  MONTHLY SCORE  (0 – 100)
    #  Factors: Q-o-Q revenue & PAT growth, EPS trend (3Q),
    #           FII 1-month net, sector rotation, analyst sentiment,
    #           management guidance.
    # ──────────────────────────────────────────────────────────────────────
    def _score_monthly(self, symbol: str) -> Tuple[float, list]:
        m = MONTHLY_DATA.get(symbol, {})
        score = 50.0
        reasons = []

        q_rev   = m.get("q_rev_growth", 0.0)
        q_pat   = m.get("q_pat_growth", 0.0)
        eps_t   = m.get("eps_trend", "flat")
        fii_1m  = m.get("fii_1m_cr", 0.0)
        sec_rot = m.get("sector_rotation", 50)
        upgr    = m.get("analyst_upgrades", 0)
        downgr  = m.get("analyst_downgrades", 0)
        guidance= m.get("mgmt_guidance", "neutral")

        # 1. Quarterly PAT growth QoQ
        if q_pat >= 20.0:
            score += 15.0; reasons.append(f"Stellar QoQ PAT growth +{q_pat:.0f}%")
        elif q_pat >= 10.0:
            score += 8.0;  reasons.append(f"Good QoQ PAT growth +{q_pat:.0f}%")
        elif q_pat < 0.0:
            score -= 12.0; reasons.append(f"PAT declined {q_pat:.0f}% QoQ")

        # 2. Quarterly Revenue growth QoQ
        if q_rev >= 12.0:
            score += 8.0;  reasons.append(f"Strong QoQ revenue growth +{q_rev:.1f}%")
        elif q_rev >= 6.0:
            score += 4.0;  reasons.append(f"Revenue growth +{q_rev:.1f}% QoQ")
        elif q_rev < 0.0:
            score -= 8.0;  reasons.append(f"Revenue declined {q_rev:.1f}% QoQ")

        # 3. EPS trend over last 3 quarters
        if eps_t == "up":
            score += 10.0; reasons.append("EPS trending up for 3 consecutive quarters")
        elif eps_t == "down":
            score -= 10.0; reasons.append("EPS trending down — earnings deterioration")

        # 4. FII 1-month net flow
        if fii_1m >= 1500:
            score += 12.0; reasons.append(f"Very heavy FII buying ₹{fii_1m:.0f}Cr this month")
        elif fii_1m >= 500:
            score += 6.0;  reasons.append(f"FII inflow ₹{fii_1m:.0f}Cr this month")
        elif fii_1m <= -500:
            score -= 10.0; reasons.append(f"FII selling ₹{abs(fii_1m):.0f}Cr this month")

        # 5. Sector rotation score (0-100)
        if sec_rot >= 70:
            score += 8.0;  reasons.append(f"Strong sector rotation into this sector ({sec_rot})")
        elif sec_rot <= 45:
            score -= 6.0;  reasons.append(f"Sector under rotation pressure ({sec_rot})")

        # 6. Analyst activity net (upgrades - downgrades)
        net_analyst = upgr - downgr
        if net_analyst >= 3:
            score += 8.0;  reasons.append(f"Net +{net_analyst} analyst upgrades this month")
        elif net_analyst <= -2:
            score -= 8.0;  reasons.append(f"Net {net_analyst} analyst downgrades this month")

        # 7. Management guidance
        if guidance == "positive":
            score += 6.0;  reasons.append("Positive management guidance this quarter")
        elif guidance == "negative":
            score -= 8.0;  reasons.append("Negative management guidance / warning")

        return max(0.0, min(100.0, score)), reasons

    # ──────────────────────────────────────────────────────────────────────
    #  YEARLY SCORE  (0 – 100)
    #  Factors: 3Y revenue / PAT / EPS CAGR, average ROE, debt reduction,
    #           FCF yield, ESG governance score, market share trend.
    # ──────────────────────────────────────────────────────────────────────
    def _score_yearly(self, symbol: str, fundamentals: CompanyFundamentals) -> Tuple[float, list]:
        y = YEARLY_DATA.get(symbol, {})
        score = 50.0
        reasons = []

        rev_cagr = y.get("rev_cagr_3y", 8.0)
        pat_cagr = y.get("pat_cagr_3y", 8.0)
        eps_cagr = y.get("eps_cagr_3y", 8.0)
        roe3y    = y.get("roe_avg_3y",  15.0)
        debt_red = y.get("debt_reduction_pct", 0.0)
        div_yld  = y.get("div_yield", 0.5)
        fcf_yld  = y.get("fcf_yield", 1.5)
        esg      = y.get("esg_score", 60)
        mkt_shr  = y.get("market_share", "stable")

        # 1. 3Y PAT CAGR — long-term profit engine strength
        if pat_cagr >= 20.0:
            score += 15.0; reasons.append(f"Exceptional 3Y PAT CAGR of {pat_cagr:.0f}%")
        elif pat_cagr >= 12.0:
            score += 8.0;  reasons.append(f"Strong 3Y PAT CAGR of {pat_cagr:.0f}%")
        elif pat_cagr < 5.0:
            score -= 10.0; reasons.append(f"Weak 3Y PAT CAGR of {pat_cagr:.0f}%")

        # 2. 3Y Revenue CAGR
        if rev_cagr >= 15.0:
            score += 8.0;  reasons.append(f"Strong 3Y revenue CAGR {rev_cagr:.0f}%")
        elif rev_cagr < 6.0:
            score -= 6.0;  reasons.append(f"Sluggish 3Y revenue CAGR {rev_cagr:.0f}%")

        # 3. Average 3Y ROE
        if roe3y >= 25.0:
            score += 10.0; reasons.append(f"Excellent 3Y avg ROE of {roe3y:.0f}%")
        elif roe3y >= 15.0:
            score += 5.0;  reasons.append(f"Good 3Y avg ROE of {roe3y:.0f}%")
        elif roe3y < 10.0:
            score -= 8.0;  reasons.append(f"Poor ROE of {roe3y:.0f}% (below cost of capital)")

        # 4. Debt reduction (positive = reduced debt)
        if debt_red >= 15.0:
            score += 8.0;  reasons.append(f"Significant debt reduction of {debt_red:.0f}%")
        elif debt_red <= -10.0:
            score -= 10.0; reasons.append(f"Debt increased {abs(debt_red):.0f}% — balance sheet risk")

        # 5. Free Cash Flow Yield
        if fcf_yld >= 4.0:
            score += 6.0;  reasons.append(f"High FCF yield {fcf_yld:.1f}% (cash generative)")
        elif fcf_yld < 1.0:
            score -= 4.0;  reasons.append(f"Low FCF yield {fcf_yld:.1f}% — capital intensive")

        # 6. ESG / governance (higher = better governed)
        if esg >= 80:
            score += 5.0;  reasons.append(f"Strong ESG/governance score {esg}")
        elif esg < 50:
            score -= 5.0;  reasons.append(f"Weak governance ESG score {esg}")

        # 7. Market share trajectory
        if mkt_shr == "gaining":
            score += 8.0;  reasons.append("Company gaining market share structurally")
        elif mkt_shr == "losing":
            score -= 10.0; reasons.append("Market share erosion — competitive threat")

        # 8. Promoter pledging from fundamentals model
        if fundamentals.promoter_pledge_percent > 15.0:
            score -= 15.0; reasons.append(f"High promoter pledge {fundamentals.promoter_pledge_percent:.0f}% — governance risk")
        elif fundamentals.promoter_pledge_percent == 0.0:
            score += 5.0;  reasons.append("Zero promoter pledge — clean governance")

        return max(0.0, min(100.0, score)), reasons

    # ──────────────────────────────────────────────────────────────────────
    #  MARKET REGIME SCORE  (used as macro context layer)
    # ──────────────────────────────────────────────────────────────────────
    def _score_market_regime(self, macro: MacroContext) -> float:
        score = 50.0
        if macro.nifty50_1m_return > 3.0:  score += 12.0
        elif macro.nifty50_1m_return < -3.0: score -= 12.0
        if macro.nifty50_1w_return > 1.0:  score += 8.0
        elif macro.nifty50_1w_return < -1.0: score -= 8.0
        if macro.india_vix < 13.0: score += 8.0
        elif macro.india_vix > 18.0: score -= 12.0
        if macro.advance_decline_ratio > 1.4: score += 8.0
        elif macro.advance_decline_ratio < 0.7: score -= 8.0
        net_flow = macro.fii_net_flow_5d_cr + macro.dii_net_flow_5d_cr
        if net_flow > 2000: score += 8.0
        elif net_flow < -2000: score -= 8.0
        return max(0.0, min(100.0, score))

    # ──────────────────────────────────────────────────────────────────────
    #  MAIN ANALYZE  — called by orchestrator for each symbol
    # ──────────────────────────────────────────────────────────────────────
    def analyze(
        self,
        symbol: str,
        macro: MacroContext,
        fundamentals: CompanyFundamentals,
        sector_rs_score: float = 60.0,
        news_sentiment_score: float = 0.0,
        now: Optional[datetime] = None
    ) -> FundamentalSignal:
        """Run multi-timeframe (Daily / Monthly / Yearly) fundamental analysis."""
        timestamp = now or macro.timestamp
        rationale = []

        # Hard Veto: Event Risk (earnings, ban, surveillance)
        if fundamentals.is_results_due_in_24h:
            return FundamentalSignal(
                symbol=symbol, timestamp=timestamp,
                direction=SignalDirection.NEUTRAL, confidence=0.0,
                rationale=["VETO: Earnings announcement due within 24h — no trade allowed."],
                features={"event_risk_veto": True, "reason": "EARNINGS_ANNOUNCEMENT"}
            )
        if fundamentals.is_fo_ban or fundamentals.is_asm_gsm:
            return FundamentalSignal(
                symbol=symbol, timestamp=timestamp,
                direction=SignalDirection.NEUTRAL, confidence=0.0,
                rationale=["VETO: F&O ban or ASM/GSM surveillance active."],
                features={"event_risk_veto": True, "reason": "SURVEILLANCE_BAN"}
            )

        # ── Three-Layer Scoring ─────────────────────────────────────────
        daily_score,   daily_reasons   = self._score_daily(symbol, macro)
        monthly_score, monthly_reasons = self._score_monthly(symbol)
        yearly_score,  yearly_reasons  = self._score_yearly(symbol, fundamentals)
        regime_score = self._score_market_regime(macro)

        # Weighted composite
        composite = (
            self.DAILY_WEIGHT   * daily_score
            + self.MONTHLY_WEIGHT * monthly_score
            + self.YEARLY_WEIGHT  * yearly_score
        )

        # Blend with macro regime (acts as a final overlay, ±10 points max)
        regime_adj = (regime_score - 50.0) * 0.15
        final_score = max(0.0, min(100.0, composite + regime_adj))

        # ── Direction & Confidence ───────────────────────────────────────
        if final_score >= self.long_threshold:
            direction = SignalDirection.LONG
            rationale.append(f"Multi-timeframe composite {final_score:.1f} → LONG bias")
        elif final_score <= self.short_threshold:
            direction = SignalDirection.SHORT
            rationale.append(f"Multi-timeframe composite {final_score:.1f} → SHORT bias")
        else:
            direction = SignalDirection.NEUTRAL
            rationale.append(f"Multi-timeframe composite {final_score:.1f} → NEUTRAL (consolidation band {self.short_threshold}-{self.long_threshold})")

        # Add top reasons from each layer
        rationale += [f"[DAILY]   {r}" for r in daily_reasons[:2]]
        rationale += [f"[MONTHLY] {r}" for r in monthly_reasons[:2]]
        rationale += [f"[YEARLY]  {r}" for r in yearly_reasons[:2]]

        confidence = min(1.0, max(0.0, abs(final_score - 50.0) / 50.0))

        return FundamentalSignal(
            symbol=symbol,
            timestamp=timestamp,
            direction=direction,
            confidence=round(confidence, 3),
            horizon=TradingHorizon.INTRADAY,
            rationale=rationale,
            features={
                # Composite
                "fund_score":           round(final_score, 2),
                "regime_score":         round(regime_score, 2),
                "regime_adjustment":    round(regime_adj, 2),
                # Per-timeframe scores
                "daily_score":          round(daily_score, 2),
                "monthly_score":        round(monthly_score, 2),
                "yearly_score":         round(yearly_score, 2),
                # Layer weights
                "daily_weight":         self.DAILY_WEIGHT,
                "monthly_weight":       self.MONTHLY_WEIGHT,
                "yearly_weight":        self.YEARLY_WEIGHT,
                # Key sub-signals
                "sector_rs_score":      round(sector_rs_score, 2),
                "india_vix":            macro.india_vix,
                "fii_dii_net_flow_cr":  macro.fii_net_flow_5d_cr + macro.dii_net_flow_5d_cr,
                "news_sentiment":       news_sentiment_score,
                # Daily sub-signals
                "daily_pct_change":     DAILY_DATA.get(symbol, {}).get("pct_change", 0.0),
                "daily_vol_ratio":      DAILY_DATA.get(symbol, {}).get("vol_ratio", 1.0),
                "daily_fii_net_cr":     DAILY_DATA.get(symbol, {}).get("fii_net_cr", 0.0),
                "delivery_pct":         DAILY_DATA.get(symbol, {}).get("delivery_pct", 50.0),
                "put_call_ratio":       DAILY_DATA.get(symbol, {}).get("put_call_ratio", 1.0),
                # Monthly sub-signals
                "q_pat_growth":         MONTHLY_DATA.get(symbol, {}).get("q_pat_growth", 0.0),
                "q_rev_growth":         MONTHLY_DATA.get(symbol, {}).get("q_rev_growth", 0.0),
                "eps_trend":            MONTHLY_DATA.get(symbol, {}).get("eps_trend", "flat"),
                "mgmt_guidance":        MONTHLY_DATA.get(symbol, {}).get("mgmt_guidance", "neutral"),
                "analyst_net":          MONTHLY_DATA.get(symbol, {}).get("analyst_upgrades", 0) - MONTHLY_DATA.get(symbol, {}).get("analyst_downgrades", 0),
                # Yearly sub-signals
                "pat_cagr_3y":          YEARLY_DATA.get(symbol, {}).get("pat_cagr_3y", 0.0),
                "rev_cagr_3y":          YEARLY_DATA.get(symbol, {}).get("rev_cagr_3y", 0.0),
                "roe_avg_3y":           YEARLY_DATA.get(symbol, {}).get("roe_avg_3y", 0.0),
                "fcf_yield":            YEARLY_DATA.get(symbol, {}).get("fcf_yield", 0.0),
                "esg_score":            YEARLY_DATA.get(symbol, {}).get("esg_score", 60),
                "market_share":         YEARLY_DATA.get(symbol, {}).get("market_share", "stable"),
            }
        )

    def get_multi_timeframe_breakdown(
        self,
        symbol: str,
        macro: Optional[MacroContext] = None,
        fundamentals: Optional[CompanyFundamentals] = None
    ) -> Dict[str, Any]:
        """Compute and return detailed multi-timeframe fundamental metrics for Daily, Monthly, and Yearly."""
        m_ctx = macro or MacroContext(
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
        f_ctx = fundamentals or CompanyFundamentals(
            symbol=symbol, sector="EQUITY", pe_ratio=25.0, sector_pe=25.0,
            pb_ratio=3.0, roe_percent=15.0, roce_percent=18.0, debt_to_equity=0.5,
            revenue_growth_yoy=10.0, pat_growth_yoy=12.0, promoter_holding_percent=50.0,
            promoter_pledge_percent=0.0
        )
        daily_score, daily_reasons = self._score_daily(symbol, m_ctx)
        monthly_score, monthly_reasons = self._score_monthly(symbol)
        yearly_score, yearly_reasons = self._score_yearly(symbol, f_ctx)
        regime_score = self._score_market_regime(m_ctx)
        composite = (
            self.DAILY_WEIGHT * daily_score
            + self.MONTHLY_WEIGHT * monthly_score
            + self.YEARLY_WEIGHT * yearly_score
        )
        regime_adj = (regime_score - 50.0) * 0.15
        final_score = max(0.0, min(100.0, composite + regime_adj))
        direction = "LONG" if final_score >= self.long_threshold else ("SHORT" if final_score <= self.short_threshold else "NEUTRAL")
        confidence = min(1.0, max(0.0, abs(final_score - 50.0) / 50.0))

        return {
            "symbol": symbol,
            "direction": direction,
            "confidence": round(confidence, 3),
            "composite_score": round(final_score, 1),
            "weights": {
                "daily": self.DAILY_WEIGHT,
                "monthly": self.MONTHLY_WEIGHT,
                "yearly": self.YEARLY_WEIGHT
            },
            "daily": {
                "score": round(daily_score, 1),
                "bias": "BULLISH" if daily_score >= 60 else ("BEARISH" if daily_score <= 40 else "NEUTRAL"),
                "reasons": daily_reasons,
                "metrics": DAILY_DATA.get(symbol, {})
            },
            "monthly": {
                "score": round(monthly_score, 1),
                "bias": "BULLISH" if monthly_score >= 60 else ("BEARISH" if monthly_score <= 40 else "NEUTRAL"),
                "reasons": monthly_reasons,
                "metrics": MONTHLY_DATA.get(symbol, {})
            },
            "yearly": {
                "score": round(yearly_score, 1),
                "bias": "BULLISH" if yearly_score >= 60 else ("BEARISH" if yearly_score <= 40 else "NEUTRAL"),
                "reasons": yearly_reasons,
                "metrics": YEARLY_DATA.get(symbol, {})
            },
            "macro": {
                "regime_score": round(regime_score, 1),
                "regime_adjustment": round(regime_adj, 2),
                "india_vix": m_ctx.india_vix
            }
        }

