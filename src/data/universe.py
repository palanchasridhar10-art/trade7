"""Comprehensive Nifty 50 Company Database.

Contains per-company: price reference, fundamentals, sector, technical indicators,
and realistic order flow profiles. Used by the auto-trading loop to analyse ALL
companies and execute buy/sell orders on those that pass the high win-rate gate.
"""

from typing import Dict, Any

# ─────────────────────────────────────────────────────────────────────────────
#  NIFTY 50 COMPANY MASTER — 50 large-cap NSE stocks
#  Each entry:
#    price      : reference last traded price (₹)
#    sector     : NSE sector category
#    pe         : P/E ratio
#    sector_pe  : sector average P/E
#    pb         : Price-to-Book
#    roe        : Return on Equity (%)
#    roce       : Return on Capital Employed (%)
#    de         : Debt-to-Equity
#    rev_g      : Revenue growth YoY (%)
#    pat_g      : PAT growth YoY (%)
#    promoter   : Promoter holding (%)
#    pledge     : Promoter pledge (%)
#    event      : is results / major event due in 24h?
#    fo_ban     : F&O ban active?
# ─────────────────────────────────────────────────────────────────────────────
NIFTY50_UNIVERSE: Dict[str, Dict[str, Any]] = {
    # ── Energy / Oil & Gas ────────────────────────────────────────────────────
    "RELIANCE":  {"price": 2920.0, "sector": "Energy",      "pe": 24.5, "sector_pe": 22.0, "pb": 2.4, "roe": 9.8,  "roce": 11.2, "de": 0.42, "rev_g": 8.5,  "pat_g": 12.0, "promoter": 50.3, "pledge": 0.0},
    "ONGC":      {"price":  287.0, "sector": "Energy",      "pe": 7.2,  "sector_pe": 10.0, "pb": 0.9, "roe": 13.5, "roce": 15.0, "de": 0.20, "rev_g": 5.2,  "pat_g": 18.5, "promoter": 58.9, "pledge": 0.0},
    "BPCL":      {"price":  355.0, "sector": "Energy",      "pe": 8.5,  "sector_pe": 10.0, "pb": 1.8, "roe": 22.0, "roce": 19.5, "de": 0.35, "rev_g": 6.0,  "pat_g": 40.0, "promoter": 52.9, "pledge": 0.0},
    "COALINDIA": {"price":  505.0, "sector": "Metals",      "pe": 8.0,  "sector_pe": 9.5,  "pb": 3.5, "roe": 44.0, "roce": 51.0, "de": 0.01, "rev_g": 4.5,  "pat_g": 10.0, "promoter": 63.1, "pledge": 0.0},
    "POWERGRID": {"price":  344.0, "sector": "Utilities",   "pe": 18.5, "sector_pe": 20.0, "pb": 3.3, "roe": 18.0, "roce": 13.0, "de": 1.50, "rev_g": 7.0,  "pat_g": 9.0,  "promoter": 51.3, "pledge": 0.0},
    "NTPC":      {"price":  378.0, "sector": "Utilities",   "pe": 17.0, "sector_pe": 20.0, "pb": 2.5, "roe": 14.5, "roce": 11.0, "de": 1.30, "rev_g": 9.2,  "pat_g": 14.0, "promoter": 51.1, "pledge": 0.0},
    # ── Banking & Finance ─────────────────────────────────────────────────────
    "HDFCBANK":  {"price": 1660.0, "sector": "Banking",     "pe": 19.5, "sector_pe": 18.0, "pb": 2.8, "roe": 16.0, "roce": 8.0,  "de": 7.20, "rev_g": 14.0, "pat_g": 17.0, "promoter": 0.0,  "pledge": 0.0},
    "ICICIBANK": {"price": 1240.0, "sector": "Banking",     "pe": 18.5, "sector_pe": 18.0, "pb": 3.2, "roe": 18.5, "roce": 9.5,  "de": 6.80, "rev_g": 16.0, "pat_g": 28.0, "promoter": 0.0,  "pledge": 0.0},
    "SBIN":      {"price":  795.0, "sector": "Banking",     "pe": 11.0, "sector_pe": 18.0, "pb": 1.8, "roe": 16.8, "roce": 7.5,  "de": 14.0, "rev_g": 11.0, "pat_g": 22.0, "promoter": 57.5, "pledge": 0.0},
    "AXISBANK":  {"price": 1145.0, "sector": "Banking",     "pe": 16.5, "sector_pe": 18.0, "pb": 2.2, "roe": 14.5, "roce": 7.0,  "de": 8.50, "rev_g": 13.0, "pat_g": 19.0, "promoter": 8.2,  "pledge": 0.0},
    "KOTAKBANK": {"price": 1890.0, "sector": "Banking",     "pe": 22.0, "sector_pe": 18.0, "pb": 3.5, "roe": 14.8, "roce": 8.0,  "de": 7.60, "rev_g": 15.0, "pat_g": 12.0, "promoter": 26.0, "pledge": 0.0},
    "INDUSINDBK":{"price": 1385.0, "sector": "Banking",     "pe": 12.0, "sector_pe": 18.0, "pb": 1.8, "roe": 15.5, "roce": 7.8,  "de": 9.20, "rev_g": 14.5, "pat_g": 16.0, "promoter": 16.5, "pledge": 0.0},
    "BAJFINANCE": {"price":6780.0, "sector": "NBFC",        "pe": 30.0, "sector_pe": 28.0, "pb": 6.2, "roe": 22.0, "roce": 10.5, "de": 4.20, "rev_g": 25.0, "pat_g": 22.0, "promoter": 55.9, "pledge": 0.0},
    "BAJAJFINSV":{"price": 1685.0, "sector": "NBFC",        "pe": 22.0, "sector_pe": 25.0, "pb": 3.8, "roe": 18.0, "roce": 9.0,  "de": 3.80, "rev_g": 20.0, "pat_g": 18.0, "promoter": 55.9, "pledge": 0.0},
    # ── Information Technology ─────────────────────────────────────────────────
    "TCS":       {"price": 4150.0, "sector": "IT",          "pe": 30.5, "sector_pe": 28.0, "pb": 13.2,"roe": 44.0, "roce": 55.0, "de": 0.02, "rev_g": 7.5,  "pat_g": 9.5,  "promoter": 72.3, "pledge": 0.0},
    "INFY":      {"price": 1880.0, "sector": "IT",          "pe": 27.0, "sector_pe": 28.0, "pb": 8.5, "roe": 32.0, "roce": 40.0, "de": 0.03, "rev_g": 6.5,  "pat_g": 8.0,  "promoter": 14.8, "pledge": 0.0, "event": True},
    "WIPRO":     {"price":  545.0, "sector": "IT",          "pe": 24.5, "sector_pe": 28.0, "pb": 4.8, "roe": 20.0, "roce": 25.0, "de": 0.10, "rev_g": 4.0,  "pat_g": 6.0,  "promoter": 72.9, "pledge": 0.0},
    "HCLTECH":   {"price": 1560.0, "sector": "IT",          "pe": 26.0, "sector_pe": 28.0, "pb": 6.8, "roe": 26.5, "roce": 32.0, "de": 0.05, "rev_g": 9.0,  "pat_g": 11.0, "promoter": 60.8, "pledge": 0.0},
    "TECHM":     {"price": 1480.0, "sector": "IT",          "pe": 25.5, "sector_pe": 28.0, "pb": 4.2, "roe": 17.0, "roce": 22.0, "de": 0.08, "rev_g": 5.5,  "pat_g": 12.5, "promoter": 35.1, "pledge": 0.0},
    "LTI":       {"price": 5550.0, "sector": "IT",          "pe": 32.0, "sector_pe": 28.0, "pb": 9.5, "roe": 30.0, "roce": 38.0, "de": 0.01, "rev_g": 12.0, "pat_g": 15.0, "promoter": 74.0, "pledge": 0.0},
    # ── FMCG / Consumer ───────────────────────────────────────────────────────
    "HINDUNILVR":{"price": 2580.0, "sector": "FMCG",        "pe": 55.0, "sector_pe": 50.0, "pb": 12.0,"roe": 22.0, "roce": 28.0, "de": 0.00, "rev_g": 5.0,  "pat_g": 8.0,  "promoter": 61.9, "pledge": 0.0},
    "ITC":       {"price":  485.0, "sector": "FMCG",        "pe": 27.0, "sector_pe": 30.0, "pb": 7.5, "roe": 28.5, "roce": 35.0, "de": 0.00, "rev_g": 8.0,  "pat_g": 12.0, "promoter": 0.0,  "pledge": 0.0},
    "NESTLEIND": {"price":  2420.0,"sector": "FMCG",        "pe": 75.0, "sector_pe": 60.0, "pb": 45.0,"roe": 60.0, "roce": 80.0, "de": 0.00, "rev_g": 10.0, "pat_g": 14.0, "promoter": 62.8, "pledge": 0.0},
    "BRITANNIA": {"price": 5680.0, "sector": "FMCG",        "pe": 52.0, "sector_pe": 50.0, "pb": 22.0,"roe": 42.0, "roce": 55.0, "de": 0.20, "rev_g": 6.5,  "pat_g": 10.0, "promoter": 50.5, "pledge": 0.0},
    "DABUR":     {"price":  590.0, "sector": "FMCG",        "pe": 45.0, "sector_pe": 45.0, "pb": 9.0, "roe": 20.0, "roce": 25.0, "de": 0.05, "rev_g": 7.0,  "pat_g": 9.0,  "promoter": 67.9, "pledge": 0.0},
    # ── Pharma ────────────────────────────────────────────────────────────────
    "SUNPHARMA": {"price": 1740.0, "sector": "Pharma",      "pe": 35.0, "sector_pe": 30.0, "pb": 5.2, "roe": 15.0, "roce": 17.0, "de": 0.08, "rev_g": 10.5, "pat_g": 20.0, "promoter": 54.5, "pledge": 0.0},
    "DRREDDY":   {"price": 6450.0, "sector": "Pharma",      "pe": 22.0, "sector_pe": 28.0, "pb": 4.5, "roe": 21.0, "roce": 24.0, "de": 0.15, "rev_g": 12.0, "pat_g": 18.0, "promoter": 26.7, "pledge": 0.0},
    "CIPLA":     {"price": 1530.0, "sector": "Pharma",      "pe": 28.0, "sector_pe": 28.0, "pb": 4.8, "roe": 17.5, "roce": 20.0, "de": 0.05, "rev_g": 9.0,  "pat_g": 14.0, "promoter": 33.5, "pledge": 0.0},
    "DIVISLAB":  {"price": 4980.0, "sector": "Pharma",      "pe": 52.0, "sector_pe": 35.0, "pb": 10.5,"roe": 20.0, "roce": 24.0, "de": 0.00, "rev_g": 8.5,  "pat_g": 12.0, "promoter": 51.9, "pledge": 0.0},
    # ── Auto ──────────────────────────────────────────────────────────────────
    "MARUTI":    {"price": 12400.0,"sector": "Auto",        "pe": 27.0, "sector_pe": 25.0, "pb": 5.5, "roe": 20.8, "roce": 24.0, "de": 0.00, "rev_g": 15.0, "pat_g": 30.0, "promoter": 58.2, "pledge": 0.0},
    "TATAMOTORS":{"price":  985.0, "sector": "Auto",        "pe": 12.5, "sector_pe": 20.0, "pb": 3.8, "roe": 30.0, "roce": 18.0, "de": 0.65, "rev_g": 18.0, "pat_g": 120.0,"promoter": 42.6, "pledge": 0.5},
    "M&M":       {"price": 2900.0, "sector": "Auto",        "pe": 25.0, "sector_pe": 22.0, "pb": 5.0, "roe": 20.0, "roce": 22.0, "de": 0.10, "rev_g": 12.0, "pat_g": 20.0, "promoter": 18.7, "pledge": 0.0},
    "BAJAJ-AUTO":{"price": 9850.0, "sector": "Auto",        "pe": 30.0, "sector_pe": 25.0, "pb": 8.5, "roe": 28.0, "roce": 35.0, "de": 0.00, "rev_g": 10.0, "pat_g": 22.0, "promoter": 54.9, "pledge": 0.0},
    "EICHERMOT": {"price": 4980.0, "sector": "Auto",        "pe": 35.0, "sector_pe": 28.0, "pb": 9.0, "roe": 26.0, "roce": 32.0, "de": 0.00, "rev_g": 11.0, "pat_g": 18.0, "promoter": 49.2, "pledge": 0.0},
    # ── Metals & Mining ───────────────────────────────────────────────────────
    "TATASTEEL": {"price":  162.0, "sector": "Metals",      "pe": 11.0, "sector_pe": 12.0, "pb": 1.8, "roe": 16.5, "roce": 12.0, "de": 0.80, "rev_g": 5.5,  "pat_g": 8.0,  "promoter": 34.0, "pledge": 0.0},
    "JSWSTEEL":  {"price":  932.0, "sector": "Metals",      "pe": 18.5, "sector_pe": 15.0, "pb": 3.5, "roe": 19.0, "roce": 14.0, "de": 0.72, "rev_g": 7.0,  "pat_g": 10.0, "promoter": 44.8, "pledge": 0.0},
    "HINDALCO":  {"price":  690.0, "sector": "Metals",      "pe": 13.0, "sector_pe": 12.0, "pb": 2.2, "roe": 17.0, "roce": 14.0, "de": 0.85, "rev_g": 6.0,  "pat_g": 8.0,  "promoter": 34.7, "pledge": 0.0},
    "VEDL":      {"price":  468.0, "sector": "Metals",      "pe": 14.5, "sector_pe": 14.0, "pb": 3.8, "roe": 26.5, "roce": 20.0, "de": 0.60, "rev_g": 8.0,  "pat_g": 15.0, "promoter": 55.1, "pledge": 2.5},
    # ── Capital Goods / Infra ────────────────────────────────────────────────
    "LT":        {"price": 3680.0, "sector": "Construction","pe": 32.0, "sector_pe": 28.0, "pb": 5.8, "roe": 18.0, "roce": 15.0, "de": 0.40, "rev_g": 14.0, "pat_g": 16.0, "promoter": 0.0,  "pledge": 0.0},
    "ADANIPORTS":{"price": 1450.0, "sector": "Ports",       "pe": 28.0, "sector_pe": 25.0, "pb": 4.5, "roe": 16.0, "roce": 12.0, "de": 0.90, "rev_g": 12.0, "pat_g": 18.0, "promoter": 65.8, "pledge": 0.5},
    "ADANIENT":  {"price": 2780.0, "sector": "Conglomerate","pe": 55.0, "sector_pe": 40.0, "pb": 8.0, "roe": 15.0, "roce": 10.0, "de": 1.80, "rev_g": 22.0, "pat_g": 25.0, "promoter": 72.6, "pledge": 4.0},
    "SIEMENS":   {"price": 7200.0, "sector": "Capital Goods","pe": 68.0,"sector_pe": 45.0, "pb": 15.0,"roe": 22.0, "roce": 28.0, "de": 0.00, "rev_g": 16.0, "pat_g": 20.0, "promoter": 75.0, "pledge": 0.0},
    # ── Healthcare / Insurance ────────────────────────────────────────────────
    "APOLLOHOSP":{"price": 7150.0, "sector": "Healthcare",  "pe": 72.0, "sector_pe": 55.0, "pb": 12.5,"roe": 17.5, "roce": 14.0, "de": 0.65, "rev_g": 18.0, "pat_g": 40.0, "promoter": 29.3, "pledge": 0.0},
    "SBILIFE":   {"price": 1785.0, "sector": "Insurance",   "pe": 72.0, "sector_pe": 65.0, "pb": 10.0,"roe": 14.0, "roce": 7.0,  "de": 0.00, "rev_g": 12.0, "pat_g": 15.0, "promoter": 55.5, "pledge": 0.0},
    "HDFCLIFE":  {"price": 765.0,  "sector": "Insurance",   "pe": 88.0, "sector_pe": 75.0, "pb": 9.2, "roe": 11.0, "roce": 6.0,  "de": 0.00, "rev_g": 10.0, "pat_g": 12.0, "promoter": 50.4, "pledge": 0.0},
    # ── Telecom / Technology ──────────────────────────────────────────────────
    "BHARTIARTL":{"price": 1680.0, "sector": "Telecom",     "pe": 65.0, "sector_pe": 50.0, "pb": 8.5, "roe": 13.0, "roce": 8.0,  "de": 1.50, "rev_g": 12.0, "pat_g": 110.0,"promoter": 55.9, "pledge": 0.0},
    "ASIANPAINT":{"price": 2930.0, "sector": "Consumer",    "pe": 58.0, "sector_pe": 55.0, "pb": 16.0,"roe": 28.0, "roce": 35.0, "de": 0.02, "rev_g": 8.0,  "pat_g": 10.0, "promoter": 52.8, "pledge": 0.0},
    "TITAN":     {"price": 3760.0, "sector": "Consumer",    "pe": 82.0, "sector_pe": 60.0, "pb": 28.0,"roe": 34.0, "roce": 40.0, "de": 0.00, "rev_g": 18.0, "pat_g": 22.0, "promoter": 52.9, "pledge": 0.0},
    "ULTRACEMCO":{"price": 11250.0,"sector": "Cement",      "pe": 38.0, "sector_pe": 30.0, "pb": 6.5, "roe": 17.0, "roce": 20.0, "de": 0.12, "rev_g": 9.0,  "pat_g": 14.0, "promoter": 59.7, "pledge": 0.0},
    "GRASIM":    {"price": 2680.0, "sector": "Cement",      "pe": 22.0, "sector_pe": 28.0, "pb": 3.2, "roe": 15.0, "roce": 14.0, "de": 0.55, "rev_g": 11.0, "pat_g": 15.0, "promoter": 42.7, "pledge": 0.0},
}

