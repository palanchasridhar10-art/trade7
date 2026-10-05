"""Angel One SmartAPI Broker Adapter.

Implements BaseBrokerAdapter for Angel One (SmartAPI v2).
Handles authentication with TOTP (pyotp), order placement (MIS), position tracking,
and automated intraday square-off before 15:15 IST.
"""

import os
from datetime import datetime
import logging
from typing import Dict, List, Optional
from src.broker.base import BaseBrokerAdapter
from src.core.constants import OrderSide, OrderStatus, ProductType, ExitReason
from src.core.models import Order, Position, PortfolioState
from src.data.angel_tokens import get_angel_token, get_angel_tradingsymbol

logger = logging.getLogger(__name__)

class AngelOneAdapter(BaseBrokerAdapter):
    """Angel One SmartAPI v2 Adapter for Intraday MIS Equities."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client_code: Optional[str] = None,
        pin: Optional[str] = None,
        totp_secret: Optional[str] = None
    ):
        # API Key is optional - fallback to env var or standard default key
        self.api_key = (api_key or os.getenv("ANGEL_API_KEY", "") or "smartapi_default_key").strip()
        self.client_code = client_code or os.getenv("ANGEL_CLIENT_CODE", "")
        self.pin = pin or os.getenv("ANGEL_PIN", "")
        self.totp_secret = totp_secret or os.getenv("ANGEL_TOTP_SECRET", "")
        self.smart_api = None
        self.auth_token = None
        self.refresh_token = None
        self.feed_token = None
        self.is_connected = False
        self.last_error = None

    def connect(self, otp_or_secret: Optional[str] = None) -> bool:
        """Establish authenticated SmartAPI session using client credentials and TOTP or direct OTP."""
        totp_input = (otp_or_secret or self.totp_secret or "").strip().replace(" ", "")
        
        # API Key is optional - fallback to default if not provided
        if not self.api_key:
            self.api_key = os.getenv("ANGEL_API_KEY", "") or "smartapi_default_key"

        if not (self.client_code and self.pin and totp_input):
            missing = []
            if not self.client_code: missing.append("Client Code")
            if not self.pin: missing.append("MPIN")
            if not totp_input: missing.append("OTP / TOTP")
            self.last_error = f"Missing credentials: {', '.join(missing)} are required."
            logger.warning(self.last_error)
            return False

        try:
            from SmartApi import SmartConnect
            import pyotp

            self.smart_api = SmartConnect(api_key=self.api_key)

            # Check if user entered a 6-digit OTP directly (e.g. 123456) or a Base32 secret key
            if len(totp_input) == 6 and totp_input.isdigit():
                totp_code = totp_input
            else:
                # Generate TOTP from Base32 secret
                try:
                    totp_code = pyotp.TOTP(totp_input).now()
                except Exception as ex:
                    self.last_error = f"Invalid TOTP Secret Key format: {ex}. You can enter your current 6-digit OTP directly."
                    return False

            data = self.smart_api.generateSession(self.client_code, self.pin, totp_code)

            if data.get("status"):
                self.auth_token = data["data"]["jwtToken"]
                self.refresh_token = data["data"]["refreshToken"]
                self.feed_token = self.smart_api.getfeedToken()
                self.is_connected = True
                self.last_error = None
                logger.info(f"Angel One session authenticated successfully for client {self.client_code}.")
                return True
            else:
                msg = data.get("message") or "Authentication failed. Check your Client ID, MPIN, or OTP."
                self.last_error = msg
                logger.error(f"Angel One authentication failed: {msg}")
                return False
        except Exception as e:
            self.last_error = f"Connection error: {str(e)}"
            logger.error(f"Error connecting to Angel One SmartAPI: {e}")
            return False

    def disconnect(self) -> None:
        """Log out and terminate session."""
        if self.smart_api and self.is_connected:
            try:
                self.smart_api.terminateSession(self.client_code)
            except Exception:
                pass
            self.is_connected = False
            logger.info("Angel One session terminated.")

    def get_portfolio_state(self) -> PortfolioState:
        """Fetch current funds, utilized margins, and active open positions."""
        if not self.is_connected or not self.smart_api:
            # Fallback mock/paper state if offline
            return PortfolioState(
                total_capital=1_000_000.0,
                available_cash=1_000_000.0,
                utilized_margin=0.0,
                realized_daily_pnl=0.0,
                unrealized_daily_pnl=0.0,
                weekly_realized_pnl=0.0,
                peak_capital=1_000_000.0
            )

        try:
            # Fetch RMS Limits (Funds)
            rms = self.smart_api.rmsLimit()
            net_capital = float(rms["data"].get("net", 0.0))
            available_cash = float(rms["data"].get("availablecash", 0.0))

            # Fetch Positions
            positions_data = self.smart_api.position()
            open_positions: Dict[str, Position] = {}
            unrealized_pnl = 0.0
            realized_pnl = 0.0

            if positions_data.get("status") and positions_data.get("data"):
                for p in positions_data["data"]:
                    net_qty = int(p.get("netqty", 0))
                    if net_qty != 0:
                        symbol = p.get("tradingsymbol", "")
                        pnl = float(p.get("unrealised", 0.0))
                        unrealized_pnl += pnl
                        open_positions[symbol] = Position(
                            position_id=p.get("symboltoken", symbol),
                            symbol=symbol,
                            sector="EQUITY",
                            side=OrderSide.BUY if net_qty > 0 else OrderSide.SELL,
                            product_type=ProductType.MIS,
                            quantity=abs(net_qty),
                            entry_price=float(p.get("avgprice", 0.0)),
                            current_price=float(p.get("ltp", 0.0)),
                            stop_loss=0.0,
                            target_price=0.0,
                            trailing_stop=0.0,
                            unrealized_pnl=pnl,
                            realized_pnl=float(p.get("realised", 0.0)),
                            opened_at=datetime.now(),
                            last_updated_at=datetime.now()
                        )

            return PortfolioState(
                total_capital=net_capital if net_capital > 0 else available_cash,
                available_cash=available_cash,
                utilized_margin=net_capital - available_cash,
                realized_daily_pnl=realized_pnl,
                unrealized_daily_pnl=unrealized_pnl,
                weekly_realized_pnl=realized_pnl,
                peak_capital=max(net_capital, available_cash),
                open_positions=open_positions
            )
        except Exception as e:
            logger.error(f"Error fetching portfolio state from Angel One: {e}")
            return PortfolioState(
                total_capital=1_000_000.0,
                available_cash=1_000_000.0,
                peak_capital=1_000_000.0
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
        """Submit limit order with client ID tracking on Angel One."""
        now = datetime.now()
        client_order_id = f"ANGEL-{now.strftime('%H%M%S')}-{symbol[:4]}"

        # Resolve official Angel One instrument token and tradingsymbol
        token = get_angel_token(symbol)
        trading_sym = get_angel_tradingsymbol(symbol)
        safe_qty = max(1, int(quantity))
        safe_entry = round(entry_price, 2)
        sq_off = round(abs(target_price - entry_price), 2)
        sl = round(abs(entry_price - stop_loss), 2)

        order_params = {
            "variety": "NORMAL",
            "tradingsymbol": trading_sym,
            "symboltoken": str(token),
            "transactiontype": side.upper(),
            "exchange": "NSE",
            "ordertype": "LIMIT",
            "producttype": "INTRADAY", # MIS
            "duration": "DAY",
            "price": f"{safe_entry:.2f}",
            "squareoff": f"{sq_off:.2f}",
            "stoploss": f"{sl:.2f}",
            "quantity": str(safe_qty)
        }

        logger.info(f"[Angel One] Submitting {side} {safe_qty} units of {trading_sym} (Token: {token}) @ ₹{safe_entry:.2f}")

        if self.is_connected and self.smart_api:
            try:
                response = self.smart_api.placeOrder(order_params)
                broker_order_id = response.get("data", {}).get("orderid", "")
                return Order(
                    order_id=broker_order_id or client_order_id,
                    client_order_id=client_order_id,
                    symbol=symbol,
                    side=OrderSide(side),
                    product_type=ProductType.MIS,
                    quantity=safe_qty,
                    price=safe_entry,
                    status=OrderStatus.SUBMITTED,
                    created_at=now,
                    broker_order_id=broker_order_id
                )
            except Exception as e:
                logger.error(f"Failed to place Angel One order: {e}")

        # Fallback representation
        return Order(
            order_id=client_order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=OrderSide(side),
            product_type=ProductType.MIS,
            quantity=safe_qty,
            price=safe_entry,
            status=OrderStatus.CREATED,
            created_at=now
        )

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open pending order on Angel One."""
        if not self.is_connected or not self.smart_api:
            return False
        try:
            res = self.smart_api.cancelOrder(order_id, "NORMAL")
            return res.get("status", False)
        except Exception as e:
            logger.error(f"Error cancelling Angel One order {order_id}: {e}")
            return False

    def square_off_all_mis(self, reason: str = "EOD_SQUAREOFF") -> List[Position]:
        """Square off all active MIS equity positions prior to 15:15 IST."""
        closed = []
        portfolio = self.get_portfolio_state()
        for sym, pos in portfolio.open_positions.items():
            trading_sym = get_angel_tradingsymbol(sym)
            token = pos.position_id if (pos.position_id and pos.position_id.isdigit()) else get_angel_token(sym)
            logger.info(f"[Angel One] Auto square-off ({reason}) for {trading_sym} (Token: {token}): {pos.quantity} units")
            # Close position by sending opposite market order
            reverse_side = "SELL" if pos.side == OrderSide.BUY else "BUY"
            if self.is_connected and self.smart_api:
                try:
                    self.smart_api.placeOrder({
                        "variety": "NORMAL",
                        "tradingsymbol": trading_sym,
                        "symboltoken": str(token),
                        "transactiontype": reverse_side,
                        "exchange": "NSE",
                        "ordertype": "MARKET",
                        "producttype": "INTRADAY",
                        "duration": "DAY",
                        "price": "0",
                        "quantity": str(pos.quantity)
                    })
                except Exception as ex:
                    logger.error(f"[Angel One] Error squaring off {trading_sym}: {ex}")
            closed.append(pos)
        return closed

    def get_ltp(self, symbol: str) -> Optional[float]:
        """Fetch real-time Last Traded Price directly from Angel One SmartAPI."""
        if not self.is_connected or not self.smart_api:
            return None
        try:
            token = get_angel_token(symbol)
            ts = get_angel_tradingsymbol(symbol)
            res = self.smart_api.ltpData(exchange="NSE", tradingsymbol=ts, symboltoken=token)
            if res and res.get("status") and res.get("data"):
                return float(res["data"].get("ltp", 0.0))
        except Exception as e:
            logger.error(f"[Angel One] Error fetching live LTP for {symbol}: {e}")
        return None
