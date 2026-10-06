"""Abstract Broker Adapter Interface for Indian Markets."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from src.core.models import Order, Position, PortfolioState

class BaseBrokerAdapter(ABC):
    """Abstract interface defining required broker interaction methods."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish authenticated broker session."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Terminate broker session."""
        pass

    @abstractmethod
    def get_portfolio_state(self) -> PortfolioState:
        """Retrieve real-time capital, margins, and position summary."""
        pass

    @abstractmethod
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
        """Submit main entry order with paired SL and target brackets."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open pending order."""
        pass

    @abstractmethod
    def square_off_all_mis(self, reason: str = "EOD_SQUAREOFF") -> List[Position]:
        """Close out all intraday MIS positions at market price."""
        pass

    @abstractmethod
    def get_ltp(self, symbol: str) -> Optional[float]:
        """Fetch real-time Last Traded Price (LTP) directly from the broker."""
        pass

    def get_market_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed real-time market quote (LTP, OHLC, volume) from the broker."""
        ltp = self.get_ltp(symbol)
        if ltp is not None:
            return {"symbol": symbol, "ltp": ltp, "last_price": ltp}
        return None

    def get_all_ltp(self, symbols: List[str]) -> Dict[str, float]:
        """Fetch real-time LTPs for multiple symbols from the broker."""
        prices: Dict[str, float] = {}
        for sym in symbols:
            px = self.get_ltp(sym)
            if px is not None and px > 0:
                prices[sym] = px
        return prices
