"""Agent 1: Fundamental & Market-Condition Analyst.

Evaluates macro indicators, 1-week and 1-month market trends, institutional flows (FII/DII),
sector relative strength, company fundamentals, and corporate event risk.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from src.core.constants import SignalDirection, TradingHorizon
from src.core.models import FundamentalSignal
from src.data.feed import MacroContext, CompanyFundamentals

class FundamentalAnalystAgent:
    """Agent 1: Macro, Sector, and Corporate Fundamentals Evaluator."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        weights = cfg.get("weights", {})
        self.w_regime = weights.get("market_regime", 0.30)
        self.w_sector = weights.get("sector_strength", 0.20)
        self.w_quality = weights.get("company_quality", 0.30)
        self.w_sentiment = weights.get("news_sentiment", 0.20)

        thresholds = cfg.get("thresholds", {})
        self.long_threshold = thresholds.get("long_score", 65.0)
        self.short_threshold = thresholds.get("short_score", 35.0)

    def calculate_market_regime_score(self, macro: MacroContext) -> float:
        """Compute market regime score in range [0, 100]."""
        score = 50.0

        # Trend context (1W & 1M return)
        if macro.nifty50_1m_return > 3.0:
            score += 15.0
        elif macro.nifty50_1m_return < -3.0:
            score -= 15.0

        if macro.nifty50_1w_return > 1.0:
            score += 10.0
        elif macro.nifty50_1w_return < -1.0:
            score -= 10.0

        # India VIX penalty / bonus (VIX > 20 indicates elevated uncertainty)
        if macro.india_vix < 13.0:
            score += 10.0
        elif macro.india_vix > 18.0:
            score -= 15.0

        # Market breadth (advance / decline)
        if macro.advance_decline_ratio > 1.4:
            score += 10.0
        elif macro.advance_decline_ratio < 0.7:
            score -= 10.0

        # Institutional flows (FII + DII 5-day net)
        net_flow = macro.fii_net_flow_5d_cr + macro.dii_net_flow_5d_cr
        if net_flow > 2000.0:
            score += 10.0
        elif net_flow < -2000.0:
            score -= 10.0

        return max(0.0, min(100.0, score))

    def calculate_company_quality_score(self, fundamentals: CompanyFundamentals) -> float:
        """Compute company financial health and valuation score in range [0, 100]."""
        score = 50.0

        # Profitability: ROE and ROCE
        if fundamentals.roe_percent > 18.0:
            score += 12.0
        elif fundamentals.roe_percent < 10.0:
            score -= 12.0

        if fundamentals.roce_percent > 20.0:
            score += 8.0
        elif fundamentals.roce_percent < 12.0:
            score -= 8.0

        # Growth: YoY revenue and PAT growth
        if fundamentals.pat_growth_yoy > 15.0:
            score += 15.0
        elif fundamentals.pat_growth_yoy < 0.0:
            score -= 15.0

        # Balance sheet leverage: Debt to Equity
        if fundamentals.debt_to_equity < 0.5:
            score += 10.0
        elif fundamentals.debt_to_equity > 1.5:
            score -= 15.0

        # Governance & Promoter pledging
        if fundamentals.promoter_pledge_percent > 15.0:
            score -= 20.0
        elif fundamentals.promoter_pledge_percent == 0.0:
            score += 5.0

        return max(0.0, min(100.0, score))

    def analyze(
        self,
        symbol: str,
        macro: MacroContext,
        fundamentals: CompanyFundamentals,
        sector_rs_score: float = 60.0,
        news_sentiment_score: float = 0.0,
        now: Optional[datetime] = None
    ) -> FundamentalSignal:
        """Run parallel-safe fundamental analysis and emit typed FundamentalSignal."""
        timestamp = now or macro.timestamp
        rationale = []

        # 1. Check Event Risk Filter (Hard Veto to NEUTRAL)
        if fundamentals.is_results_due_in_24h:
            rationale.append("VETO: Quarterly earnings results announcement due within 24 hours.")
            return FundamentalSignal(
                symbol=symbol,
                timestamp=timestamp,
                direction=SignalDirection.NEUTRAL,
                confidence=0.0,
                rationale=rationale,
                features={"event_risk_veto": True, "reason": "EARNINGS_ANNOUNCEMENT"}
            )

        if fundamentals.is_fo_ban or fundamentals.is_asm_gsm:
            rationale.append("VETO: Stock is under regulatory F&O ban or ASM/GSM surveillance list.")
            return FundamentalSignal(
                symbol=symbol,
                timestamp=timestamp,
                direction=SignalDirection.NEUTRAL,
                confidence=0.0,
                rationale=rationale,
                features={"event_risk_veto": True, "reason": "SURVEILLANCE_BAN"}
            )

        # 2. Compute individual components
        regime_score = self.calculate_market_regime_score(macro)
        quality_score = self.calculate_company_quality_score(fundamentals)

        # Normalize news sentiment from [-1.0, 1.0] to [0, 100]
        news_norm = ((news_sentiment_score + 1.0) / 2.0) * 100.0

        # 3. Aggregate composite score
        fund_score = (
            self.w_regime * regime_score
            + self.w_sector * sector_rs_score
            + self.w_quality * quality_score
            + self.w_sentiment * news_norm
        )

        # Direction and confidence
        if fund_score >= self.long_threshold:
            direction = SignalDirection.LONG
            rationale.append(f"Composite fundamental score ({fund_score:.1f}) exceeds long threshold ({self.long_threshold}).")
        elif fund_score <= self.short_threshold:
            direction = SignalDirection.SHORT
            rationale.append(f"Composite fundamental score ({fund_score:.1f}) is below short threshold ({self.short_threshold}).")
        else:
            direction = SignalDirection.NEUTRAL
            rationale.append(f"Composite fundamental score ({fund_score:.1f}) remains in neutral consolidation band.")

        confidence = min(1.0, max(0.0, abs(fund_score - 50.0) / 50.0))

        if macro.india_vix > 18.0:
            rationale.append(f"Elevated India VIX ({macro.india_vix:.1f}) urges caution.")
        if fundamentals.pat_growth_yoy > 15.0:
            rationale.append(f"Strong YoY PAT growth of {fundamentals.pat_growth_yoy:.1f}%.")

        return FundamentalSignal(
            symbol=symbol,
            timestamp=timestamp,
            direction=direction,
            confidence=round(confidence, 3),
            horizon=TradingHorizon.INTRADAY,
            rationale=rationale,
            features={
                "fund_score": round(fund_score, 2),
                "market_regime_score": round(regime_score, 2),
                "sector_rs_score": round(sector_rs_score, 2),
                "company_quality_score": round(quality_score, 2),
                "news_sentiment_score": round(news_sentiment_score, 2),
                "india_vix": macro.india_vix,
                "fii_dii_net_flow_cr": macro.fii_net_flow_5d_cr + macro.dii_net_flow_5d_cr
            }
        )
