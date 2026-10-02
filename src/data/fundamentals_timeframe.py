"""Multi-Timeframe Fundamental Data for Nifty 50 Companies.

Three temporal layers per company:
  - DAILY   : Price action, volume, FII/DII flow, news sentiment, intraday momentum
  - MONTHLY  : Quarterly earnings trend, sector rotation, institutional positioning
  - YEARLY   : Valuation multiples, revenue/PAT growth CAGR, governance, balance sheet

Each layer produces an independent score (0-100) that feeds Agent 1.
"""

from typing import Dict, Any

# ─────────────────────────────────────────────────────────────────────────────
#  DAILY FUNDAMENTAL DATA
#  Updated every trading session. Captures:
#   - % change today vs yesterday
#   - Volume vs 20-DMA ratio
#   - FII/DII net buy-sell today (₹ Cr)
#   - News sentiment score [-1 = very bearish, +1 = very bullish]
#   - Delivery volume %  (higher = conviction; < 30% = speculative)
#   - Put/Call ratio    (< 0.8 = bullish, > 1.2 = bearish)
#   - Intraday high/low range % (volatility)
# ─────────────────────────────────────────────────────────────────────────────
DAILY_DATA: Dict[str, Dict[str, Any]] = {
    "RELIANCE":   {"pct_change": 1.42,  "vol_ratio": 1.60, "fii_net_cr": 180.0,  "dii_net_cr": 90.0,  "news_sentiment": 0.55, "delivery_pct": 62.0, "put_call_ratio": 0.72, "hl_range_pct": 1.8},
    "ONGC":       {"pct_change": 2.10,  "vol_ratio": 1.85, "fii_net_cr": 120.0,  "dii_net_cr": 65.0,  "news_sentiment": 0.65, "delivery_pct": 58.0, "put_call_ratio": 0.68, "hl_range_pct": 2.1},
    "BPCL":       {"pct_change": 1.85,  "vol_ratio": 1.70, "fii_net_cr": 95.0,   "dii_net_cr": 55.0,  "news_sentiment": 0.60, "delivery_pct": 55.0, "put_call_ratio": 0.74, "hl_range_pct": 1.9},
    "COALINDIA":  {"pct_change": 2.50,  "vol_ratio": 1.95, "fii_net_cr": 210.0,  "dii_net_cr": 105.0, "news_sentiment": 0.70, "delivery_pct": 64.0, "put_call_ratio": 0.65, "hl_range_pct": 2.3},
    "POWERGRID":  {"pct_change": 0.30,  "vol_ratio": 1.10, "fii_net_cr": 20.0,   "dii_net_cr": 40.0,  "news_sentiment": 0.10, "delivery_pct": 48.0, "put_call_ratio": 0.92, "hl_range_pct": 0.8},
    "NTPC":       {"pct_change": 1.60,  "vol_ratio": 1.55, "fii_net_cr": 140.0,  "dii_net_cr": 70.0,  "news_sentiment": 0.50, "delivery_pct": 57.0, "put_call_ratio": 0.70, "hl_range_pct": 1.7},
    "HDFCBANK":   {"pct_change": 0.85,  "vol_ratio": 1.45, "fii_net_cr": 320.0,  "dii_net_cr": 150.0, "news_sentiment": 0.45, "delivery_pct": 68.0, "put_call_ratio": 0.80, "hl_range_pct": 1.2},
    "ICICIBANK":  {"pct_change": 0.95,  "vol_ratio": 1.50, "fii_net_cr": 280.0,  "dii_net_cr": 130.0, "news_sentiment": 0.50, "delivery_pct": 65.0, "put_call_ratio": 0.78, "hl_range_pct": 1.3},
    "SBIN":       {"pct_change": 1.75,  "vol_ratio": 1.70, "fii_net_cr": 195.0,  "dii_net_cr": 85.0,  "news_sentiment": 0.58, "delivery_pct": 60.0, "put_call_ratio": 0.72, "hl_range_pct": 1.9},
    "AXISBANK":   {"pct_change": 0.60,  "vol_ratio": 1.35, "fii_net_cr": 110.0,  "dii_net_cr": 60.0,  "news_sentiment": 0.35, "delivery_pct": 55.0, "put_call_ratio": 0.86, "hl_range_pct": 1.1},
    "KOTAKBANK":  {"pct_change": -0.45, "vol_ratio": 1.08, "fii_net_cr": -50.0,  "dii_net_cr": 20.0,  "news_sentiment":-0.20, "delivery_pct": 50.0, "put_call_ratio": 1.05, "hl_range_pct": 0.9},
    "INDUSINDBK": {"pct_change": 0.40,  "vol_ratio": 1.15, "fii_net_cr": 35.0,   "dii_net_cr": 25.0,  "news_sentiment": 0.15, "delivery_pct": 48.0, "put_call_ratio": 0.92, "hl_range_pct": 1.0},
    "BAJFINANCE": {"pct_change": -0.85, "vol_ratio": 1.20, "fii_net_cr": -80.0,  "dii_net_cr": 10.0,  "news_sentiment":-0.35, "delivery_pct": 45.0, "put_call_ratio": 1.15, "hl_range_pct": 1.1},
    "BAJAJFINSV": {"pct_change": 0.20,  "vol_ratio": 1.10, "fii_net_cr": 15.0,   "dii_net_cr": 20.0,  "news_sentiment": 0.10, "delivery_pct": 46.0, "put_call_ratio": 0.98, "hl_range_pct": 0.9},
    "TCS":        {"pct_change": -0.60, "vol_ratio": 0.88, "fii_net_cr": -120.0, "dii_net_cr": -20.0, "news_sentiment":-0.25, "delivery_pct": 52.0, "put_call_ratio": 1.10, "hl_range_pct": 0.8},
    "INFY":       {"pct_change": -0.30, "vol_ratio": 0.92, "fii_net_cr": -45.0,  "dii_net_cr": 5.0,   "news_sentiment":-0.15, "delivery_pct": 54.0, "put_call_ratio": 0.95, "hl_range_pct": 0.7},
    "WIPRO":      {"pct_change": 1.10,  "vol_ratio": 1.30, "fii_net_cr": 55.0,   "dii_net_cr": 30.0,  "news_sentiment": 0.40, "delivery_pct": 55.0, "put_call_ratio": 0.82, "hl_range_pct": 1.2},
    "HCLTECH":    {"pct_change": 1.20,  "vol_ratio": 1.40, "fii_net_cr": 75.0,   "dii_net_cr": 40.0,  "news_sentiment": 0.45, "delivery_pct": 58.0, "put_call_ratio": 0.80, "hl_range_pct": 1.3},
    "TECHM":      {"pct_change": 0.90,  "vol_ratio": 1.32, "fii_net_cr": 50.0,   "dii_net_cr": 28.0,  "news_sentiment": 0.38, "delivery_pct": 54.0, "put_call_ratio": 0.84, "hl_range_pct": 1.1},
    "LTI":        {"pct_change": 0.80,  "vol_ratio": 1.25, "fii_net_cr": 40.0,   "dii_net_cr": 22.0,  "news_sentiment": 0.32, "delivery_pct": 52.0, "put_call_ratio": 0.85, "hl_range_pct": 1.0},
    "HINDUNILVR": {"pct_change": -0.50, "vol_ratio": 1.15, "fii_net_cr": -40.0,  "dii_net_cr": 15.0,  "news_sentiment":-0.20, "delivery_pct": 60.0, "put_call_ratio": 1.08, "hl_range_pct": 0.8},
    "ITC":        {"pct_change": 1.80,  "vol_ratio": 1.72, "fii_net_cr": 180.0,  "dii_net_cr": 90.0,  "news_sentiment": 0.62, "delivery_pct": 63.0, "put_call_ratio": 0.70, "hl_range_pct": 1.9},
    "NESTLEIND":  {"pct_change": -0.20, "vol_ratio": 0.92, "fii_net_cr": -10.0,  "dii_net_cr": 8.0,   "news_sentiment":-0.08, "delivery_pct": 70.0, "put_call_ratio": 0.98, "hl_range_pct": 0.5},
    "BRITANNIA":  {"pct_change": 0.50,  "vol_ratio": 1.05, "fii_net_cr": 22.0,   "dii_net_cr": 15.0,  "news_sentiment": 0.20, "delivery_pct": 65.0, "put_call_ratio": 0.92, "hl_range_pct": 0.7},
    "DABUR":      {"pct_change": 0.60,  "vol_ratio": 1.20, "fii_net_cr": 28.0,   "dii_net_cr": 18.0,  "news_sentiment": 0.22, "delivery_pct": 60.0, "put_call_ratio": 0.90, "hl_range_pct": 0.8},
    "SUNPHARMA":  {"pct_change": 1.10,  "vol_ratio": 1.38, "fii_net_cr": 65.0,   "dii_net_cr": 35.0,  "news_sentiment": 0.42, "delivery_pct": 58.0, "put_call_ratio": 0.82, "hl_range_pct": 1.2},
    "DRREDDY":    {"pct_change": 0.90,  "vol_ratio": 1.28, "fii_net_cr": 48.0,   "dii_net_cr": 28.0,  "news_sentiment": 0.35, "delivery_pct": 55.0, "put_call_ratio": 0.85, "hl_range_pct": 1.0},
    "CIPLA":      {"pct_change": 0.85,  "vol_ratio": 1.30, "fii_net_cr": 42.0,   "dii_net_cr": 25.0,  "news_sentiment": 0.33, "delivery_pct": 54.0, "put_call_ratio": 0.86, "hl_range_pct": 1.0},
    "DIVISLAB":   {"pct_change": -0.40, "vol_ratio": 1.08, "fii_net_cr": -15.0,  "dii_net_cr": 8.0,   "news_sentiment":-0.15, "delivery_pct": 52.0, "put_call_ratio": 1.02, "hl_range_pct": 0.8},
    "MARUTI":     {"pct_change": 0.75,  "vol_ratio": 1.25, "fii_net_cr": 52.0,   "dii_net_cr": 30.0,  "news_sentiment": 0.30, "delivery_pct": 55.0, "put_call_ratio": 0.87, "hl_range_pct": 1.0},
    "TATAMOTORS": {"pct_change": 2.80,  "vol_ratio": 2.10, "fii_net_cr": 320.0,  "dii_net_cr": 140.0, "news_sentiment": 0.75, "delivery_pct": 62.0, "put_call_ratio": 0.62, "hl_range_pct": 2.8},
    "M&M":        {"pct_change": 0.95,  "vol_ratio": 1.35, "fii_net_cr": 60.0,   "dii_net_cr": 32.0,  "news_sentiment": 0.38, "delivery_pct": 56.0, "put_call_ratio": 0.84, "hl_range_pct": 1.1},
    "BAJAJ-AUTO": {"pct_change": 0.80,  "vol_ratio": 1.28, "fii_net_cr": 45.0,   "dii_net_cr": 25.0,  "news_sentiment": 0.32, "delivery_pct": 55.0, "put_call_ratio": 0.86, "hl_range_pct": 1.0},
    "EICHERMOT":  {"pct_change": 0.70,  "vol_ratio": 1.22, "fii_net_cr": 38.0,   "dii_net_cr": 22.0,  "news_sentiment": 0.28, "delivery_pct": 54.0, "put_call_ratio": 0.88, "hl_range_pct": 0.9},
    "TATASTEEL":  {"pct_change": 2.20,  "vol_ratio": 1.90, "fii_net_cr": 250.0,  "dii_net_cr": 110.0, "news_sentiment": 0.68, "delivery_pct": 60.0, "put_call_ratio": 0.66, "hl_range_pct": 2.3},
    "JSWSTEEL":   {"pct_change": 1.65,  "vol_ratio": 1.62, "fii_net_cr": 120.0,  "dii_net_cr": 65.0,  "news_sentiment": 0.55, "delivery_pct": 57.0, "put_call_ratio": 0.74, "hl_range_pct": 1.8},
    "HINDALCO":   {"pct_change": 1.40,  "vol_ratio": 1.52, "fii_net_cr": 90.0,   "dii_net_cr": 50.0,  "news_sentiment": 0.48, "delivery_pct": 55.0, "put_call_ratio": 0.78, "hl_range_pct": 1.6},
    "VEDL":       {"pct_change": 0.85,  "vol_ratio": 1.05, "fii_net_cr": 30.0,   "dii_net_cr": 18.0,  "news_sentiment": 0.22, "delivery_pct": 48.0, "put_call_ratio": 0.95, "hl_range_pct": 1.2},
    "LT":         {"pct_change": 0.90,  "vol_ratio": 1.32, "fii_net_cr": 55.0,   "dii_net_cr": 30.0,  "news_sentiment": 0.35, "delivery_pct": 56.0, "put_call_ratio": 0.84, "hl_range_pct": 1.1},
    "ADANIPORTS": {"pct_change": 0.75,  "vol_ratio": 1.28, "fii_net_cr": 42.0,   "dii_net_cr": 22.0,  "news_sentiment": 0.28, "delivery_pct": 52.0, "put_call_ratio": 0.88, "hl_range_pct": 1.0},
    "ADANIENT":   {"pct_change": -0.55, "vol_ratio": 1.12, "fii_net_cr": -35.0,  "dii_net_cr": 10.0,  "news_sentiment":-0.22, "delivery_pct": 45.0, "put_call_ratio": 1.08, "hl_range_pct": 1.2},
    "SIEMENS":    {"pct_change": 0.80,  "vol_ratio": 1.25, "fii_net_cr": 38.0,   "dii_net_cr": 20.0,  "news_sentiment": 0.30, "delivery_pct": 60.0, "put_call_ratio": 0.88, "hl_range_pct": 0.9},
    "APOLLOHOSP": {"pct_change": 0.95,  "vol_ratio": 1.30, "fii_net_cr": 48.0,   "dii_net_cr": 26.0,  "news_sentiment": 0.36, "delivery_pct": 58.0, "put_call_ratio": 0.84, "hl_range_pct": 1.1},
    "SBILIFE":    {"pct_change": 0.70,  "vol_ratio": 1.22, "fii_net_cr": 35.0,   "dii_net_cr": 18.0,  "news_sentiment": 0.26, "delivery_pct": 55.0, "put_call_ratio": 0.89, "hl_range_pct": 0.9},
    "HDFCLIFE":   {"pct_change": 0.60,  "vol_ratio": 1.18, "fii_net_cr": 28.0,   "dii_net_cr": 15.0,  "news_sentiment": 0.22, "delivery_pct": 54.0, "put_call_ratio": 0.90, "hl_range_pct": 0.8},
    "BHARTIARTL": {"pct_change": 1.30,  "vol_ratio": 1.52, "fii_net_cr": 85.0,   "dii_net_cr": 42.0,  "news_sentiment": 0.48, "delivery_pct": 60.0, "put_call_ratio": 0.76, "hl_range_pct": 1.5},
    "ASIANPAINT": {"pct_change": -0.60, "vol_ratio": 1.18, "fii_net_cr": -42.0,  "dii_net_cr": 12.0,  "news_sentiment":-0.25, "delivery_pct": 62.0, "put_call_ratio": 1.06, "hl_range_pct": 0.9},
    "TITAN":      {"pct_change": 0.85,  "vol_ratio": 1.32, "fii_net_cr": 45.0,   "dii_net_cr": 25.0,  "news_sentiment": 0.34, "delivery_pct": 58.0, "put_call_ratio": 0.85, "hl_range_pct": 1.1},
    "ULTRACEMCO": {"pct_change": 0.65,  "vol_ratio": 1.20, "fii_net_cr": 30.0,   "dii_net_cr": 18.0,  "news_sentiment": 0.24, "delivery_pct": 55.0, "put_call_ratio": 0.90, "hl_range_pct": 0.9},
    "GRASIM":     {"pct_change": 0.70,  "vol_ratio": 1.22, "fii_net_cr": 32.0,   "dii_net_cr": 19.0,  "news_sentiment": 0.26, "delivery_pct": 54.0, "put_call_ratio": 0.89, "hl_range_pct": 0.9},
}

