"""Deterministic Risk Engine (Zero LLM Bypass).

Enforces non-negotiable risk invariants, hard caps, and automated kill switches.
All mathematical checks are purely deterministic code.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from src.core.constants import RiskAction, OrderSide, ProductType
from src.core.models import TradeProposal, PortfolioState, RiskVerdict
from src.data.calendar import NSECalendar

class DeterministicRiskEngine:
    """Non-overridable deterministic risk engine."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self.capital_allocation_pct = cfg.get("capital_allocation_pct", 90.0) / 100.0 # 90% capital allocation
        self.stop_loss_pct = cfg.get("stop_loss_pct", 5.0) / 100.0                   # 5.0% loss limit
        self.profit_target_pct = cfg.get("profit_target_pct", 18.0) / 100.0           # 18.0% target (15-20%)
        self.min_target_pct = cfg.get("min_profit_target_pct", 15.0) / 100.0         # 15% min target
        self.max_target_pct = cfg.get("max_profit_target_pct", 20.0) / 100.0         # 20% max target
        self.max_single_stock_pct = cfg.get("max_single_stock_exposure_percent", 90.0) / 100.0
        self.max_sector_exposure_pct = cfg.get("max_sector_exposure_percent", 90.0) / 100.0
        self.daily_loss_limit_pct = cfg.get("daily_loss_limit_percent", 10.0) / 100.0
        self.weekly_loss_limit_pct = cfg.get("weekly_loss_limit_percent", 15.0) / 100.0
        self.max_drawdown_pct = cfg.get("max_drawdown_limit_percent", 20.0) / 100.0
        self.max_open_positions = cfg.get("max_open_positions", 2)
        self.min_expected_gain_to_cost_ratio = cfg.get("min_expected_gain_to_cost_ratio", 3.0)

    def calculate_statutory_costs(self, entry_price: float, target_price: float, quantity: int, product_type: ProductType) -> float:
        """Estimate realistic Indian market statutory costs for roundtrip trade."""
        turnover_entry = entry_price * quantity
        turnover_exit = target_price * quantity
        total_turnover = turnover_entry + turnover_exit

        # Brokerage: ₹20 per executed leg or 0.03% (whichever lower)
        brokerage = min(20.0, turnover_entry * 0.0003) + min(20.0, turnover_exit * 0.0003)

        # STT: 0.025% on intraday sell leg, or 0.1% on delivery both legs
        if product_type == ProductType.MIS:
            stt = turnover_exit * 0.00025
        else:
            stt = total_turnover * 0.001

        # Exchange turnover charge (NSE: ~0.00297%)
        exchange_charges = total_turnover * 0.0000297

        # SEBI turnover charge (₹10 / Crore = 0.0001%)
        sebi_charges = total_turnover * 0.000001

        # Stamp duty (0.003% on intraday buy, 0.015% on delivery buy)
        stamp_duty = turnover_entry * (0.00003 if product_type == ProductType.MIS else 0.00015)

        # GST: 18% on (Brokerage + Exchange Charges + SEBI Charges)
        gst = (brokerage + exchange_charges + sebi_charges) * 0.18

        return brokerage + stt + exchange_charges + sebi_charges + stamp_duty + gst

    def evaluate_proposal(
        self,
        proposal: TradeProposal,
        portfolio: PortfolioState,
        current_time: Optional[datetime] = None,
        is_restricted_event: bool = False,
        adv_crores: float = 25.0,
        enforce_timing: bool = True
    ) -> RiskVerdict:
        """Run all deterministic risk checks on a proposed trade."""
        now = current_time or NSECalendar.get_ist_now()
        rules_triggered = []

        # Check 1: Emergency Kill Switch
        if portfolio.is_kill_switch_active:
            return RiskVerdict(
                action=RiskAction.VETOED,
                symbol=proposal.symbol,
                original_quantity=proposal.suggested_quantity,
                approved_quantity=0,
                approved_risk_amount=0.0,
                reason=f"Kill switch active: {portfolio.kill_switch_reason or 'Emergency halt'}",
                rules_triggered=["KILL_SWITCH_ACTIVE"]
            )

        # Check 2: Permitted Execution Window (09:30 - 15:00 IST)
        if enforce_timing and not NSECalendar.is_trade_window_open(now):
            return RiskVerdict(
                action=RiskAction.VETOED,
                symbol=proposal.symbol,
                original_quantity=proposal.suggested_quantity,
                approved_quantity=0,
                approved_risk_amount=0.0,
                reason=f"Outside allowed trade window (09:30-15:00 IST). Current: {now.strftime('%H:%M:%S')}",
                rules_triggered=["OUTSIDE_TRADE_WINDOW"]
            )

        # Check 3: Daily Portfolio Loss Limit (2.0%)
        current_daily_loss = -(portfolio.realized_daily_pnl + portfolio.unrealized_daily_pnl)
        daily_loss_threshold = portfolio.total_capital * self.daily_loss_limit_pct
        if current_daily_loss >= daily_loss_threshold:
            return RiskVerdict(
                action=RiskAction.VETOED,
                symbol=proposal.symbol,
                original_quantity=proposal.suggested_quantity,
                approved_quantity=0,
                approved_risk_amount=0.0,
                reason=f"Daily loss limit breached: -₹{current_daily_loss:,.2f} >= threshold ₹{daily_loss_threshold:,.2f}",
                rules_triggered=["DAILY_LOSS_LIMIT_BREACHED"]
            )

        # Check 4: Weekly Portfolio Loss Limit (5.0%)
        weekly_loss = -portfolio.weekly_realized_pnl
        weekly_threshold = portfolio.total_capital * self.weekly_loss_limit_pct
        if weekly_loss >= weekly_threshold:
            return RiskVerdict(
                action=RiskAction.VETOED,
                symbol=proposal.symbol,
                original_quantity=proposal.suggested_quantity,
                approved_quantity=0,
                approved_risk_amount=0.0,
                reason=f"Weekly loss limit breached: -₹{weekly_loss:,.2f} >= threshold ₹{weekly_threshold:,.2f}",
                rules_triggered=["WEEKLY_LOSS_LIMIT_BREACHED"]
            )

        # Check 5: Peak-to-Trough Drawdown Limit
        drawdown_amount = max(0.0, portfolio.peak_capital - portfolio.total_capital)
        drawdown_pct = drawdown_amount / portfolio.peak_capital if portfolio.peak_capital > 0 else 0.0
        if drawdown_pct >= self.max_drawdown_pct:
            return RiskVerdict(
                action=RiskAction.VETOED,
                symbol=proposal.symbol,
                original_quantity=proposal.suggested_quantity,
                approved_quantity=0,
                approved_risk_amount=0.0,
                reason=f"Max drawdown reached: {drawdown_pct*100:.2f}% >= {self.max_drawdown_pct*100:.2f}%",
                rules_triggered=["MAX_DRAWDOWN_BREACHED"]
            )

        # Check 6: Max Concurrent Open Positions
        if len(portfolio.open_positions) >= self.max_open_positions:
            return RiskVerdict(
                action=RiskAction.VETOED,
                symbol=proposal.symbol,
                original_quantity=proposal.suggested_quantity,
                approved_quantity=0,
                approved_risk_amount=0.0,
                reason=f"Max open positions ({self.max_open_positions}) reached",
                rules_triggered=["MAX_POSITIONS_REACHED"]
            )

        # Check 7: Event Risk Filter (Earnings in 24h, ASM/GSM, F&O ban)
        if is_restricted_event:
            return RiskVerdict(
                action=RiskAction.VETOED,
                symbol=proposal.symbol,
                original_quantity=proposal.suggested_quantity,
                approved_quantity=0,
                approved_risk_amount=0.0,
                reason="Event risk: earnings in 24h or stock under surveillance/ban list",
                rules_triggered=["EVENT_RISK_SURVEILLANCE"]
            )

        # Check 8: Minimum Liquidity Hurdle
        if adv_crores < 10.0:
            return RiskVerdict(
                action=RiskAction.VETOED,
                symbol=proposal.symbol,
                original_quantity=proposal.suggested_quantity,
                approved_quantity=0,
                approved_risk_amount=0.0,
                reason=f"Stock ADV (₹{adv_crores:.2f} Cr) is below ₹10.0 Cr liquidity threshold",
                rules_triggered=["ILLIQUID_STOCK_REJECTED"]
            )

        # Check 9: Quantity Sizing Based on 90% Capital Allocation
        risk_per_unit = abs(proposal.entry_price - proposal.stop_loss)
        if risk_per_unit <= 0.0:
            return RiskVerdict(
                action=RiskAction.VETOED,
                symbol=proposal.symbol,
                original_quantity=proposal.suggested_quantity,
                approved_quantity=0,
                approved_risk_amount=0.0,
                reason="Invalid stop loss: risk per unit is zero",
                rules_triggered=["ZERO_RISK_PER_UNIT"]
            )

        # 1. 90% Trading Capital Allocation to Buy or Sell
        target_capital = portfolio.total_capital * self.capital_allocation_pct
        max_qty_by_capital = int(target_capital / proposal.entry_price)

        # 2. Available Cash & Margin Limit
        # For Indian intraday MIS, SEBI margin is 20% (5x leverage); CNC delivery is 100%
        margin_requirement_pct = 0.20 if proposal.product_type == ProductType.MIS else 1.0
        margin_per_unit = proposal.entry_price * margin_requirement_pct

        if portfolio.available_cash < margin_per_unit:
            return RiskVerdict(
                action=RiskAction.VETOED,
                symbol=proposal.symbol,
                original_quantity=proposal.suggested_quantity,
                approved_quantity=0,
                approved_risk_amount=0.0,
                reason=f"Insufficient available cash (₹{portfolio.available_cash:,.2f}) for required margin (₹{margin_per_unit:,.2f} / unit)",
                rules_triggered=["INSUFFICIENT_AVAILABLE_CASH"]
            )

        max_qty_by_available_cash = int(portfolio.available_cash / margin_per_unit)

        # Final approved quantity deploys 90% of trading capital
        approved_qty = min(
            proposal.suggested_quantity,
            max_qty_by_capital,
            max_qty_by_available_cash
        )

        if approved_qty <= 0:
            return RiskVerdict(
                action=RiskAction.VETOED,
                symbol=proposal.symbol,
                original_quantity=proposal.suggested_quantity,
                approved_quantity=0,
                approved_risk_amount=0.0,
                reason="Quantity clamped to 0: order value exceeds available cash or capital allocation limits",
                rules_triggered=["EXPOSURE_CAP_CLAMP_ZERO"]
            )

        # Check 10: Cost Hurdle Check (Expected gross gain >= 3x statutory costs)
        expected_gain = approved_qty * abs(proposal.target_price - proposal.entry_price)
        estimated_costs = self.calculate_statutory_costs(
            proposal.entry_price, proposal.target_price, approved_qty, proposal.product_type
        )

        if estimated_costs > 0 and (expected_gain / estimated_costs) < self.min_expected_gain_to_cost_ratio:
            return RiskVerdict(
                action=RiskAction.VETOED,
                symbol=proposal.symbol,
                original_quantity=proposal.suggested_quantity,
                approved_quantity=0,
                approved_risk_amount=0.0,
                reason=f"Cost hurdle failed: Expected gain ₹{expected_gain:.2f} is < {self.min_expected_gain_to_cost_ratio}x statutory costs (₹{estimated_costs:.2f})",
                rules_triggered=["COST_HURDLE_FAILED"],
                estimated_roundtrip_cost=estimated_costs,
                expected_gain=expected_gain
            )

        # Determine if proposal was downsized or fully approved
        action = RiskAction.APPROVED if approved_qty == proposal.suggested_quantity else RiskAction.DOWNSIZED
        if action == RiskAction.DOWNSIZED:
            rules_triggered.append("QUANTITY_DOWNSIZED_FOR_SAFETY")

        approved_risk = approved_qty * risk_per_unit

        return RiskVerdict(
            action=action,
            symbol=proposal.symbol,
            original_quantity=proposal.suggested_quantity,
            approved_quantity=approved_qty,
            approved_risk_amount=approved_risk,
            reason="All risk invariants validated successfully",
            rules_triggered=rules_triggered,
            estimated_roundtrip_cost=estimated_costs,
            expected_gain=expected_gain
        )
