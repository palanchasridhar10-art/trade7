"""Market data abstractions, quote structures, and hygiene validators."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class Bar(BaseModel):
    """OHLCV Bar representation."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None

class Quote(BaseModel):
    """Real-time market depth / price quote."""
    symbol: str
    timestamp: datetime
    last_price: float
    bid_price: float
    ask_price: float
    volume: int
    open_interest: Optional[int] = None
    average_daily_volume: int = 1_000_000

class MacroContext(BaseModel):
    """Macroeconomic and Indian market-wide financial condition metrics."""
    timestamp: datetime
    nifty50_close: float
    nifty50_1w_return: float
    nifty50_1m_return: float
    india_vix: float
    advance_decline_ratio: float
    fii_net_flow_5d_cr: float
    dii_net_flow_5d_cr: float
    crude_oil_brent: float
    usd_inr: float

    # Indian Stock Market Financial Condition Indicators
    gsec_10y_yield: float = 6.92                    # 10-Year Indian Sovereign Benchmark Bond Yield (%)
    repo_rate: float = 6.50                         # RBI Benchmark Repo Rate (%)
    cpi_inflation: float = 4.60                     # India Retail CPI Inflation Rate (%)
    manufacturing_pmi: float = 58.4                 # India Manufacturing PMI (>50 = Expansionary)
    banking_system_liquidity_cr: float = 45000.0   # RBI Net Banking Liquidity Surplus/Deficit (₹ Cr)
    forex_reserves_usd_bn: float = 692.0            # India Foreign Exchange Reserves ($ Billion)
    nifty_pe: float = 22.4                          # Nifty 50 Trailing PE Ratio
    nifty_pe_5y_avg: float = 21.8                   # Historical 5-Year Average PE
    gst_collection_cr: float = 187000.0             # Monthly GST Collection Velocity (₹ Cr)

class CompanyFundamentals(BaseModel):
    """Fundamental and corporate metrics for a single stock."""
    symbol: str
    sector: str
    pe_ratio: float
    sector_pe: float
    pb_ratio: float
    roe_percent: float
    roce_percent: float
    debt_to_equity: float
    revenue_growth_yoy: float
    pat_growth_yoy: float
    promoter_holding_percent: float
    promoter_pledge_percent: float
    is_results_due_in_24h: bool = False
    is_fo_ban: bool = False
    is_asm_gsm: bool = False

class DataFeedQualityValidator:
    """Hygiene checks to prevent trading on stale or corrupted data."""

    @staticmethod
    def is_stale(quote_time: datetime, current_time: datetime, max_latency_seconds: int = 30) -> bool:
        """Flag data if delayed beyond acceptable threshold."""
        delta = abs((current_time - quote_time).total_seconds())
        return delta > max_latency_seconds

    @staticmethod
    def validate_bar(bar: Bar) -> bool:
        """Validate logical OHLC relationship."""
        if bar.high < bar.low:
            return False
        if not (bar.low <= bar.open <= bar.high):
            return False
        if not (bar.low <= bar.close <= bar.high):
            return False
        if bar.volume < 0:
            return False
        return True
