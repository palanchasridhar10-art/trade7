"""Abstract Broker Adapter Interface for Indian Markets."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
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
        target_price: float
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
