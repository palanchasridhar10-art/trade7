"""System-wide constants and enumerations for the Autonomous 3-Agent Trading System."""

from enum import Enum

class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"

class TradingHorizon(str, Enum):
    INTRADAY = "intraday"
    SWING = "swing"
    POSITIONAL = "positional"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class ProductType(str, Enum):
    MIS = "MIS"   # Margin Intraday Square-off
    CNC = "CNC"   # Cash and Carry (Delivery)
    NRML = "NRML" # Normal (F&O positional)

class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    SL_LIMIT = "SL_LIMIT"
    SL_MARKET = "SL_MARKET"

class OrderStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"

class ExitReason(str, Enum):
    TARGET = "TARGET"
    STOP_LOSS = "STOP_LOSS"
    TRAILING_STOP = "TRAILING_STOP"
    EOD_MIS = "EOD_MIS"
    KILL_SWITCH = "KILL_SWITCH"
    MANUAL = "MANUAL"

class MarketRegime(str, Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"

class RiskAction(str, Enum):
    APPROVED = "APPROVED"
    DOWNSIZED = "DOWNSIZED"
    VETOED = "VETOED"