# ─────────────────────────────────────────────────────────────────────────────
#  MONTHLY FUNDAMENTAL DATA
#  Updated every month / quarterly earnings cycle. Captures:
#   - Quarterly revenue growth QoQ %
#   - Quarterly PAT growth QoQ %
#   - EPS trend (3-quarter direction: up/flat/down)
#   - FII 1-month net flow (₹ Cr)
#   - Sector 1-month rotation score (0-100)
#   - Analyst upgrades/downgrades this month
#   - Management guidance: positive / neutral / negative
# ─────────────────────────────────────────────────────────────────────────────
MONTHLY_DATA: Dict[str, Dict[str, Any]] = {
    "RELIANCE":   {"q_rev_growth": 8.5,  "q_pat_growth": 12.0, "eps_trend": "up",   "fii_1m_cr": 1800.0,  "sector_rotation": 72, "analyst_upgrades": 4, "analyst_downgrades": 1, "mgmt_guidance": "positive"},
    "ONGC":       {"q_rev_growth": 5.2,  "q_pat_growth": 18.5, "eps_trend": "up",   "fii_1m_cr": 1200.0,  "sector_rotation": 68, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "BPCL":       {"q_rev_growth": 6.0,  "q_pat_growth": 40.0, "eps_trend": "up",   "fii_1m_cr": 950.0,   "sector_rotation": 70, "analyst_upgrades": 3, "analyst_downgrades": 1, "mgmt_guidance": "positive"},
    "COALINDIA":  {"q_rev_growth": 4.5,  "q_pat_growth": 10.0, "eps_trend": "up",   "fii_1m_cr": 2100.0,  "sector_rotation": 74, "analyst_upgrades": 5, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "POWERGRID":  {"q_rev_growth": 7.0,  "q_pat_growth": 9.0,  "eps_trend": "flat", "fii_1m_cr": 200.0,   "sector_rotation": 52, "analyst_upgrades": 1, "analyst_downgrades": 2, "mgmt_guidance": "neutral"},
    "NTPC":       {"q_rev_growth": 9.2,  "q_pat_growth": 14.0, "eps_trend": "up",   "fii_1m_cr": 1400.0,  "sector_rotation": 65, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "HDFCBANK":   {"q_rev_growth": 14.0, "q_pat_growth": 17.0, "eps_trend": "up",   "fii_1m_cr": 3200.0,  "sector_rotation": 68, "analyst_upgrades": 4, "analyst_downgrades": 1, "mgmt_guidance": "positive"},
    "ICICIBANK":  {"q_rev_growth": 16.0, "q_pat_growth": 28.0, "eps_trend": "up",   "fii_1m_cr": 2800.0,  "sector_rotation": 70, "analyst_upgrades": 5, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "SBIN":       {"q_rev_growth": 11.0, "q_pat_growth": 22.0, "eps_trend": "up",   "fii_1m_cr": 1950.0,  "sector_rotation": 66, "analyst_upgrades": 4, "analyst_downgrades": 1, "mgmt_guidance": "positive"},
    "AXISBANK":   {"q_rev_growth": 13.0, "q_pat_growth": 19.0, "eps_trend": "up",   "fii_1m_cr": 1100.0,  "sector_rotation": 62, "analyst_upgrades": 3, "analyst_downgrades": 1, "mgmt_guidance": "positive"},
    "KOTAKBANK":  {"q_rev_growth": 15.0, "q_pat_growth": 12.0, "eps_trend": "flat", "fii_1m_cr": -500.0,  "sector_rotation": 55, "analyst_upgrades": 1, "analyst_downgrades": 3, "mgmt_guidance": "neutral"},
    "INDUSINDBK": {"q_rev_growth": 14.5, "q_pat_growth": 16.0, "eps_trend": "up",   "fii_1m_cr": 350.0,   "sector_rotation": 58, "analyst_upgrades": 2, "analyst_downgrades": 1, "mgmt_guidance": "neutral"},
    "BAJFINANCE": {"q_rev_growth": 25.0, "q_pat_growth": 22.0, "eps_trend": "flat", "fii_1m_cr": -800.0,  "sector_rotation": 50, "analyst_upgrades": 1, "analyst_downgrades": 3, "mgmt_guidance": "neutral"},
    "BAJAJFINSV": {"q_rev_growth": 20.0, "q_pat_growth": 18.0, "eps_trend": "up",   "fii_1m_cr": 150.0,   "sector_rotation": 56, "analyst_upgrades": 2, "analyst_downgrades": 1, "mgmt_guidance": "neutral"},
    "TCS":        {"q_rev_growth": 7.5,  "q_pat_growth": 9.5,  "eps_trend": "flat", "fii_1m_cr": -1200.0, "sector_rotation": 45, "analyst_upgrades": 1, "analyst_downgrades": 3, "mgmt_guidance": "neutral"},
    "INFY":       {"q_rev_growth": 6.5,  "q_pat_growth": 8.0,  "eps_trend": "flat", "fii_1m_cr": -450.0,  "sector_rotation": 44, "analyst_upgrades": 1, "analyst_downgrades": 2, "mgmt_guidance": "neutral"},
    "WIPRO":      {"q_rev_growth": 4.0,  "q_pat_growth": 6.0,  "eps_trend": "up",   "fii_1m_cr": 550.0,   "sector_rotation": 52, "analyst_upgrades": 2, "analyst_downgrades": 1, "mgmt_guidance": "positive"},
    "HCLTECH":    {"q_rev_growth": 9.0,  "q_pat_growth": 11.0, "eps_trend": "up",   "fii_1m_cr": 750.0,   "sector_rotation": 58, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "TECHM":      {"q_rev_growth": 5.5,  "q_pat_growth": 12.5, "eps_trend": "up",   "fii_1m_cr": 500.0,   "sector_rotation": 54, "analyst_upgrades": 2, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "LTI":        {"q_rev_growth": 12.0, "q_pat_growth": 15.0, "eps_trend": "up",   "fii_1m_cr": 400.0,   "sector_rotation": 60, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "HINDUNILVR": {"q_rev_growth": 5.0,  "q_pat_growth": 8.0,  "eps_trend": "flat", "fii_1m_cr": -400.0,  "sector_rotation": 42, "analyst_upgrades": 1, "analyst_downgrades": 2, "mgmt_guidance": "neutral"},
    "ITC":        {"q_rev_growth": 8.0,  "q_pat_growth": 12.0, "eps_trend": "up",   "fii_1m_cr": 1800.0,  "sector_rotation": 70, "analyst_upgrades": 5, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "NESTLEIND":  {"q_rev_growth": 10.0, "q_pat_growth": 14.0, "eps_trend": "flat", "fii_1m_cr": -100.0,  "sector_rotation": 48, "analyst_upgrades": 1, "analyst_downgrades": 1, "mgmt_guidance": "neutral"},
    "BRITANNIA":  {"q_rev_growth": 6.5,  "q_pat_growth": 10.0, "eps_trend": "up",   "fii_1m_cr": 220.0,   "sector_rotation": 54, "analyst_upgrades": 2, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "DABUR":      {"q_rev_growth": 7.0,  "q_pat_growth": 9.0,  "eps_trend": "up",   "fii_1m_cr": 280.0,   "sector_rotation": 55, "analyst_upgrades": 2, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "SUNPHARMA":  {"q_rev_growth": 10.5, "q_pat_growth": 20.0, "eps_trend": "up",   "fii_1m_cr": 650.0,   "sector_rotation": 62, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "DRREDDY":    {"q_rev_growth": 12.0, "q_pat_growth": 18.0, "eps_trend": "up",   "fii_1m_cr": 480.0,   "sector_rotation": 60, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "CIPLA":      {"q_rev_growth": 9.0,  "q_pat_growth": 14.0, "eps_trend": "up",   "fii_1m_cr": 420.0,   "sector_rotation": 58, "analyst_upgrades": 2, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "DIVISLAB":   {"q_rev_growth": 8.5,  "q_pat_growth": 12.0, "eps_trend": "flat", "fii_1m_cr": -150.0,  "sector_rotation": 50, "analyst_upgrades": 1, "analyst_downgrades": 1, "mgmt_guidance": "neutral"},
    "MARUTI":     {"q_rev_growth": 15.0, "q_pat_growth": 30.0, "eps_trend": "up",   "fii_1m_cr": 520.0,   "sector_rotation": 64, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "TATAMOTORS": {"q_rev_growth": 18.0, "q_pat_growth": 120.0,"eps_trend": "up",   "fii_1m_cr": 3200.0,  "sector_rotation": 78, "analyst_upgrades": 6, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "M&M":        {"q_rev_growth": 12.0, "q_pat_growth": 20.0, "eps_trend": "up",   "fii_1m_cr": 600.0,   "sector_rotation": 64, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "BAJAJ-AUTO": {"q_rev_growth": 10.0, "q_pat_growth": 22.0, "eps_trend": "up",   "fii_1m_cr": 450.0,   "sector_rotation": 62, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "EICHERMOT":  {"q_rev_growth": 11.0, "q_pat_growth": 18.0, "eps_trend": "up",   "fii_1m_cr": 380.0,   "sector_rotation": 60, "analyst_upgrades": 2, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "TATASTEEL":  {"q_rev_growth": 5.5,  "q_pat_growth": 8.0,  "eps_trend": "up",   "fii_1m_cr": 2500.0,  "sector_rotation": 72, "analyst_upgrades": 4, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "JSWSTEEL":   {"q_rev_growth": 7.0,  "q_pat_growth": 10.0, "eps_trend": "up",   "fii_1m_cr": 1200.0,  "sector_rotation": 68, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "HINDALCO":   {"q_rev_growth": 6.0,  "q_pat_growth": 8.0,  "eps_trend": "up",   "fii_1m_cr": 900.0,   "sector_rotation": 65, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "VEDL":       {"q_rev_growth": 8.0,  "q_pat_growth": 15.0, "eps_trend": "flat", "fii_1m_cr": 300.0,   "sector_rotation": 58, "analyst_upgrades": 2, "analyst_downgrades": 1, "mgmt_guidance": "neutral"},
    "LT":         {"q_rev_growth": 14.0, "q_pat_growth": 16.0, "eps_trend": "up",   "fii_1m_cr": 550.0,   "sector_rotation": 66, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "ADANIPORTS": {"q_rev_growth": 12.0, "q_pat_growth": 18.0, "eps_trend": "up",   "fii_1m_cr": 420.0,   "sector_rotation": 62, "analyst_upgrades": 2, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "ADANIENT":   {"q_rev_growth": 22.0, "q_pat_growth": 25.0, "eps_trend": "flat", "fii_1m_cr": -350.0,  "sector_rotation": 48, "analyst_upgrades": 1, "analyst_downgrades": 3, "mgmt_guidance": "neutral"},
    "SIEMENS":    {"q_rev_growth": 16.0, "q_pat_growth": 20.0, "eps_trend": "up",   "fii_1m_cr": 380.0,   "sector_rotation": 64, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "APOLLOHOSP": {"q_rev_growth": 18.0, "q_pat_growth": 40.0, "eps_trend": "up",   "fii_1m_cr": 480.0,   "sector_rotation": 66, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "SBILIFE":    {"q_rev_growth": 12.0, "q_pat_growth": 15.0, "eps_trend": "up",   "fii_1m_cr": 350.0,   "sector_rotation": 60, "analyst_upgrades": 2, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "HDFCLIFE":   {"q_rev_growth": 10.0, "q_pat_growth": 12.0, "eps_trend": "up",   "fii_1m_cr": 280.0,   "sector_rotation": 58, "analyst_upgrades": 2, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "BHARTIARTL": {"q_rev_growth": 12.0, "q_pat_growth": 110.0,"eps_trend": "up",   "fii_1m_cr": 850.0,   "sector_rotation": 68, "analyst_upgrades": 4, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "ASIANPAINT": {"q_rev_growth": 8.0,  "q_pat_growth": 10.0, "eps_trend": "flat", "fii_1m_cr": -420.0,  "sector_rotation": 44, "analyst_upgrades": 1, "analyst_downgrades": 2, "mgmt_guidance": "neutral"},
    "TITAN":      {"q_rev_growth": 18.0, "q_pat_growth": 22.0, "eps_trend": "up",   "fii_1m_cr": 450.0,   "sector_rotation": 64, "analyst_upgrades": 3, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "ULTRACEMCO": {"q_rev_growth": 9.0,  "q_pat_growth": 14.0, "eps_trend": "up",   "fii_1m_cr": 300.0,   "sector_rotation": 60, "analyst_upgrades": 2, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
    "GRASIM":     {"q_rev_growth": 11.0, "q_pat_growth": 15.0, "eps_trend": "up",   "fii_1m_cr": 320.0,   "sector_rotation": 61, "analyst_upgrades": 2, "analyst_downgrades": 0, "mgmt_guidance": "positive"},
}

# ─────────────────────────────────────────────────────────────────────────────
#  YEARLY FUNDAMENTAL DATA
#  Updated annually. Captures long-term structural quality:
#   - 3-year revenue CAGR %
#   - 3-year PAT CAGR %
#   - 3-year EPS CAGR %
#   - Return on Equity 3-year average
#   - Debt reduction % (positive = debt reduced)
#   - Dividend yield %
#   - Free cash flow yield %
#   - ESG / governance score (0-100)
#   - Market share trend: gaining / stable / losing
# ─────────────────────────────────────────────────────────────────────────────
YEARLY_DATA: Dict[str, Dict[str, Any]] = {
    "RELIANCE":   {"rev_cagr_3y": 12.5, "pat_cagr_3y": 14.2, "eps_cagr_3y": 13.8, "roe_avg_3y": 9.5,  "debt_reduction_pct": -5.0,  "div_yield": 0.35, "fcf_yield": 2.1, "esg_score": 62, "market_share": "gaining"},
    "ONGC":       {"rev_cagr_3y": 8.5,  "pat_cagr_3y": 22.0, "eps_cagr_3y": 20.5, "roe_avg_3y": 12.0, "debt_reduction_pct": 8.0,   "div_yield": 4.50, "fcf_yield": 5.2, "esg_score": 55, "market_share": "stable"},
    "BPCL":       {"rev_cagr_3y": 9.2,  "pat_cagr_3y": 35.0, "eps_cagr_3y": 32.0, "roe_avg_3y": 20.0, "debt_reduction_pct": 12.0,  "div_yield": 3.80, "fcf_yield": 4.8, "esg_score": 58, "market_share": "stable"},
    "COALINDIA":  {"rev_cagr_3y": 7.5,  "pat_cagr_3y": 18.0, "eps_cagr_3y": 17.5, "roe_avg_3y": 42.0, "debt_reduction_pct": 0.0,   "div_yield": 6.20, "fcf_yield": 8.5, "esg_score": 48, "market_share": "stable"},
    "POWERGRID":  {"rev_cagr_3y": 6.5,  "pat_cagr_3y": 8.0,  "eps_cagr_3y": 7.5,  "roe_avg_3y": 17.5, "debt_reduction_pct": -3.0,  "div_yield": 4.20, "fcf_yield": 3.8, "esg_score": 65, "market_share": "stable"},
    "NTPC":       {"rev_cagr_3y": 8.0,  "pat_cagr_3y": 12.0, "eps_cagr_3y": 11.5, "roe_avg_3y": 14.0, "debt_reduction_pct": -2.0,  "div_yield": 3.50, "fcf_yield": 3.2, "esg_score": 60, "market_share": "stable"},
    "HDFCBANK":   {"rev_cagr_3y": 16.0, "pat_cagr_3y": 18.0, "eps_cagr_3y": 17.5, "roe_avg_3y": 15.5, "debt_reduction_pct": 0.0,   "div_yield": 1.10, "fcf_yield": 1.2, "esg_score": 78, "market_share": "gaining"},
    "ICICIBANK":  {"rev_cagr_3y": 18.0, "pat_cagr_3y": 35.0, "eps_cagr_3y": 33.0, "roe_avg_3y": 17.0, "debt_reduction_pct": 0.0,   "div_yield": 0.80, "fcf_yield": 1.0, "esg_score": 76, "market_share": "gaining"},
    "SBIN":       {"rev_cagr_3y": 14.0, "pat_cagr_3y": 45.0, "eps_cagr_3y": 42.0, "roe_avg_3y": 14.0, "debt_reduction_pct": 0.0,   "div_yield": 1.80, "fcf_yield": 1.5, "esg_score": 70, "market_share": "stable"},
    "AXISBANK":   {"rev_cagr_3y": 15.0, "pat_cagr_3y": 28.0, "eps_cagr_3y": 26.0, "roe_avg_3y": 13.5, "debt_reduction_pct": 0.0,   "div_yield": 0.90, "fcf_yield": 0.8, "esg_score": 72, "market_share": "stable"},
    "KOTAKBANK":  {"rev_cagr_3y": 17.0, "pat_cagr_3y": 15.0, "eps_cagr_3y": 14.0, "roe_avg_3y": 14.0, "debt_reduction_pct": 0.0,   "div_yield": 0.10, "fcf_yield": 0.5, "esg_score": 80, "market_share": "stable"},
    "INDUSINDBK": {"rev_cagr_3y": 16.0, "pat_cagr_3y": 20.0, "eps_cagr_3y": 19.0, "roe_avg_3y": 14.5, "debt_reduction_pct": 0.0,   "div_yield": 0.80, "fcf_yield": 0.7, "esg_score": 68, "market_share": "stable"},
    "BAJFINANCE": {"rev_cagr_3y": 28.0, "pat_cagr_3y": 25.0, "eps_cagr_3y": 23.0, "roe_avg_3y": 21.0, "debt_reduction_pct": 0.0,   "div_yield": 0.45, "fcf_yield": 0.3, "esg_score": 72, "market_share": "gaining"},
    "BAJAJFINSV": {"rev_cagr_3y": 22.0, "pat_cagr_3y": 20.0, "eps_cagr_3y": 19.0, "roe_avg_3y": 17.5, "debt_reduction_pct": 0.0,   "div_yield": 0.20, "fcf_yield": 0.4, "esg_score": 70, "market_share": "stable"},
    "TCS":        {"rev_cagr_3y": 14.0, "pat_cagr_3y": 12.0, "eps_cagr_3y": 11.5, "roe_avg_3y": 45.0, "debt_reduction_pct": 0.0,   "div_yield": 1.40, "fcf_yield": 3.2, "esg_score": 88, "market_share": "stable"},
    "INFY":       {"rev_cagr_3y": 12.0, "pat_cagr_3y": 10.0, "eps_cagr_3y": 9.5,  "roe_avg_3y": 32.0, "debt_reduction_pct": 0.0,   "div_yield": 1.80, "fcf_yield": 3.5, "esg_score": 85, "market_share": "stable"},
    "WIPRO":      {"rev_cagr_3y": 10.0, "pat_cagr_3y": 8.0,  "eps_cagr_3y": 7.5,  "roe_avg_3y": 20.0, "debt_reduction_pct": 5.0,   "div_yield": 0.90, "fcf_yield": 2.8, "esg_score": 84, "market_share": "stable"},
    "HCLTECH":    {"rev_cagr_3y": 13.0, "pat_cagr_3y": 14.0, "eps_cagr_3y": 13.5, "roe_avg_3y": 26.0, "debt_reduction_pct": 2.0,   "div_yield": 3.20, "fcf_yield": 4.0, "esg_score": 82, "market_share": "gaining"},
    "TECHM":      {"rev_cagr_3y": 11.0, "pat_cagr_3y": 15.0, "eps_cagr_3y": 14.0, "roe_avg_3y": 17.5, "debt_reduction_pct": 3.0,   "div_yield": 2.80, "fcf_yield": 3.5, "esg_score": 80, "market_share": "stable"},
    "LTI":        {"rev_cagr_3y": 18.0, "pat_cagr_3y": 20.0, "eps_cagr_3y": 19.0, "roe_avg_3y": 29.0, "debt_reduction_pct": 0.0,   "div_yield": 0.90, "fcf_yield": 2.2, "esg_score": 78, "market_share": "gaining"},
    "HINDUNILVR": {"rev_cagr_3y": 8.0,  "pat_cagr_3y": 9.0,  "eps_cagr_3y": 8.5,  "roe_avg_3y": 22.0, "debt_reduction_pct": 0.0,   "div_yield": 1.50, "fcf_yield": 3.2, "esg_score": 86, "market_share": "stable"},
    "ITC":        {"rev_cagr_3y": 12.0, "pat_cagr_3y": 14.0, "eps_cagr_3y": 13.5, "roe_avg_3y": 28.0, "debt_reduction_pct": 0.0,   "div_yield": 3.60, "fcf_yield": 5.5, "esg_score": 75, "market_share": "gaining"},
    "NESTLEIND":  {"rev_cagr_3y": 10.0, "pat_cagr_3y": 12.0, "eps_cagr_3y": 11.5, "roe_avg_3y": 60.0, "debt_reduction_pct": 0.0,   "div_yield": 1.20, "fcf_yield": 2.8, "esg_score": 82, "market_share": "stable"},
    "BRITANNIA":  {"rev_cagr_3y": 8.0,  "pat_cagr_3y": 11.0, "eps_cagr_3y": 10.5, "roe_avg_3y": 42.0, "debt_reduction_pct": 8.0,   "div_yield": 1.80, "fcf_yield": 3.8, "esg_score": 72, "market_share": "stable"},
    "DABUR":      {"rev_cagr_3y": 9.0,  "pat_cagr_3y": 10.0, "eps_cagr_3y": 9.5,  "roe_avg_3y": 20.0, "debt_reduction_pct": 5.0,   "div_yield": 1.20, "fcf_yield": 3.5, "esg_score": 78, "market_share": "stable"},
    "SUNPHARMA":  {"rev_cagr_3y": 12.0, "pat_cagr_3y": 22.0, "eps_cagr_3y": 21.0, "roe_avg_3y": 15.0, "debt_reduction_pct": 15.0,  "div_yield": 0.80, "fcf_yield": 2.5, "esg_score": 70, "market_share": "gaining"},
    "DRREDDY":    {"rev_cagr_3y": 14.0, "pat_cagr_3y": 25.0, "eps_cagr_3y": 23.0, "roe_avg_3y": 21.0, "debt_reduction_pct": 20.0,  "div_yield": 0.60, "fcf_yield": 3.2, "esg_score": 72, "market_share": "stable"},
    "CIPLA":      {"rev_cagr_3y": 11.0, "pat_cagr_3y": 18.0, "eps_cagr_3y": 17.0, "roe_avg_3y": 17.5, "debt_reduction_pct": 12.0,  "div_yield": 0.50, "fcf_yield": 2.8, "esg_score": 68, "market_share": "stable"},
    "DIVISLAB":   {"rev_cagr_3y": 10.0, "pat_cagr_3y": 14.0, "eps_cagr_3y": 13.0, "roe_avg_3y": 20.0, "debt_reduction_pct": 0.0,   "div_yield": 0.90, "fcf_yield": 2.2, "esg_score": 74, "market_share": "stable"},
    "MARUTI":     {"rev_cagr_3y": 18.0, "pat_cagr_3y": 35.0, "eps_cagr_3y": 33.0, "roe_avg_3y": 20.0, "debt_reduction_pct": 0.0,   "div_yield": 0.60, "fcf_yield": 2.5, "esg_score": 72, "market_share": "gaining"},
    "TATAMOTORS": {"rev_cagr_3y": 22.0, "pat_cagr_3y": 85.0, "eps_cagr_3y": 78.0, "roe_avg_3y": 25.0, "debt_reduction_pct": 18.0,  "div_yield": 0.20, "fcf_yield": 1.8, "esg_score": 68, "market_share": "gaining"},
    "M&M":        {"rev_cagr_3y": 15.0, "pat_cagr_3y": 28.0, "eps_cagr_3y": 26.0, "roe_avg_3y": 19.0, "debt_reduction_pct": 5.0,   "div_yield": 0.80, "fcf_yield": 2.2, "esg_score": 74, "market_share": "gaining"},
    "BAJAJ-AUTO": {"rev_cagr_3y": 12.0, "pat_cagr_3y": 18.0, "eps_cagr_3y": 17.0, "roe_avg_3y": 28.0, "debt_reduction_pct": 0.0,   "div_yield": 1.80, "fcf_yield": 4.2, "esg_score": 72, "market_share": "stable"},
    "EICHERMOT":  {"rev_cagr_3y": 14.0, "pat_cagr_3y": 22.0, "eps_cagr_3y": 21.0, "roe_avg_3y": 26.0, "debt_reduction_pct": 0.0,   "div_yield": 1.20, "fcf_yield": 3.8, "esg_score": 75, "market_share": "gaining"},
    "TATASTEEL":  {"rev_cagr_3y": 12.0, "pat_cagr_3y": 20.0, "eps_cagr_3y": 18.0, "roe_avg_3y": 15.0, "debt_reduction_pct": 25.0,  "div_yield": 1.80, "fcf_yield": 3.5, "esg_score": 62, "market_share": "stable"},
    "JSWSTEEL":   {"rev_cagr_3y": 14.0, "pat_cagr_3y": 18.0, "eps_cagr_3y": 16.5, "roe_avg_3y": 18.5, "debt_reduction_pct": 10.0,  "div_yield": 1.20, "fcf_yield": 2.8, "esg_score": 65, "market_share": "stable"},
    "HINDALCO":   {"rev_cagr_3y": 10.0, "pat_cagr_3y": 15.0, "eps_cagr_3y": 14.0, "roe_avg_3y": 17.0, "debt_reduction_pct": 12.0,  "div_yield": 1.00, "fcf_yield": 2.5, "esg_score": 62, "market_share": "stable"},
    "VEDL":       {"rev_cagr_3y": 11.0, "pat_cagr_3y": 20.0, "eps_cagr_3y": 18.0, "roe_avg_3y": 25.0, "debt_reduction_pct": -5.0,  "div_yield": 8.50, "fcf_yield": 6.2, "esg_score": 52, "market_share": "stable"},
    "LT":         {"rev_cagr_3y": 16.0, "pat_cagr_3y": 18.0, "eps_cagr_3y": 17.0, "roe_avg_3y": 18.0, "debt_reduction_pct": 5.0,   "div_yield": 1.20, "fcf_yield": 2.2, "esg_score": 76, "market_share": "gaining"},
    "ADANIPORTS": {"rev_cagr_3y": 18.0, "pat_cagr_3y": 22.0, "eps_cagr_3y": 20.5, "roe_avg_3y": 16.0, "debt_reduction_pct": -8.0,  "div_yield": 0.60, "fcf_yield": 1.8, "esg_score": 58, "market_share": "gaining"},
    "ADANIENT":   {"rev_cagr_3y": 25.0, "pat_cagr_3y": 30.0, "eps_cagr_3y": 28.0, "roe_avg_3y": 14.0, "debt_reduction_pct": -15.0, "div_yield": 0.10, "fcf_yield": 0.5, "esg_score": 45, "market_share": "gaining"},
    "SIEMENS":    {"rev_cagr_3y": 18.0, "pat_cagr_3y": 22.0, "eps_cagr_3y": 20.5, "roe_avg_3y": 22.0, "debt_reduction_pct": 0.0,   "div_yield": 0.35, "fcf_yield": 1.8, "esg_score": 80, "market_share": "gaining"},
    "APOLLOHOSP": {"rev_cagr_3y": 20.0, "pat_cagr_3y": 45.0, "eps_cagr_3y": 42.0, "roe_avg_3y": 16.0, "debt_reduction_pct": -10.0, "div_yield": 0.40, "fcf_yield": 1.2, "esg_score": 72, "market_share": "gaining"},
    "SBILIFE":    {"rev_cagr_3y": 15.0, "pat_cagr_3y": 18.0, "eps_cagr_3y": 17.0, "roe_avg_3y": 14.0, "debt_reduction_pct": 0.0,   "div_yield": 0.30, "fcf_yield": 0.8, "esg_score": 74, "market_share": "gaining"},
    "HDFCLIFE":   {"rev_cagr_3y": 12.0, "pat_cagr_3y": 14.0, "eps_cagr_3y": 13.0, "roe_avg_3y": 11.0, "debt_reduction_pct": 0.0,   "div_yield": 0.40, "fcf_yield": 0.6, "esg_score": 76, "market_share": "stable"},
    "BHARTIARTL": {"rev_cagr_3y": 14.0, "pat_cagr_3y": 95.0, "eps_cagr_3y": 90.0, "roe_avg_3y": 12.0, "debt_reduction_pct": -5.0,  "div_yield": 0.40, "fcf_yield": 1.5, "esg_score": 70, "market_share": "gaining"},
    "ASIANPAINT": {"rev_cagr_3y": 12.0, "pat_cagr_3y": 10.0, "eps_cagr_3y": 9.5,  "roe_avg_3y": 28.0, "debt_reduction_pct": 0.0,   "div_yield": 0.80, "fcf_yield": 2.8, "esg_score": 80, "market_share": "stable"},
    "TITAN":      {"rev_cagr_3y": 22.0, "pat_cagr_3y": 28.0, "eps_cagr_3y": 26.0, "roe_avg_3y": 34.0, "debt_reduction_pct": 0.0,   "div_yield": 0.45, "fcf_yield": 1.8, "esg_score": 78, "market_share": "gaining"},
    "ULTRACEMCO": {"rev_cagr_3y": 12.0, "pat_cagr_3y": 18.0, "eps_cagr_3y": 17.0, "roe_avg_3y": 17.0, "debt_reduction_pct": 15.0,  "div_yield": 0.85, "fcf_yield": 2.2, "esg_score": 72, "market_share": "stable"},
    "GRASIM":     {"rev_cagr_3y": 14.0, "pat_cagr_3y": 18.0, "eps_cagr_3y": 17.0, "roe_avg_3y": 15.0, "debt_reduction_pct": 8.0,   "div_yield": 0.70, "fcf_yield": 2.0, "esg_score": 68, "market_share": "stable"},
}
