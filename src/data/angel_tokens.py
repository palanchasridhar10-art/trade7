"""Official Angel One SmartAPI Instrument Token Mapping for Nifty 50 Equities."""

from typing import Dict, Any, Optional

ANGEL_ONE_TOKENS: Dict[str, Dict[str, Any]] = {
    "ADANIENT": {"token": "25", "tradingsymbol": "ADANIENT-EQ", "lotsize": 1},
    "ADANIPORTS": {"token": "15083", "tradingsymbol": "ADANIPORTS-EQ", "lotsize": 1},
    "APOLLOHOSP": {"token": "157", "tradingsymbol": "APOLLOHOSP-EQ", "lotsize": 1},
    "ASIANPAINT": {"token": "236", "tradingsymbol": "ASIANPAINT-EQ", "lotsize": 1},
    "AXISBANK": {"token": "5900", "tradingsymbol": "AXISBANK-EQ", "lotsize": 1},
    "BAJAJ-AUTO": {"token": "16669", "tradingsymbol": "BAJAJ-AUTO-EQ", "lotsize": 1},
    "BAJAJFINSV": {"token": "16675", "tradingsymbol": "BAJAJFINSV-EQ", "lotsize": 1},
    "BAJFINANCE": {"token": "317", "tradingsymbol": "BAJFINANCE-EQ", "lotsize": 1},
    "BHARTIARTL": {"token": "10604", "tradingsymbol": "BHARTIARTL-EQ", "lotsize": 1},
    "BPCL": {"token": "526", "tradingsymbol": "BPCL-EQ", "lotsize": 1},
    "BRITANNIA": {"token": "547", "tradingsymbol": "BRITANNIA-EQ", "lotsize": 1},
    "CIPLA": {"token": "694", "tradingsymbol": "CIPLA-EQ", "lotsize": 1},
    "COALINDIA": {"token": "20374", "tradingsymbol": "COALINDIA-EQ", "lotsize": 1},
    "DABUR": {"token": "772", "tradingsymbol": "DABUR-EQ", "lotsize": 1},
    "DIVISLAB": {"token": "10940", "tradingsymbol": "DIVISLAB-EQ", "lotsize": 1},
    "DRREDDY": {"token": "881", "tradingsymbol": "DRREDDY-EQ", "lotsize": 1},
    "EICHERMOT": {"token": "910", "tradingsymbol": "EICHERMOT-EQ", "lotsize": 1},
    "GRASIM": {"token": "1232", "tradingsymbol": "GRASIM-EQ", "lotsize": 1},
    "HCLTECH": {"token": "7229", "tradingsymbol": "HCLTECH-EQ", "lotsize": 1},
    "HDFCBANK": {"token": "1333", "tradingsymbol": "HDFCBANK-EQ", "lotsize": 1},
    "HDFCLIFE": {"token": "467", "tradingsymbol": "HDFCLIFE-EQ", "lotsize": 1},
    "HINDALCO": {"token": "1363", "tradingsymbol": "HINDALCO-EQ", "lotsize": 1},
    "HINDUNILVR": {"token": "1394", "tradingsymbol": "HINDUNILVR-EQ", "lotsize": 1},
    "ICICIBANK": {"token": "4963", "tradingsymbol": "ICICIBANK-EQ", "lotsize": 1},
    "INDUSINDBK": {"token": "5258", "tradingsymbol": "INDUSINDBK-EQ", "lotsize": 1},
    "INFY": {"token": "1594", "tradingsymbol": "INFY-EQ", "lotsize": 1},
    "ITC": {"token": "1660", "tradingsymbol": "ITC-EQ", "lotsize": 1},
    "JSWSTEEL": {"token": "11723", "tradingsymbol": "JSWSTEEL-EQ", "lotsize": 1},
    "KOTAKBANK": {"token": "1922", "tradingsymbol": "KOTAKBANK-EQ", "lotsize": 1},
    "LT": {"token": "11483", "tradingsymbol": "LT-EQ", "lotsize": 1},
    "LTI": {"token": "17818", "tradingsymbol": "LTM-EQ", "lotsize": 1},
    "M&M": {"token": "2031", "tradingsymbol": "M&M-EQ", "lotsize": 1},
    "MARUTI": {"token": "10999", "tradingsymbol": "MARUTI-EQ", "lotsize": 1},
    "NESTLEIND": {"token": "17963", "tradingsymbol": "NESTLEIND-EQ", "lotsize": 1},
    "NTPC": {"token": "11630", "tradingsymbol": "NTPC-EQ", "lotsize": 1},
    "ONGC": {"token": "2475", "tradingsymbol": "ONGC-EQ", "lotsize": 1},
    "POWERGRID": {"token": "14977", "tradingsymbol": "POWERGRID-EQ", "lotsize": 1},
    "RELIANCE": {"token": "2885", "tradingsymbol": "RELIANCE-EQ", "lotsize": 1},
    "SBILIFE": {"token": "21808", "tradingsymbol": "SBILIFE-EQ", "lotsize": 1},
    "SBIN": {"token": "3045", "tradingsymbol": "SBIN-EQ", "lotsize": 1},
    "SIEMENS": {"token": "3150", "tradingsymbol": "SIEMENS-EQ", "lotsize": 1},
    "SUNPHARMA": {"token": "3351", "tradingsymbol": "SUNPHARMA-EQ", "lotsize": 1},
    "TATAMOTORS": {"token": "759782", "tradingsymbol": "TMCV-EQ", "lotsize": 1},
    "TATASTEEL": {"token": "3499", "tradingsymbol": "TATASTEEL-EQ", "lotsize": 1},
    "TCS": {"token": "11536", "tradingsymbol": "TCS-EQ", "lotsize": 1},
    "TECHM": {"token": "13538", "tradingsymbol": "TECHM-EQ", "lotsize": 1},
    "TITAN": {"token": "3506", "tradingsymbol": "TITAN-EQ", "lotsize": 1},
    "ULTRACEMCO": {"token": "11532", "tradingsymbol": "ULTRACEMCO-EQ", "lotsize": 1},
    "VEDL": {"token": "3063", "tradingsymbol": "VEDL-EQ", "lotsize": 1},
    "WIPRO": {"token": "3787", "tradingsymbol": "WIPRO-EQ", "lotsize": 1},
}

def get_angel_token(symbol: str) -> str:
    """Return Angel One symbol token for order placement and market quotes."""
    sym_clean = symbol.upper().strip().replace("-EQ", "")
    entry = ANGEL_ONE_TOKENS.get(sym_clean, {})
    return entry.get("token", "")

def get_angel_tradingsymbol(symbol: str) -> str:
    """Return Angel One formatted trading symbol (e.g. RELIANCE-EQ, TMCV-EQ)."""
    sym_clean = symbol.upper().strip().replace("-EQ", "")
    entry = ANGEL_ONE_TOKENS.get(sym_clean, {})
    return entry.get("tradingsymbol", f"{sym_clean}-EQ")