# ─────────────────────────────────────────────────────────────────────────────
#  PER-COMPANY ORDER FLOW PROFILES (bid/ask depth, CVD, institutional flows)
#  These represent the realistic order book conditions for each stock.
#  Positive cumulative_delta = net buyer pressure (LONG signal)
#  Negative cumulative_delta = net seller pressure (SHORT signal)
# ─────────────────────────────────────────────────────────────────────────────
ORDER_FLOW_PROFILES: Dict[str, Dict[str, Any]] = {
    "RELIANCE":   {"bid_depth_qty": 350_000, "ask_depth_qty": 210_000, "buy_volume": 1_250_000, "sell_volume": 850_000,   "cumulative_delta":  400_000, "total_volume": 2_100_000, "institutional_block_buys": 65_000,  "institutional_block_sells": 15_000},
    "ONGC":       {"bid_depth_qty": 520_000, "ask_depth_qty": 280_000, "buy_volume": 2_800_000, "sell_volume": 1_600_000,  "cumulative_delta":  1_200_000,"total_volume": 4_400_000, "institutional_block_buys": 90_000,  "institutional_block_sells": 20_000},
    "BPCL":       {"bid_depth_qty": 480_000, "ask_depth_qty": 240_000, "buy_volume": 1_900_000, "sell_volume": 1_100_000,  "cumulative_delta":  800_000, "total_volume": 3_000_000, "institutional_block_buys": 75_000,  "institutional_block_sells": 18_000},
    "COALINDIA":  {"bid_depth_qty": 600_000, "ask_depth_qty": 310_000, "buy_volume": 3_500_000, "sell_volume": 2_000_000,  "cumulative_delta":  1_500_000,"total_volume": 5_500_000, "institutional_block_buys": 110_000, "institutional_block_sells": 25_000},
    "POWERGRID":  {"bid_depth_qty": 400_000, "ask_depth_qty": 350_000, "buy_volume": 2_100_000, "sell_volume": 1_900_000,  "cumulative_delta":  200_000, "total_volume": 4_000_000, "institutional_block_buys": 40_000,  "institutional_block_sells": 35_000},
    "NTPC":       {"bid_depth_qty": 450_000, "ask_depth_qty": 320_000, "buy_volume": 2_400_000, "sell_volume": 1_700_000,  "cumulative_delta":  700_000, "total_volume": 4_100_000, "institutional_block_buys": 60_000,  "institutional_block_sells": 22_000},
    "HDFCBANK":   {"bid_depth_qty": 410_000, "ask_depth_qty": 360_000, "buy_volume": 1_800_000, "sell_volume": 1_500_000,  "cumulative_delta":  300_000, "total_volume": 3_300_000, "institutional_block_buys": 80_000,  "institutional_block_sells": 30_000},
    "ICICIBANK":  {"bid_depth_qty": 300_000, "ask_depth_qty": 260_000, "buy_volume": 1_400_000, "sell_volume": 1_200_000,  "cumulative_delta":  200_000, "total_volume": 2_600_000, "institutional_block_buys": 40_000,  "institutional_block_sells": 20_000},
    "SBIN":       {"bid_depth_qty": 550_000, "ask_depth_qty": 320_000, "buy_volume": 2_100_000, "sell_volume": 1_400_000,  "cumulative_delta":  700_000, "total_volume": 3_500_000, "institutional_block_buys": 120_000, "institutional_block_sells": 25_000},
    "AXISBANK":   {"bid_depth_qty": 380_000, "ask_depth_qty": 290_000, "buy_volume": 1_600_000, "sell_volume": 1_200_000,  "cumulative_delta":  400_000, "total_volume": 2_800_000, "institutional_block_buys": 55_000,  "institutional_block_sells": 22_000},
    "KOTAKBANK":  {"bid_depth_qty": 200_000, "ask_depth_qty": 280_000, "buy_volume": 850_000,  "sell_volume": 1_100_000,   "cumulative_delta": -250_000, "total_volume": 1_950_000, "institutional_block_buys": 12_000,  "institutional_block_sells": 48_000},
    "INDUSINDBK": {"bid_depth_qty": 310_000, "ask_depth_qty": 270_000, "buy_volume": 1_200_000, "sell_volume": 1_050_000,  "cumulative_delta":  150_000, "total_volume": 2_250_000, "institutional_block_buys": 35_000,  "institutional_block_sells": 25_000},
    "BAJFINANCE": {"bid_depth_qty": 180_000, "ask_depth_qty": 290_000, "buy_volume": 650_000,  "sell_volume": 920_000,     "cumulative_delta": -270_000, "total_volume": 1_570_000, "institutional_block_buys": 8_000,   "institutional_block_sells": 52_000},
    "BAJAJFINSV": {"bid_depth_qty": 250_000, "ask_depth_qty": 220_000, "buy_volume": 1_100_000, "sell_volume": 950_000,    "cumulative_delta":  150_000, "total_volume": 2_050_000, "institutional_block_buys": 30_000,  "institutional_block_sells": 20_000},
    "TCS":        {"bid_depth_qty": 140_000, "ask_depth_qty": 280_000, "buy_volume": 420_000,  "sell_volume": 680_000,     "cumulative_delta": -260_000, "total_volume": 1_100_000, "institutional_block_buys": 5_000,   "institutional_block_sells": 45_000},
    "INFY":       {"bid_depth_qty": 200_000, "ask_depth_qty": 190_000, "buy_volume": 1_620_000, "sell_volume": 1_580_000,  "cumulative_delta":   40_000, "total_volume": 3_200_000, "institutional_block_buys": 20_000,  "institutional_block_sells": 18_000},
    "WIPRO":      {"bid_depth_qty": 280_000, "ask_depth_qty": 240_000, "buy_volume": 1_500_000, "sell_volume": 1_200_000,  "cumulative_delta":  300_000, "total_volume": 2_700_000, "institutional_block_buys": 45_000,  "institutional_block_sells": 18_000},
    "HCLTECH":    {"bid_depth_qty": 320_000, "ask_depth_qty": 250_000, "buy_volume": 1_800_000, "sell_volume": 1_350_000,  "cumulative_delta":  450_000, "total_volume": 3_150_000, "institutional_block_buys": 60_000,  "institutional_block_sells": 20_000},
    "TECHM":      {"bid_depth_qty": 260_000, "ask_depth_qty": 220_000, "buy_volume": 1_300_000, "sell_volume": 1_050_000,  "cumulative_delta":  250_000, "total_volume": 2_350_000, "institutional_block_buys": 38_000,  "institutional_block_sells": 15_000},
    "LTI":        {"bid_depth_qty": 150_000, "ask_depth_qty": 130_000, "buy_volume":  900_000,  "sell_volume": 750_000,    "cumulative_delta":  150_000, "total_volume": 1_650_000, "institutional_block_buys": 28_000,  "institutional_block_sells": 12_000},
    "HINDUNILVR": {"bid_depth_qty": 180_000, "ask_depth_qty": 220_000, "buy_volume":  800_000,  "sell_volume": 980_000,    "cumulative_delta": -180_000, "total_volume": 1_780_000, "institutional_block_buys": 10_000,  "institutional_block_sells": 42_000},
    "ITC":        {"bid_depth_qty": 650_000, "ask_depth_qty": 380_000, "buy_volume": 4_200_000, "sell_volume": 2_800_000,  "cumulative_delta": 1_400_000,"total_volume": 7_000_000, "institutional_block_buys": 150_000, "institutional_block_sells": 40_000},
    "NESTLEIND":  {"bid_depth_qty": 80_000,  "ask_depth_qty": 90_000,  "buy_volume":  320_000,  "sell_volume": 360_000,    "cumulative_delta":  -40_000, "total_volume":  680_000,  "institutional_block_buys": 5_000,   "institutional_block_sells": 12_000},
    "BRITANNIA":  {"bid_depth_qty": 95_000,  "ask_depth_qty": 80_000,  "buy_volume":  450_000,  "sell_volume": 380_000,    "cumulative_delta":   70_000, "total_volume":  830_000,  "institutional_block_buys": 12_000,  "institutional_block_sells": 8_000},
    "DABUR":      {"bid_depth_qty": 200_000, "ask_depth_qty": 175_000, "buy_volume":  900_000,  "sell_volume": 780_000,    "cumulative_delta":  120_000, "total_volume": 1_680_000, "institutional_block_buys": 22_000,  "institutional_block_sells": 14_000},
    "SUNPHARMA":  {"bid_depth_qty": 280_000, "ask_depth_qty": 220_000, "buy_volume": 1_300_000, "sell_volume": 1_050_000,  "cumulative_delta":  250_000, "total_volume": 2_350_000, "institutional_block_buys": 45_000,  "institutional_block_sells": 18_000},
    "DRREDDY":    {"bid_depth_qty": 120_000, "ask_depth_qty": 100_000, "buy_volume":  580_000,  "sell_volume": 470_000,    "cumulative_delta":  110_000, "total_volume": 1_050_000, "institutional_block_buys": 20_000,  "institutional_block_sells": 10_000},
    "CIPLA":      {"bid_depth_qty": 220_000, "ask_depth_qty": 180_000, "buy_volume": 1_100_000, "sell_volume": 880_000,    "cumulative_delta":  220_000, "total_volume": 1_980_000, "institutional_block_buys": 35_000,  "institutional_block_sells": 15_000},
    "DIVISLAB":   {"bid_depth_qty": 90_000,  "ask_depth_qty": 110_000, "buy_volume":  380_000,  "sell_volume": 460_000,    "cumulative_delta":  -80_000, "total_volume":  840_000,  "institutional_block_buys": 8_000,   "institutional_block_sells": 18_000},
    "MARUTI":     {"bid_depth_qty": 90_000,  "ask_depth_qty": 70_000,  "buy_volume":  420_000,  "sell_volume": 340_000,    "cumulative_delta":   80_000, "total_volume":  760_000,  "institutional_block_buys": 18_000,  "institutional_block_sells": 8_000},
    "TATAMOTORS": {"bid_depth_qty": 580_000, "ask_depth_qty": 330_000, "buy_volume": 3_800_000, "sell_volume": 2_500_000,  "cumulative_delta": 1_300_000,"total_volume": 6_300_000, "institutional_block_buys": 130_000, "institutional_block_sells": 35_000},
    "M&M":        {"bid_depth_qty": 200_000, "ask_depth_qty": 165_000, "buy_volume":  950_000,  "sell_volume": 780_000,    "cumulative_delta":  170_000, "total_volume": 1_730_000, "institutional_block_buys": 32_000,  "institutional_block_sells": 15_000},
    "BAJAJ-AUTO": {"bid_depth_qty": 75_000,  "ask_depth_qty": 65_000,  "buy_volume":  350_000,  "sell_volume": 290_000,    "cumulative_delta":   60_000, "total_volume":  640_000,  "institutional_block_buys": 15_000,  "institutional_block_sells": 8_000},
    "EICHERMOT":  {"bid_depth_qty": 110_000, "ask_depth_qty": 90_000,  "buy_volume":  520_000,  "sell_volume": 420_000,    "cumulative_delta":  100_000, "total_volume":  940_000,  "institutional_block_buys": 20_000,  "institutional_block_sells": 10_000},
    "TATASTEEL":  {"bid_depth_qty": 750_000, "ask_depth_qty": 420_000, "buy_volume": 5_500_000, "sell_volume": 3_800_000,  "cumulative_delta": 1_700_000,"total_volume": 9_300_000, "institutional_block_buys": 160_000, "institutional_block_sells": 45_000},
    "JSWSTEEL":   {"bid_depth_qty": 420_000, "ask_depth_qty": 310_000, "buy_volume": 2_600_000, "sell_volume": 1_900_000,  "cumulative_delta":  700_000, "total_volume": 4_500_000, "institutional_block_buys": 85_000,  "institutional_block_sells": 30_000},
    "HINDALCO":   {"bid_depth_qty": 380_000, "ask_depth_qty": 290_000, "buy_volume": 2_200_000, "sell_volume": 1_650_000,  "cumulative_delta":  550_000, "total_volume": 3_850_000, "institutional_block_buys": 70_000,  "institutional_block_sells": 25_000},
    "VEDL":       {"bid_depth_qty": 310_000, "ask_depth_qty": 280_000, "buy_volume": 1_800_000, "sell_volume": 1_600_000,  "cumulative_delta":  200_000, "total_volume": 3_400_000, "institutional_block_buys": 40_000,  "institutional_block_sells": 32_000},
    "LT":         {"bid_depth_qty": 185_000, "ask_depth_qty": 155_000, "buy_volume":  900_000,  "sell_volume": 730_000,    "cumulative_delta":  170_000, "total_volume": 1_630_000, "institutional_block_buys": 30_000,  "institutional_block_sells": 14_000},
    "ADANIPORTS": {"bid_depth_qty": 260_000, "ask_depth_qty": 210_000, "buy_volume": 1_200_000, "sell_volume": 960_000,    "cumulative_delta":  240_000, "total_volume": 2_160_000, "institutional_block_buys": 42_000,  "institutional_block_sells": 18_000},
    "ADANIENT":   {"bid_depth_qty": 200_000, "ask_depth_qty": 240_000, "buy_volume":  880_000,  "sell_volume": 1_050_000,  "cumulative_delta": -170_000, "total_volume": 1_930_000, "institutional_block_buys": 15_000,  "institutional_block_sells": 40_000},
    "SIEMENS":    {"bid_depth_qty": 60_000,  "ask_depth_qty": 50_000,  "buy_volume":  280_000,  "sell_volume": 220_000,    "cumulative_delta":   60_000, "total_volume":  500_000,  "institutional_block_buys": 12_000,  "institutional_block_sells": 6_000},
    "APOLLOHOSP": {"bid_depth_qty": 80_000,  "ask_depth_qty": 65_000,  "buy_volume":  360_000,  "sell_volume": 290_000,    "cumulative_delta":   70_000, "total_volume":  650_000,  "institutional_block_buys": 15_000,  "institutional_block_sells": 8_000},
    "SBILIFE":    {"bid_depth_qty": 160_000, "ask_depth_qty": 140_000, "buy_volume":  720_000,  "sell_volume": 600_000,    "cumulative_delta":  120_000, "total_volume": 1_320_000, "institutional_block_buys": 25_000,  "institutional_block_sells": 12_000},
    "HDFCLIFE":   {"bid_depth_qty": 210_000, "ask_depth_qty": 195_000, "buy_volume":  950_000,  "sell_volume": 880_000,    "cumulative_delta":   70_000, "total_volume": 1_830_000, "institutional_block_buys": 22_000,  "institutional_block_sells": 16_000},
    "BHARTIARTL": {"bid_depth_qty": 340_000, "ask_depth_qty": 270_000, "buy_volume": 1_600_000, "sell_volume": 1_250_000,  "cumulative_delta":  350_000, "total_volume": 2_850_000, "institutional_block_buys": 55_000,  "institutional_block_sells": 20_000},
    "ASIANPAINT": {"bid_depth_qty": 120_000, "ask_depth_qty": 150_000, "buy_volume":  540_000,  "sell_volume": 660_000,    "cumulative_delta": -120_000, "total_volume": 1_200_000, "institutional_block_buys": 8_000,   "institutional_block_sells": 28_000},
    "TITAN":      {"bid_depth_qty": 155_000, "ask_depth_qty": 120_000, "buy_volume":  720_000,  "sell_volume": 560_000,    "cumulative_delta":  160_000, "total_volume": 1_280_000, "institutional_block_buys": 28_000,  "institutional_block_sells": 12_000},
    "ULTRACEMCO": {"bid_depth_qty": 75_000,  "ask_depth_qty": 60_000,  "buy_volume":  350_000,  "sell_volume": 280_000,    "cumulative_delta":   70_000, "total_volume":  630_000,  "institutional_block_buys": 16_000,  "institutional_block_sells": 8_000},
    "GRASIM":     {"bid_depth_qty": 130_000, "ask_depth_qty": 110_000, "buy_volume":  620_000,  "sell_volume": 510_000,    "cumulative_delta":  110_000, "total_volume": 1_130_000, "institutional_block_buys": 22_000,  "institutional_block_sells": 12_000},
}

