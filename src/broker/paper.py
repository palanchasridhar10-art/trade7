"""Paper Trading Broker with Indian Market Statutory Charges & Slippage Simulation."""

from datetime import datetime
import uuid
from typing import Dict, List, Optional
from src.broker.base import BaseBrokerAdapter
from src.core.constants import OrderSide, OrderStatus, ProductType, ExitReason
from src.core.models import Order, Position, PortfolioState, TradeRecord

class PaperBroker(BaseBrokerAdapter):
    """Simulated paper broker enforcing realistic execution costs and slippage."""

    def __init__(self, initial_capital: float = 1_000_000.0, slippage_pct: float = 0.08):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.peak_capital = initial_capital
        self.slippage_pct = slippage_pct / 100.0
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.completed_trades: List[TradeRecord] = []
        self.daily_realized_pnl = 0.0
        self.connected = False

    def connect(self) -> bool:
        self.connected = True
        return True

    def disconnect(self) -> None:
        self.connected = False

    def calculate_statutory_fees(self, turnover_entry: float, turnover_exit: float, is_intraday: bool = True) -> float:
        """Calculate comprehensive Indian statutory charges."""
        total_turnover = turnover_entry + turnover_exit
        brokerage = min(20.0, turnover_entry * 0.0003) + min(20.0, turnover_exit * 0.0003)
        stt = turnover_exit * 0.00025 if is_intraday else total_turnover * 0.001
        exchange_charges = total_turnover * 0.0000297
        sebi_charges = total_turnover * 0.000001
        stamp_duty = turnover_entry * (0.00003 if is_intraday else 0.00015)
        gst = (brokerage + exchange_charges + sebi_charges) * 0.18
        return brokerage + stt + exchange_charges + sebi_charges + stamp_duty + gst

    def get_portfolio_state(self) -> PortfolioState:
        """Return current snapshot of capital and position state."""
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_equity = self.capital + unrealized
        self.peak_capital = max(self.peak_capital, total_equity)

        # Sector exposure
        sector_exp: Dict[str, float] = {}
        for pos in self.positions.values():
            val = pos.quantity * pos.current_price
            sector_exp[pos.sector] = sector_exp.get(pos.sector, 0.0) + val

        return PortfolioState(
            total_capital=round(total_equity, 2),
            available_cash=round(self.capital, 2),
            utilized_margin=round(sum(p.quantity * p.entry_price for p in self.positions.values()), 2),
            realized_daily_pnl=round(self.daily_realized_pnl, 2),
            unrealized_daily_pnl=round(unrealized, 2),
            weekly_realized_pnl=round(self.daily_realized_pnl, 2),
            peak_capital=round(self.peak_capital, 2),
            open_positions=self.positions,
            sector_exposure=sector_exp,
            trades_count_today=len(self.completed_trades)
        )

    def submit_bracket_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target_price: float,
        sector: str = "GENERAL"
    ) -> Order:
        """Simulate order execution with slippage applied to fill price.
        
        MIS margin requirement: 20% of position value (5x SEBI leverage).
        Duplicate position guard: if symbol already open, skip.
        """
        # Guard: don't open duplicate position in same symbol
        if symbol in self.positions:
            import uuid as _uuid
            now = datetime.now()
            return Order(
                order_id=f"DUP-{symbol}-{now.strftime('%H%M%S')}",
                client_order_id=f"DUP-{symbol}",
                symbol=symbol,
                side=OrderSide(side),
                product_type=ProductType.MIS,
                quantity=0,
                price=entry_price,
                status=OrderStatus.REJECTED,
                created_at=now
            )

        now = datetime.now()
        order_id = str(uuid.uuid4())
        client_id = f"CL-{order_id[:8]}"
        order_side = OrderSide(side)

        # Apply slippage to fill price
        if order_side == OrderSide.BUY:
            fill_price = round(entry_price * (1.0 + self.slippage_pct), 2)
        else:
            fill_price = round(entry_price * (1.0 - self.slippage_pct), 2)

        # MIS intraday margin: 20% of position value (SEBI 5x leverage)
        position_value = fill_price * quantity
        margin_required = position_value * 0.20  # 20% MIS margin

        # If insufficient cash for even the margin, reduce qty to what we can afford
        if margin_required > self.capital and self.capital > 0:
            quantity = max(1, int(self.capital / (fill_price * 0.20)))
            margin_required = fill_price * quantity * 0.20

        order = Order(
            order_id=order_id,
            client_order_id=client_id,
            symbol=symbol,
            side=order_side,
            product_type=ProductType.MIS,
            quantity=quantity,
            price=entry_price,
            status=OrderStatus.FILLED,
            created_at=now,
            filled_at=now,
            average_fill_price=fill_price
        )
        self.orders[order_id] = order

        # Deduct MIS margin from available cash (not full position value)
        self.capital -= margin_required

        # Create active position
        pos_id = str(uuid.uuid4())
        position = Position(
            position_id=pos_id,
            symbol=symbol,
            sector=sector,
            side=order_side,
            product_type=ProductType.MIS,
            quantity=quantity,
            entry_price=fill_price,
            current_price=fill_price,
            stop_loss=stop_loss,
            target_price=target_price,
            trailing_stop=stop_loss,
            opened_at=now,
            last_updated_at=now
        )
        self.positions[symbol] = position
        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders and self.orders[order_id].status != OrderStatus.FILLED:
            self.orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False

    def update_price_tick(self, symbol: str, current_price: float) -> Optional[TradeRecord]:
        """Update market price for a symbol, evaluate stop/target triggers, and close if hit."""
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]
        pos.current_price = current_price
        now = datetime.now()

        # Update unrealized PnL
        if pos.side == OrderSide.BUY:
            pos.unrealized_pnl = (current_price - pos.entry_price) * pos.quantity
        else:
            pos.unrealized_pnl = (pos.entry_price - current_price) * pos.quantity

        exit_reason = None
        exit_price = None

        # Calculate percentage return of position
        pnl_pct = (current_price - pos.entry_price) / pos.entry_price if pos.side == OrderSide.BUY else (pos.entry_price - current_price) / pos.entry_price

        # Automatic Square-Off Triggers:
        # Profit Target: 15% to 20% (or target_price reached)
        # Stop Loss: -5.0% (or stop_loss reached)
        if pos.side == OrderSide.BUY:
            if current_price >= pos.target_price or pnl_pct >= 0.15:
                exit_reason = ExitReason.TARGET
                exit_price = current_price
            elif current_price <= pos.stop_loss or pnl_pct <= -0.05:
                exit_reason = ExitReason.STOP_LOSS
                exit_price = current_price
        else: # SHORT
            if current_price <= pos.target_price or pnl_pct >= 0.15:
                exit_reason = ExitReason.TARGET
                exit_price = current_price
            elif current_price >= pos.stop_loss or pnl_pct <= -0.05:
                exit_reason = ExitReason.STOP_LOSS
                exit_price = current_price

        if exit_reason and exit_price:
            return self._close_position(symbol, exit_price, exit_reason, now)

        return None

    def _close_position(self, symbol: str, raw_exit_price: float, exit_reason: ExitReason, exit_time: datetime) -> TradeRecord:
        pos = self.positions.pop(symbol)

        # Apply slippage on exit
        if pos.side == OrderSide.BUY:
            fill_exit = round(raw_exit_price * (1.0 - self.slippage_pct), 2)
            gross_pnl = (fill_exit - pos.entry_price) * pos.quantity
        else:
            fill_exit = round(raw_exit_price * (1.0 + self.slippage_pct), 2)
            gross_pnl = (pos.entry_price - fill_exit) * pos.quantity

        turnover_in = pos.entry_price * pos.quantity
        turnover_out = fill_exit * pos.quantity
        fees = self.calculate_statutory_fees(turnover_in, turnover_out, is_intraday=True)
        net_pnl = gross_pnl - fees
        slippage_cost = abs(fill_exit - raw_exit_price) * pos.quantity

        risk_amount = abs(pos.entry_price - pos.stop_loss) * pos.quantity
        r_multiple = round(gross_pnl / risk_amount, 2) if risk_amount > 0 else 0.0

        self.capital += net_pnl
        # Refund MIS margin on close (20% of entry value)
        margin_refund = pos.entry_price * pos.quantity * 0.20
        self.capital += margin_refund
        self.daily_realized_pnl += net_pnl

        record = TradeRecord(
            trade_id=str(uuid.uuid4()),
            decision_id=str(uuid.uuid4()),
            symbol=symbol,
            side=pos.side,
            product_type=pos.product_type,
            quantity=pos.quantity,
            entry_price=pos.entry_price,
            exit_price=fill_exit,
            stop_price=pos.stop_loss,
            target_price=pos.target_price,
            exit_reason=exit_reason,
            gross_pnl=round(gross_pnl, 2),
            net_pnl=round(net_pnl, 2),
            fees_and_taxes=round(fees, 2),
            slippage=round(slippage_cost, 2),
            r_multiple=r_multiple,
            kelly_fraction=0.0,
            win_prob_est=0.0,
            opened_at=pos.opened_at,
            closed_at=exit_time
        )
        self.completed_trades.append(record)
        return record

    def square_off_all_mis(self, reason: str = "EOD_SQUAREOFF") -> List[Position]:
        """Close out all active MIS positions immediately."""
        closed = []
        symbols = list(self.positions.keys())
        now = datetime.now()
        for sym in symbols:
            pos = self.positions[sym]
            self._close_position(sym, pos.current_price, ExitReason.EOD_MIS, now)
            closed.append(pos)
        return closed
