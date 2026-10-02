"""Agent 3: Execution Agent.

Evaluates the strict consensus gate between Agent 1 and Agent 2,
coordinates with the DeterministicRiskEngine, and constructs bracketed orders.
"""

from datetime import datetime
import uuid
from typing import Dict, Any, Optional, Tuple
from src.core.constants import SignalDirection, OrderSide, ProductType, RiskAction
from src.core.models import (
    FundamentalSignal,
    TechnicalSignal,
    ConsensusResult,
    TradeProposal,
    RiskVerdict,
    PortfolioState
)
from src.risk.engine import DeterministicRiskEngine

class ExecutionAgent:
    """Agent 3: Consensus Evaluator and Trade Proposal Coordinator."""

    def __init__(self, risk_engine: DeterministicRiskEngine, config: Optional[Dict[str, Any]] = None):
        self.risk_engine = risk_engine
        cfg = config or {}
        consensus_cfg = cfg.get("consensus", {})
        self.min_fund_conf = consensus_cfg.get("min_fund_confidence", 0.40)
        self.min_tech_conf = consensus_cfg.get("min_tech_confidence", 0.60)
        self.min_combined_conviction = consensus_cfg.get("min_combined_conviction", 0.65)
        self.w_fund = consensus_cfg.get("fund_weight", 0.40)
        self.w_tech = consensus_cfg.get("tech_weight", 0.60)

    def evaluate_consensus(
        self,
        fund_signal: FundamentalSignal,
        tech_signal: TechnicalSignal
    ) -> ConsensusResult:
        """Evaluate strict consensus gate between Agent 1 and Agent 2."""
        now = datetime.now()
        symbol = fund_signal.symbol

        # Check 1: Directional agreement (neither can be NEUTRAL)
        if fund_signal.direction == SignalDirection.NEUTRAL or tech_signal.direction == SignalDirection.NEUTRAL:
            return ConsensusResult(
                symbol=symbol,
                timestamp=now,
                consensus_reached=False,
                direction=SignalDirection.NEUTRAL,
                combined_conviction=0.0,
                fund_confidence=fund_signal.confidence,
                tech_confidence=tech_signal.confidence,
                calibrated_win_prob=tech_signal.win_prob,
                payoff_ratio=tech_signal.payoff_ratio,
                reason="At least one agent returned NEUTRAL bias (Abstention)."
            )

        if fund_signal.direction != tech_signal.direction:
            return ConsensusResult(
                symbol=symbol,
                timestamp=now,
                consensus_reached=False,
                direction=SignalDirection.NEUTRAL,
                combined_conviction=0.0,
                fund_confidence=fund_signal.confidence,
                tech_confidence=tech_signal.confidence,
                calibrated_win_prob=tech_signal.win_prob,
                payoff_ratio=tech_signal.payoff_ratio,
                reason=f"Directional conflict: Fundamental={fund_signal.direction.value} vs Technical={tech_signal.direction.value}."
            )

        # Check 2: Minimum confidence thresholds
        if fund_signal.confidence < self.min_fund_conf:
            return ConsensusResult(
                symbol=symbol,
                timestamp=now,
                consensus_reached=False,
                direction=fund_signal.direction,
                combined_conviction=0.0,
                fund_confidence=fund_signal.confidence,
                tech_confidence=tech_signal.confidence,
                calibrated_win_prob=tech_signal.win_prob,
                payoff_ratio=tech_signal.payoff_ratio,
                reason=f"Fundamental confidence ({fund_signal.confidence:.2f}) is below minimum {self.min_fund_conf}."
            )

        if tech_signal.confidence < self.min_tech_conf:
            return ConsensusResult(
                symbol=symbol,
                timestamp=now,
                consensus_reached=False,
                direction=tech_signal.direction,
                combined_conviction=0.0,
                fund_confidence=fund_signal.confidence,
                tech_confidence=tech_signal.confidence,
                calibrated_win_prob=tech_signal.win_prob,
                payoff_ratio=tech_signal.payoff_ratio,
                reason=f"Technical confidence ({tech_signal.confidence:.2f}) is below minimum {self.min_tech_conf}."
            )

        # Check 3: Combined weighted conviction
        combined_conviction = (self.w_fund * fund_signal.confidence) + (self.w_tech * tech_signal.confidence)
        if combined_conviction < self.min_combined_conviction:
            return ConsensusResult(
                symbol=symbol,
                timestamp=now,
                consensus_reached=False,
                direction=fund_signal.direction,
                combined_conviction=round(combined_conviction, 3),
                fund_confidence=fund_signal.confidence,
                tech_confidence=tech_signal.confidence,
                calibrated_win_prob=tech_signal.win_prob,
                payoff_ratio=tech_signal.payoff_ratio,
                reason=f"Combined conviction ({combined_conviction:.2f}) below requirement {self.min_combined_conviction}."
            )

        # Check 4: Positive Expectancy (Calibrated Win Prob >= 0.55 & Payoff Ratio >= 1.5)
        if tech_signal.win_prob < 0.55 or tech_signal.payoff_ratio < 1.50:
            return ConsensusResult(
                symbol=symbol,
                timestamp=now,
                consensus_reached=False,
                direction=fund_signal.direction,
                combined_conviction=round(combined_conviction, 3),
                fund_confidence=fund_signal.confidence,
                tech_confidence=tech_signal.confidence,
                calibrated_win_prob=tech_signal.win_prob,
                payoff_ratio=tech_signal.payoff_ratio,
                reason=f"Positive expectancy check failed (p={tech_signal.win_prob:.2f} < 0.55 or b={tech_signal.payoff_ratio:.2f} < 1.50)."
            )

        return ConsensusResult(
            symbol=symbol,
            timestamp=now,
            consensus_reached=True,
            direction=fund_signal.direction,
            combined_conviction=round(combined_conviction, 3),
            fund_confidence=fund_signal.confidence,
            tech_confidence=tech_signal.confidence,
            calibrated_win_prob=tech_signal.win_prob,
            payoff_ratio=tech_signal.payoff_ratio,
            reason="High conviction consensus reached across fundamental and technical agents."
        )

    def build_trade_proposal(
        self,
        consensus: ConsensusResult,
        tech_signal: TechnicalSignal,
        portfolio: PortfolioState,
        sector: str = "GENERAL"
    ) -> Optional[TradeProposal]:
        """Convert consensus agreement into a concrete trade proposal."""
        if not consensus.consensus_reached:
            return None

        side = OrderSide.BUY if consensus.direction == SignalDirection.LONG else OrderSide.SELL
        risk_per_unit = abs(tech_signal.entry - tech_signal.stop_loss)

        if risk_per_unit <= 0.0 or tech_signal.kelly_fraction <= 0.0:
            return None

        # Suggested quantity calculated from Kelly fraction and capital allocation
        suggested_risk = portfolio.total_capital * tech_signal.kelly_fraction
        suggested_qty = int(suggested_risk / risk_per_unit)

        # If capital is insufficient to purchase even 1 unit within risk budget, return None
        if suggested_qty <= 0:
            return None

        return TradeProposal(
            proposal_id=str(uuid.uuid4()),
            symbol=tech_signal.symbol,
            sector=sector,
            side=side,
            product_type=ProductType.MIS,
            entry_price=tech_signal.entry,
            stop_loss=tech_signal.stop_loss,
            target_price=tech_signal.target,
            suggested_quantity=suggested_qty,
            suggested_risk_amount=round(suggested_risk, 2),
            kelly_fraction=tech_signal.kelly_fraction,
            calibrated_win_prob=tech_signal.win_prob,
            payoff_ratio=tech_signal.payoff_ratio,
            timestamp=datetime.now()
        )

    def process_cycle(
        self,
        fund_signal: FundamentalSignal,
        tech_signal: TechnicalSignal,
        portfolio: PortfolioState,
        sector: str = "GENERAL",
        is_restricted_event: bool = False,
        adv_crores: float = 25.0,
        enforce_timing: bool = True
    ) -> Tuple[ConsensusResult, Optional[TradeProposal], Optional[RiskVerdict]]:
        """Run full Agent 3 evaluation: Consensus Gate -> Proposal -> Deterministic Risk Engine."""
        consensus = self.evaluate_consensus(fund_signal, tech_signal)
        if not consensus.consensus_reached:
            return consensus, None, None

        proposal = self.build_trade_proposal(consensus, tech_signal, portfolio, sector=sector)
        if not proposal:
            return consensus, None, None

        verdict = self.risk_engine.evaluate_proposal(
            proposal=proposal,
            portfolio=portfolio,
            is_restricted_event=is_restricted_event,
            adv_crores=adv_crores,
            enforce_timing=enforce_timing
        )

        return consensus, proposal, verdict