# ─────────────────────────────────────────────────────────────────────────────
#  PER-COMPANY TECHNICAL INDICATOR PROFILES
#  adx_offset : how much above/below base ADX (30) to simulate
#  rsi        : current RSI reading
#  macd_hist  : MACD histogram value (+ve = bullish momentum)
#  volume_ratio: current volume vs 20-DMA
#  vwap_diff  : price as fraction of VWAP (>1 = above VWAP)
# ─────────────────────────────────────────────────────────────────────────────
TECHNICAL_PROFILES: Dict[str, Dict[str, Any]] = {
    # Strong BUY setups (ADX > 28, RSI 55-78, above VWAP, strong vol)
    "RELIANCE":   {"adx": 32.0, "rsi14": 63.0, "macd_hist":  3.5, "volume_ratio": 1.60, "vwap_ratio": 1.006, "ema20_r": 0.990, "ema50_r": 0.970, "ema200_r": 0.920},
    "ONGC":       {"adx": 35.0, "rsi14": 67.0, "macd_hist":  4.2, "volume_ratio": 1.80, "vwap_ratio": 1.008, "ema20_r": 0.988, "ema50_r": 0.968, "ema200_r": 0.915},
    "BPCL":       {"adx": 33.0, "rsi14": 64.0, "macd_hist":  3.8, "volume_ratio": 1.70, "vwap_ratio": 1.007, "ema20_r": 0.991, "ema50_r": 0.972, "ema200_r": 0.922},
    "COALINDIA":  {"adx": 38.0, "rsi14": 70.0, "macd_hist":  5.0, "volume_ratio": 1.90, "vwap_ratio": 1.010, "ema20_r": 0.985, "ema50_r": 0.965, "ema200_r": 0.910},
    "SBIN":       {"adx": 34.0, "rsi14": 65.0, "macd_hist":  4.0, "volume_ratio": 1.75, "vwap_ratio": 1.007, "ema20_r": 0.989, "ema50_r": 0.970, "ema200_r": 0.918},
    "HDFCBANK":   {"adx": 30.0, "rsi14": 60.0, "macd_hist":  2.8, "volume_ratio": 1.50, "vwap_ratio": 1.005, "ema20_r": 0.992, "ema50_r": 0.974, "ema200_r": 0.925},
    "ICICIBANK":  {"adx": 31.0, "rsi14": 61.0, "macd_hist":  3.0, "volume_ratio": 1.55, "vwap_ratio": 1.006, "ema20_r": 0.991, "ema50_r": 0.972, "ema200_r": 0.922},
    "AXISBANK":   {"adx": 29.0, "rsi14": 58.0, "macd_hist":  2.2, "volume_ratio": 1.40, "vwap_ratio": 1.004, "ema20_r": 0.993, "ema50_r": 0.975, "ema200_r": 0.928},
    "TATAMOTORS": {"adx": 40.0, "rsi14": 72.0, "macd_hist":  6.5, "volume_ratio": 2.10, "vwap_ratio": 1.012, "ema20_r": 0.982, "ema50_r": 0.960, "ema200_r": 0.905},
    "TATASTEEL":  {"adx": 36.0, "rsi14": 68.0, "macd_hist":  4.8, "volume_ratio": 1.85, "vwap_ratio": 1.009, "ema20_r": 0.987, "ema50_r": 0.966, "ema200_r": 0.912},
    "ITC":        {"adx": 33.0, "rsi14": 65.0, "macd_hist":  4.2, "volume_ratio": 1.70, "vwap_ratio": 1.008, "ema20_r": 0.990, "ema50_r": 0.971, "ema200_r": 0.920},
    "WIPRO":      {"adx": 29.0, "rsi14": 57.0, "macd_hist":  2.5, "volume_ratio": 1.35, "vwap_ratio": 1.004, "ema20_r": 0.992, "ema50_r": 0.973, "ema200_r": 0.925},
    "HCLTECH":    {"adx": 31.0, "rsi14": 60.0, "macd_hist":  3.0, "volume_ratio": 1.45, "vwap_ratio": 1.005, "ema20_r": 0.991, "ema50_r": 0.972, "ema200_r": 0.922},
    "TECHM":      {"adx": 30.0, "rsi14": 59.0, "macd_hist":  2.8, "volume_ratio": 1.40, "vwap_ratio": 1.005, "ema20_r": 0.992, "ema50_r": 0.973, "ema200_r": 0.924},
    "LTI":        {"adx": 29.0, "rsi14": 57.0, "macd_hist":  2.2, "volume_ratio": 1.30, "vwap_ratio": 1.004, "ema20_r": 0.993, "ema50_r": 0.975, "ema200_r": 0.927},
    "JSWSTEEL":   {"adx": 32.0, "rsi14": 62.0, "macd_hist":  3.5, "volume_ratio": 1.60, "vwap_ratio": 1.007, "ema20_r": 0.990, "ema50_r": 0.971, "ema200_r": 0.920},
    "HINDALCO":   {"adx": 30.0, "rsi14": 60.0, "macd_hist":  3.0, "volume_ratio": 1.50, "vwap_ratio": 1.005, "ema20_r": 0.992, "ema50_r": 0.972, "ema200_r": 0.922},
    "SUNPHARMA":  {"adx": 30.0, "rsi14": 60.0, "macd_hist":  2.8, "volume_ratio": 1.45, "vwap_ratio": 1.005, "ema20_r": 0.991, "ema50_r": 0.972, "ema200_r": 0.923},
    "DRREDDY":    {"adx": 29.0, "rsi14": 58.0, "macd_hist":  2.5, "volume_ratio": 1.35, "vwap_ratio": 1.004, "ema20_r": 0.992, "ema50_r": 0.974, "ema200_r": 0.926},
    "CIPLA":      {"adx": 30.0, "rsi14": 60.0, "macd_hist":  2.8, "volume_ratio": 1.42, "vwap_ratio": 1.005, "ema20_r": 0.991, "ema50_r": 0.973, "ema200_r": 0.923},
    "BHARTIARTL": {"adx": 32.0, "rsi14": 63.0, "macd_hist":  3.5, "volume_ratio": 1.60, "vwap_ratio": 1.006, "ema20_r": 0.990, "ema50_r": 0.971, "ema200_r": 0.920},
    "MARUTI":     {"adx": 29.0, "rsi14": 57.0, "macd_hist":  2.2, "volume_ratio": 1.30, "vwap_ratio": 1.004, "ema20_r": 0.993, "ema50_r": 0.975, "ema200_r": 0.927},
    "M&M":        {"adx": 30.0, "rsi14": 59.0, "macd_hist":  2.8, "volume_ratio": 1.40, "vwap_ratio": 1.005, "ema20_r": 0.992, "ema50_r": 0.973, "ema200_r": 0.923},
    "BAJAJ-AUTO": {"adx": 30.0, "rsi14": 60.0, "macd_hist":  2.8, "volume_ratio": 1.40, "vwap_ratio": 1.005, "ema20_r": 0.991, "ema50_r": 0.972, "ema200_r": 0.923},
    "EICHERMOT":  {"adx": 29.0, "rsi14": 58.0, "macd_hist":  2.5, "volume_ratio": 1.35, "vwap_ratio": 1.004, "ema20_r": 0.992, "ema50_r": 0.974, "ema200_r": 0.926},
    "LT":         {"adx": 30.0, "rsi14": 60.0, "macd_hist":  2.8, "volume_ratio": 1.42, "vwap_ratio": 1.005, "ema20_r": 0.991, "ema50_r": 0.973, "ema200_r": 0.923},
    "ADANIPORTS": {"adx": 30.0, "rsi14": 59.0, "macd_hist":  2.5, "volume_ratio": 1.38, "vwap_ratio": 1.005, "ema20_r": 0.992, "ema50_r": 0.973, "ema200_r": 0.924},
    "SBILIFE":    {"adx": 29.0, "rsi14": 57.0, "macd_hist":  2.2, "volume_ratio": 1.32, "vwap_ratio": 1.004, "ema20_r": 0.993, "ema50_r": 0.975, "ema200_r": 0.927},
    "HDFCLIFE":   {"adx": 29.0, "rsi14": 57.0, "macd_hist":  2.0, "volume_ratio": 1.30, "vwap_ratio": 1.004, "ema20_r": 0.993, "ema50_r": 0.975, "ema200_r": 0.927},
    "TITAN":      {"adx": 30.0, "rsi14": 60.0, "macd_hist":  2.8, "volume_ratio": 1.42, "vwap_ratio": 1.005, "ema20_r": 0.991, "ema50_r": 0.973, "ema200_r": 0.923},
    "ULTRACEMCO": {"adx": 29.0, "rsi14": 57.0, "macd_hist":  2.2, "volume_ratio": 1.32, "vwap_ratio": 1.004, "ema20_r": 0.993, "ema50_r": 0.975, "ema200_r": 0.927},
    "GRASIM":     {"adx": 29.0, "rsi14": 57.0, "macd_hist":  2.2, "volume_ratio": 1.30, "vwap_ratio": 1.004, "ema20_r": 0.993, "ema50_r": 0.975, "ema200_r": 0.927},
    "NTPC":       {"adx": 31.0, "rsi14": 61.0, "macd_hist":  3.0, "volume_ratio": 1.50, "vwap_ratio": 1.006, "ema20_r": 0.991, "ema50_r": 0.972, "ema200_r": 0.921},
    "POWERGRID":  {"adx": 28.0, "rsi14": 54.0, "macd_hist":  1.5, "volume_ratio": 1.20, "vwap_ratio": 1.002, "ema20_r": 0.994, "ema50_r": 0.977, "ema200_r": 0.930},
    "SIEMENS":    {"adx": 30.0, "rsi14": 60.0, "macd_hist":  2.8, "volume_ratio": 1.40, "vwap_ratio": 1.005, "ema20_r": 0.991, "ema50_r": 0.973, "ema200_r": 0.924},
    "APOLLOHOSP": {"adx": 30.0, "rsi14": 60.0, "macd_hist":  2.8, "volume_ratio": 1.40, "vwap_ratio": 1.005, "ema20_r": 0.991, "ema50_r": 0.973, "ema200_r": 0.923},
    "DABUR":      {"adx": 28.0, "rsi14": 55.0, "macd_hist":  1.8, "volume_ratio": 1.28, "vwap_ratio": 1.003, "ema20_r": 0.993, "ema50_r": 0.976, "ema200_r": 0.929},
    # Neutral/weak setups — will be filtered out by gate
    "TCS":        {"adx": 19.0, "rsi14": 52.0, "macd_hist":  0.5, "volume_ratio": 0.90, "vwap_ratio": 1.000, "ema20_r": 0.999, "ema50_r": 0.985, "ema200_r": 0.940},
    "INFY":       {"adx": 22.0, "rsi14": 50.0, "macd_hist":  0.2, "volume_ratio": 1.00, "vwap_ratio": 1.000, "ema20_r": 0.998, "ema50_r": 0.988, "ema200_r": 0.945},
    "KOTAKBANK":  {"adx": 18.0, "rsi14": 42.0, "macd_hist": -1.5, "volume_ratio": 1.10, "vwap_ratio": 0.998, "ema20_r": 1.005, "ema50_r": 1.015, "ema200_r": 0.980},
    "BAJFINANCE": {"adx": 20.0, "rsi14": 40.0, "macd_hist": -2.0, "volume_ratio": 1.15, "vwap_ratio": 0.997, "ema20_r": 1.008, "ema50_r": 1.018, "ema200_r": 0.985},
    "HINDUNILVR": {"adx": 17.0, "rsi14": 38.0, "macd_hist": -2.5, "volume_ratio": 1.20, "vwap_ratio": 0.996, "ema20_r": 1.010, "ema50_r": 1.020, "ema200_r": 0.990},
    "NESTLEIND":  {"adx": 16.0, "rsi14": 44.0, "macd_hist": -1.0, "volume_ratio": 0.95, "vwap_ratio": 0.999, "ema20_r": 1.002, "ema50_r": 1.010, "ema200_r": 0.970},
    "BRITANNIA":  {"adx": 22.0, "rsi14": 48.0, "macd_hist":  0.8, "volume_ratio": 1.05, "vwap_ratio": 1.001, "ema20_r": 0.997, "ema50_r": 0.990, "ema200_r": 0.955},
    "ASIANPAINT": {"adx": 15.0, "rsi14": 36.0, "macd_hist": -3.0, "volume_ratio": 1.25, "vwap_ratio": 0.995, "ema20_r": 1.012, "ema50_r": 1.022, "ema200_r": 0.995},
    "ADANIENT":   {"adx": 20.0, "rsi14": 45.0, "macd_hist": -0.8, "volume_ratio": 1.10, "vwap_ratio": 0.998, "ema20_r": 1.004, "ema50_r": 1.012, "ema200_r": 0.975},
    "DIVISLAB":   {"adx": 18.0, "rsi14": 40.0, "macd_hist": -1.8, "volume_ratio": 1.12, "vwap_ratio": 0.997, "ema20_r": 1.007, "ema50_r": 1.016, "ema200_r": 0.982},
    "VEDL":       {"adx": 21.0, "rsi14": 47.0, "macd_hist":  0.5, "volume_ratio": 1.08, "vwap_ratio": 1.000, "ema20_r": 0.999, "ema50_r": 0.988, "ema200_r": 0.950},
    "INDUSINDBK": {"adx": 25.0, "rsi14": 52.0, "macd_hist":  1.2, "volume_ratio": 1.20, "vwap_ratio": 1.002, "ema20_r": 0.994, "ema50_r": 0.980, "ema200_r": 0.940},
    "BAJAJFINSV": {"adx": 24.0, "rsi14": 52.0, "macd_hist":  1.0, "volume_ratio": 1.18, "vwap_ratio": 1.002, "ema20_r": 0.994, "ema50_r": 0.980, "ema200_r": 0.942},
}

