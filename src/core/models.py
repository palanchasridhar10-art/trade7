"""Pydantic data models enforcing strict schema contracts across all agents and layers."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from src.core.constants import (
    SignalDirection,
    TradingHorizon,
    OrderSide,
    ProductType,
    OrderStatus,
    ExitReason,
    RiskAction
)

class FundamentalSignal(BaseModel):
    """Signal emitted by Agent 1 (Fundamental & Market Context)."""
    agent: str = Field(default="fundamental")
    symbol: str
    exchange: str = Field(default="NSE")
    timestamp: datetime
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    horizon: TradingHorizon = Field(default=TradingHorizon.INTRADAY)
    rationale: List[str] = Field(default_factory=list)
    features: Dict[str, Any] = Field(default_factory=dict)

class TechnicalSignal(BaseModel):
    """Signal emitted by Agent 2 (Technical & Kelly Sizing)."""
    agent: str = Field(default="technical")
    symbol: str
    exchange: str = Field(default="NSE")
    timestamp: datetime
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    horizon: TradingHorizon = Field(default=TradingHorizon.INTRADAY)
    rationale: List[str] = Field(default_factory=list)
    features: Dict[str, Any] = Field(default_factory=dict)
    
    # Actionable trade parameters
    entry: float = Field(gt=0.0)
    stop_loss: float = Field(gt=0.0)
    target: float = Field(gt=0.0)
    win_prob: float = Field(ge=0.0, le=1.0)
    payoff_ratio: float = Field(ge=0.0)
    kelly_fraction: float = Field(ge=0.0, le=1.0)
    suggested_position_value: float = Field(ge=0.0)

class ConsensusResult(BaseModel):
    """Result of Agent 3's Consensus Gate combining Agent 1 & Agent 2."""
    symbol: str
    timestamp: datetime
    consensus_reached: bool
    direction: SignalDirection
    combined_conviction: float = Field(ge=0.0, le=1.0)
    fund_confidence: float = Field(ge=0.0, le=1.0)
    tech_confidence: float = Field(ge=0.0, le=1.0)
    calibrated_win_prob: float = Field(ge=0.0, le=1.0)
    payoff_ratio: float = Field(ge=0.0)
    reason: str

class TradeProposal(BaseModel):
    """Trade proposal constructed prior to deterministic risk checks."""
    proposal_id: str
    symbol: str
    sector: str = "GENERAL"
    side: OrderSide
    product_type: ProductType = ProductType.MIS
    entry_price: float = Field(gt=0.0)
    stop_loss: float = Field(gt=0.0)
    target_price: float = Field(gt=0.0)
    suggested_quantity: int = Field(gt=0)
    suggested_risk_amount: float = Field(gt=0.0)
    kelly_fraction: float
    calibrated_win_prob: float
    payoff_ratio: float
    timestamp: datetime

class RiskVerdict(BaseModel):
    """Decision output from the deterministic RiskEngine."""
    action: RiskAction
    symbol: str
    original_quantity: int
    approved_quantity: int
    approved_risk_amount: float
    reason: str
    rules_triggered: List[str] = Field(default_factory=list)
    estimated_roundtrip_cost: float = 0.0
    expected_gain: float = 0.0

class Order(BaseModel):
    """Broker order object representing execution state."""
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    product_type: ProductType
    quantity: int
    price: float
    trigger_price: Optional[float] = None
    status: OrderStatus = OrderStatus.CREATED
    created_at: datetime
    filled_at: Optional[datetime] = None
    average_fill_price: float = 0.0
    broker_order_id: Optional[str] = None
    reject_reason: Optional[str] = None

class Position(BaseModel):
    """Live active position tracked in portfolio."""
    position_id: str
    symbol: str
    sector: str
    side: OrderSide
    product_type: ProductType
    quantity: int
    entry_price: float
    current_price: float
    stop_loss: float
    target_price: float
    trailing_stop: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    opened_at: datetime
    last_updated_at: datetime

class PortfolioState(BaseModel):
    """Current snapshot of portfolio capital and active exposure."""
    total_capital: float
    available_cash: float
    utilized_margin: float = 0.0
    realized_daily_pnl: float = 0.0
    unrealized_daily_pnl: float = 0.0
    weekly_realized_pnl: float = 0.0
    peak_capital: float
    open_positions: Dict[str, Position] = Field(default_factory=dict)
    sector_exposure: Dict[str, float] = Field(default_factory=dict)
    trades_count_today: int = 0
    is_kill_switch_active: bool = False
    kill_switch_reason: Optional[str] = None

class TradeRecord(BaseModel):
    """Persistent episodic journal entry for completed trade."""
    trade_id: str
    decision_id: str
    symbol: str
    side: OrderSide
    product_type: ProductType
    quantity: int
    entry_price: float
    exit_price: float
    stop_price: float
    target_price: float
    exit_reason: ExitReason
    gross_pnl: float
    net_pnl: float
    fees_and_taxes: float
    slippage: float
    r_multiple: float
    kelly_fraction: float
    win_prob_est: float
    opened_at: datetime
    closed_at: datetime
