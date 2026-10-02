"""NSE Market Calendar, Trading Hours, and Holiday Schedule (IST)."""

from datetime import datetime, time, date
import pytz

IST_TZ = pytz.timezone("Asia/Kolkata")

# NSE Standard Official Holidays for 2026 (illustrative sample)
NSE_HOLIDAYS_2026 = {
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 3),   # Holi
    date(2026, 3, 20),  # Id-Ul-Fitr
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 14),  # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 5, 27),  # Bakri Id
    date(2026, 8, 15),  # Independence Day
    date(2026, 10, 2),  # Mahatma Gandhi Jayanti
    date(2026, 10, 20), # Dussehra
    date(2026, 11, 8),  # Diwali Laxmi Pujan (Muhurat trading evening only)
    date(2026, 11, 10), # Diwali Balipratipada
    date(2026, 11, 24), # Gurunanak Jayanti
    date(2026, 12, 25), # Christmas
}

class NSECalendar:
    """Validator for NSE trading sessions and active trading windows."""

    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 30)
    TRADE_WINDOW_START = time(9, 30)
    TRADE_WINDOW_END = time(15, 0)
    MIS_SQUAREOFF = time(15, 15)

    @classmethod
    def get_ist_now(cls) -> datetime:
        """Return current timezone-aware timestamp in Asia/Kolkata."""
        return datetime.now(IST_TZ)

    @classmethod
    def is_trading_day(cls, dt: datetime) -> bool:
        """Check if date is a weekday and not an NSE official holiday."""
        local_date = dt.astimezone(IST_TZ).date() if dt.tzinfo else dt.date()
        # 0 = Monday, 6 = Sunday
        if local_date.weekday() >= 5:
            return False
        if local_date in NSE_HOLIDAYS_2026:
            return False
        return True

    @classmethod
    def is_market_open(cls, dt: datetime) -> bool:
        """Return True if within standard 09:15 - 15:30 IST session."""
        if not cls.is_trading_day(dt):
            return False
        local_time = dt.astimezone(IST_TZ).time() if dt.tzinfo else dt.time()
        return cls.MARKET_OPEN <= local_time <= cls.MARKET_CLOSE

    @classmethod
    def is_trade_window_open(cls, dt: datetime) -> bool:
        """Return True if within safe algorithmic trading window (09:30 - 15:00 IST)."""
        if not cls.is_trading_day(dt):
            return False
        local_time = dt.astimezone(IST_TZ).time() if dt.tzinfo else dt.time()
        return cls.TRADE_WINDOW_START <= local_time <= cls.TRADE_WINDOW_END

    @classmethod
    def should_square_off_mis(cls, dt: datetime) -> bool:
        """Return True if time has reached or passed 15:15 IST intraday cut-off."""
        if not cls.is_trading_day(dt):
            return False
        local_time = dt.astimezone(IST_TZ).time() if dt.tzinfo else dt.time()
        return local_time >= cls.MIS_SQUAREOFF