# ─────────────────────────────────────────────────────────────────────────────
#  SMART MONEY CONCEPTS (SMC) PROFILES
#  Includes: Market Structure (BOS / CHoCH), Liquidity Sweeps (SSL / BSL),
#  Price Inefficiencies (Unmitigated Order Blocks, Fair Value Gaps BISI / SIBI),
#  and Dealing Range pricing (Discount vs. Premium).
# ─────────────────────────────────────────────────────────────────────────────
def _build_smc_profiles() -> Dict[str, Dict[str, Any]]:
    profiles: Dict[str, Dict[str, Any]] = {}
    bullish_top_tier = {
        "RELIANCE", "ONGC", "BPCL", "COALINDIA", "SBIN", "HDFCBANK",
        "ICICIBANK", "AXISBANK", "TATAMOTORS", "TATASTEEL", "ITC",
        "WIPRO", "HCLTECH", "TECHM", "LTI", "JSWSTEEL", "HINDALCO",
        "SUNPHARMA", "DRREDDY", "CIPLA", "BHARTIARTL", "MARUTI", "M&M",
        "BAJAJ-AUTO", "EICHERMOT", "LT", "ADANIPORTS", "SBILIFE", "HDFCLIFE",
        "TITAN", "ULTRACEMCO", "GRASIM", "NTPC", "POWERGRID", "SIEMENS",
        "APOLLOHOSP", "DABUR"
    }

    bearish_tier = {
        "TCS", "KOTAKBANK", "BAJFINANCE", "HINDUNILVR", "ASIANPAINT",
        "NESTLEIND", "DIVISLAB"
    }

    for sym, cdata in NIFTY50_UNIVERSE.items():
        px = cdata.get("price", 2000.0)
        tp = TECHNICAL_PROFILES.get(sym, {})
        adx = tp.get("adx", 20.0)

        if sym in bullish_top_tier and adx >= 28.0:
            # Institutional Accumulation / Trend Continuation
            # Price swept SSL below swing low and has broken structure upwards (BULLISH_BOS)
            # Retesting unmitigated Bullish Order Block and filling BISI FVG in Discount
            swing_high = round(px * 1.035, 2)
            swing_low = round(px * 0.970, 2)
            bsl_price = round(px * 1.038, 2)
            ssl_price = round(px * 0.968, 2)
            range_high = round(px * 1.045, 2)
            range_low = round(px * 0.965, 2)
            ob_bottom = round(px * 0.992, 2)
            ob_top = round(px * 1.004, 2)
            fvg_bottom = round(px * 0.995, 2)
            fvg_top = round(px * 1.005, 2)

            profiles[sym] = {
                "market_structure": "BULLISH_BOS",
                "swing_high": swing_high,
                "swing_low": swing_low,
                "liquidity_event": "SSL_SWEPT",
                "bsl_price": bsl_price,
                "ssl_price": ssl_price,
                "dealing_range_high": range_high,
                "dealing_range_low": range_low,
                "order_blocks": [
                    {
                        "ob_type": "BULLISH_OB",
                        "top_price": ob_top,
                        "bottom_price": ob_bottom,
                        "midpoint": round((ob_top + ob_bottom) / 2.0, 2),
                        "mitigated": False,
                        "volume_displacement": 1.90,
                        "is_price_in_zone": True
                    }
                ],
                "fair_value_gaps": [
                    {
                        "fvg_type": "BISI",
                        "top_price": fvg_top,
                        "bottom_price": fvg_bottom,
                        "consequent_encroachment": round((fvg_top + fvg_bottom) / 2.0, 2),
                        "status": "PARTIALLY_FILLED",
                        "is_price_in_fvg": True
                    }
                ]
            }
        elif sym in bearish_tier:
            # Institutional Distribution / Breakdown
            # Price swept BSL and broke structure downwards (BEARISH_BOS)
            # Operating in Premium zone tapping Bearish OB
            swing_high = round(px * 1.025, 2)
            swing_low = round(px * 0.960, 2)
            bsl_price = round(px * 1.028, 2)
            ssl_price = round(px * 0.955, 2)
            range_high = round(px * 1.035, 2)
            range_low = round(px * 0.950, 2)
            ob_bottom = round(px * 0.996, 2)
            ob_top = round(px * 1.008, 2)
            fvg_bottom = round(px * 0.994, 2)
            fvg_top = round(px * 1.004, 2)

            profiles[sym] = {
                "market_structure": "BEARISH_BOS",
                "swing_high": swing_high,
                "swing_low": swing_low,
                "liquidity_event": "BSL_SWEPT",
                "bsl_price": bsl_price,
                "ssl_price": ssl_price,
                "dealing_range_high": range_high,
                "dealing_range_low": range_low,
                "order_blocks": [
                    {
                        "ob_type": "BEARISH_OB",
                        "top_price": ob_top,
                        "bottom_price": ob_bottom,
                        "midpoint": round((ob_top + ob_bottom) / 2.0, 2),
                        "mitigated": False,
                        "volume_displacement": 1.65,
                        "is_price_in_zone": True
                    }
                ],
                "fair_value_gaps": [
                    {
                        "fvg_type": "SIBI",
                        "top_price": fvg_top,
                        "bottom_price": fvg_bottom,
                        "consequent_encroachment": round((fvg_top + fvg_bottom) / 2.0, 2),
                        "status": "UNFILLED",
                        "is_price_in_fvg": True
                    }
                ]
            }
        else:
            # Internal Consolidation / Ranging
            swing_high = round(px * 1.020, 2)
            swing_low = round(px * 0.980, 2)
            profiles[sym] = {
                "market_structure": "RANGING_CONSOLIDATION",
                "swing_high": swing_high,
                "swing_low": swing_low,
                "liquidity_event": "NEUTRAL",
                "bsl_price": swing_high,
                "ssl_price": swing_low,
                "dealing_range_high": round(px * 1.03, 2),
                "dealing_range_low": round(px * 0.97, 2),
                "order_blocks": [],
                "fair_value_gaps": []
            }

    return profiles

SMC_PROFILES: Dict[str, Dict[str, Any]] = _build_smc_profiles()

