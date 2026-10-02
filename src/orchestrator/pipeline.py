"""Orchestrator: Coordinates Scheduler, Parallel Agents, Risk Engine, and Broker."""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import concurrent.futures
from src.core.constants import SignalDirection, RiskAction
from src.core.models import (
    FundamentalSignal,
    TechnicalSignal,
    ConsensusResult,
    TradeProposal,
    RiskVerdict,
    PortfolioState,
    Order
)
from src.data.calendar import NSECalendar
from src.data.feed import MacroContext, CompanyFundamentals, Quote
from src.agents.agent1_fundamental import FundamentalAnalystAgent
from src.agents.agent2_technical import TechnicalAnalystAgent
from src.agents.agent3_execution import ExecutionAgent
from src.risk.engine import DeterministicRiskEngine
from src.broker.base import BaseBrokerAdapter
from src.memory.journal import TradeJournal

class TradingOrchestrator:
    """Central pipeline orchestrating the autonomous 3-agent cycle."""

    def __init__(
        self,
        agent1: FundamentalAnalystAgent,
        agent2: TechnicalAnalystAgent,
        agent3: ExecutionAgent,
        risk_engine: DeterministicRiskEngine,
        broker: BaseBrokerAdapter,
        journal: TradeJournal,
        config: Optional[Dict[str, Any]] = None
    ):
        self.agent1 = agent1
        self.agent2 = agent2
        self.agent3 = agent3
        self.risk_engine = risk_engine
        self.broker = broker
        self.journal = journal
        self.config = config or {}

    def compute_day_profit_potential(
        self,
        win_prob: float,
        fund_score: float,
        adx: float,
        volume_ratio: float,
        orderflow: Dict[str, Any],
        target_pct: float = 18.0,
        stop_pct: float = 5.0
    ) -> Dict[str, float]:
        """Calculates expected profit and alpha potential score for universe ranking."""
        ev_pct = (win_prob * target_pct) - ((1.0 - win_prob) * stop_pct)
        fund_factor = max(0.5, 0.7 + (fund_score / 100.0) * 0.6)  # Score 86 -> 1.216x
        adx_factor = max(1.0, min(50.0, adx) / 25.0)             # ADX 32 -> 1.28x
        vol_factor = max(1.0, min(2.5, volume_ratio))            # Vol 1.6x -> 1.6x

        cvd = orderflow.get("cumulative_volume_delta", orderflow.get("cumulative_delta", 0))
        bid_depth = orderflow.get("bid_depth_qty", 100000)
        ask_depth = max(1, orderflow.get("ask_depth_qty", 100000))
        imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth) if (bid_depth + ask_depth) > 0 else 0.0
        of_factor = 1.0 + (0.20 if cvd > 0 else -0.10) + max(-0.15, min(0.20, imbalance * 0.5))

        alpha_score = ev_pct * fund_factor * adx_factor * vol_factor * of_factor
        return {
            "expected_profit_pct": round(ev_pct, 2),
            "leveraged_expected_profit_pct": round(ev_pct * 5.0, 2),  # 5x broker margin leverage
            "day_profit_potential_score": round(alpha_score, 2),
            "fund_factor": round(fund_factor, 3),
            "momentum_factor": round(adx_factor * vol_factor, 3),
            "orderflow_factor": round(of_factor, 3)
        }

    def run_cycle_for_symbol(
        self,
        symbol: str,
        sector: str,
        quote: Quote,
        macro: MacroContext,
        fundamentals: CompanyFundamentals,
        technical_inputs: Dict[str, Any],
        current_time: Optional[datetime] = None,
        enforce_timing: bool = True,
        execute_order: bool = True
    ) -> Dict[str, Any]:
        """Execute one complete decision cycle for a given symbol."""
        now = current_time or NSECalendar.get_ist_now()
        cycle_id = f"CYC-{str(uuid.uuid4())[:8]}"
        decision_id = str(uuid.uuid4())

        # Step 1: Market Hours & Safe Trade Window Check
        if enforce_timing and not NSECalendar.is_trade_window_open(now):
            return {
                "cycle_id": cycle_id,
                "symbol": symbol,
                "action": "NO_TRADE",
                "reason": "Outside allowed algorithmic execution window (09:30-15:00 IST)"
            }

        # Step 2: Fetch Live Portfolio State
        portfolio = self.broker.get_portfolio_state()

        # Step 3: Run Agent 1 and Agent 2 in Parallel (Zero Anchoring Bias)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_agent1 = executor.submit(
                self.agent1.analyze,
                symbol=symbol,
                macro=macro,
                fundamentals=fundamentals,
                sector_rs_score=technical_inputs.get("sector_rs_score", 55.0),
                news_sentiment_score=technical_inputs.get("news_sentiment_score", 0.0),
                now=now
            )
            future_agent2 = executor.submit(
                self.agent2.analyze,
                symbol=symbol,
                current_price=quote.last_price,
                ema20=technical_inputs.get("ema20", quote.last_price),
                ema50=technical_inputs.get("ema50", quote.last_price),
                ema200=technical_inputs.get("ema200", quote.last_price),
                adx=technical_inputs.get("adx", 20.0),
                rsi14=technical_inputs.get("rsi14", 50.0),
                macd_hist=technical_inputs.get("macd_hist", 0.0),
                atr14=technical_inputs.get("atr14", max(2.0, quote.last_price * 0.01)),
                vwap=technical_inputs.get("vwap", quote.last_price),
                volume_ratio=technical_inputs.get("volume_ratio", 1.0),
                orderflow=technical_inputs.get("orderflow"),
                portfolio_capital=portfolio.total_capital,
                now=now
            )
            fund_signal: FundamentalSignal = future_agent1.result()
            tech_signal: TechnicalSignal = future_agent2.result()

        # Step 4: Agent 3 Consensus Evaluation & Risk Check
        consensus, proposal, risk_verdict = self.agent3.process_cycle(
            fund_signal=fund_signal,
            tech_signal=tech_signal,
            portfolio=portfolio,
            sector=sector,
            is_restricted_event=fundamentals.is_results_due_in_24h or fundamentals.is_fo_ban or fundamentals.is_asm_gsm,
            adv_crores=technical_inputs.get("adv_crores", 25.0),
            enforce_timing=enforce_timing
        )

        # Calculate Day Profit Potential
        fund_composite = fund_signal.features.get("fund_score", 50.0)
        profit_metrics = self.compute_day_profit_potential(
            win_prob=tech_signal.confidence,
            fund_score=fund_composite,
            adx=technical_inputs.get("adx", 20.0),
            volume_ratio=technical_inputs.get("volume_ratio", 1.0),
            orderflow=technical_inputs.get("orderflow") or {}
        )

        # Step 5: Execution Decision
        action = "NO_TRADE"
        reason = "Consensus not reached"
        executed_order: Optional[Order] = None

        if not consensus.consensus_reached:
            reason = consensus.reason
        elif risk_verdict and risk_verdict.action == RiskAction.VETOED:
            reason = f"Risk Engine Veto: {risk_verdict.reason}"
        elif risk_verdict and risk_verdict.approved_quantity > 0:
            if execute_order:
                action = "TRADE"
                reason = f"Approved ({risk_verdict.action.value}) {risk_verdict.approved_quantity} units. Risk: ₹{risk_verdict.approved_risk_amount:,.2f}"

                # Step 6: Submit to Broker — passes sector for position tracking
                executed_order = self.broker.submit_bracket_order(
                    symbol=symbol,
                    side=proposal.side.value,
                    quantity=risk_verdict.approved_quantity,
                    entry_price=proposal.entry_price,
                    stop_loss=proposal.stop_loss,
                    target_price=proposal.target_price,
                    sector=sector
                )
            else:
                action = "QUALIFIED_CANDIDATE"
                reason = f"Candidate approved: {risk_verdict.approved_quantity} units with expected profit {profit_metrics['expected_profit_pct']}%"

        # Step 7: Record Audit Trail to Memory Journal (only when executed directly)
        if execute_order:
            self.journal.record_decision(
                decision_id=decision_id,
                cycle_id=cycle_id,
                symbol=symbol,
                fund_signal=fund_signal,
                tech_signal=tech_signal,
                consensus_reached=consensus.consensus_reached,
                risk_verdict=risk_verdict,
                action=action,
                reason=reason
            )

        return {
            "cycle_id": cycle_id,
            "decision_id": decision_id,
            "symbol": symbol,
            "sector": sector,
            "fund_direction": fund_signal.direction.value,
            "fund_confidence": fund_signal.confidence,
            "fund_score": fund_composite,
            "fund_daily_score": fund_signal.features.get("daily_score", 50.0),
            "fund_monthly_score": fund_signal.features.get("monthly_score", 50.0),
            "fund_yearly_score": fund_signal.features.get("yearly_score", 50.0),
            "fund_features": fund_signal.features,
            "fund_rationale": fund_signal.rationale,
            "fund_signal": fund_signal,
            "tech_direction": tech_signal.direction.value,
            "tech_confidence": tech_signal.confidence,
            "tech_signal": tech_signal,
            "consensus_reached": consensus.consensus_reached,
            "action": action,
            "reason": reason,
            "order": executed_order.model_dump() if executed_order else None,
            "proposal": proposal,
            "risk_verdict": risk_verdict,
            "profit_metrics": profit_metrics,
            "features": tech_signal.features,
            "orderflow": {
                "orderflow_score": tech_signal.features.get("orderflow_score", 0.0),
                "order_book_imbalance": tech_signal.features.get("order_book_imbalance", 0.0),
                "cumulative_volume_delta": tech_signal.features.get("cumulative_volume_delta", 0),
                "delta_ratio": tech_signal.features.get("delta_ratio", 0.0),
                "institutional_block_bias": tech_signal.features.get("institutional_block_bias", 0.0),
                "orderflow_regime": tech_signal.features.get("orderflow_regime", "BALANCED")
            },
            "tech_rationale": tech_signal.rationale
        }

    def execute_approved_trade(
        self,
        symbol: str,
        sector: str,
        proposal: TradeProposal,
        risk_verdict: RiskVerdict,
        fund_signal: FundamentalSignal,
        tech_signal: TechnicalSignal,
        cycle_id: str,
        decision_id: str
    ) -> Optional[Order]:
        """Submits an approved proposal for execution to the broker and logs to the journal."""
        executed_order = self.broker.submit_bracket_order(
            symbol=symbol,
            side=proposal.side.value,
            quantity=risk_verdict.approved_quantity,
            entry_price=proposal.entry_price,
            stop_loss=proposal.stop_loss,
            target_price=proposal.target_price,
            sector=sector
        )

        reason = f"Approved single top profit trade ({risk_verdict.action.value}) {risk_verdict.approved_quantity} units. Risk: ₹{risk_verdict.approved_risk_amount:,.2f}"

        self.journal.record_decision(
            decision_id=decision_id,
            cycle_id=cycle_id,
            symbol=symbol,
            fund_signal=fund_signal,
            tech_signal=tech_signal,
            consensus_reached=True,
            risk_verdict=risk_verdict,
            action="TRADE",
            reason=reason
        )
        return executed_order
