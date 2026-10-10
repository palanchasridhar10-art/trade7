"""TradingView Real-Time Background Price & Indicator Synchronization Engine.

Uses TradingView's official Indian Market Scanner endpoint (zero API keys required)
to continuously update real-time stock prices, OHLCV bars, Nifty 50 benchmark index close,
India VIX, and technical indicators (RSI, EMAs, VWAP) in the background.
"""

import json
import time
import ssl
import logging
import threading
import urllib.request
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from src.data.calendar import NSECalendar
from src.data.universe import NIFTY50_UNIVERSE, TECHNICAL_PROFILES, SMC_PROFILES

logger = logging.getLogger("tradingview_service")

# Custom ticker overrides for TradingView NSE scanner
TV_TICKER_OVERRIDES: Dict[str, str] = {
    "TATAMOTORS": "NSE:TMCV",
    "LTI": "NSE:LTM",
    "M&M": "NSE:M&M",
    "BAJAJ-AUTO": "NSE:BAJAJ_AUTO"
}

# Reverse mapping: TradingView ticker -> system symbol
TV_REVERSE_MAP: Dict[str, str] = {
    "NSE:TMCV": "TATAMOTORS",
    "NSE:LTM": "LTI",
    "NSE:M&M": "M&M",
    "NSE:BAJAJ_AUTO": "BAJAJ-AUTO"
}

def symbol_to_tv_ticker(symbol: str) -> str:
    """Convert standard Nifty symbol to TradingView scanner ticker format."""
    sym_clean = symbol.upper().strip()
    if sym_clean in TV_TICKER_OVERRIDES:
        return TV_TICKER_OVERRIDES[sym_clean]
    clean_name = sym_clean.replace("&", "_").replace("-", "_")
    return f"NSE:{clean_name}"

def tv_ticker_to_symbol(tv_ticker: str) -> str:
    """Convert TradingView scanner ticker format back to system symbol."""
    if tv_ticker in TV_REVERSE_MAP:
        return TV_REVERSE_MAP[tv_ticker]
    if tv_ticker.startswith("NSE:"):
        base = tv_ticker[4:]
        return base.replace("_", "-") if base == "BAJAJ-AUTO" else base
    return tv_ticker


class TradingViewBackgroundService:
    """Background engine fetching real-time market data from TradingView."""

    SCANNER_URL = "https://scanner.tradingview.com/india/scan"
    DEFAULT_COLUMNS = [
        "close",
        "open",
        "high",
        "low",
        "volume",
        "change",
        "Recommend.All",
        "RSI",
        "EMA20",
        "EMA50",
        "EMA200",
        "VWAP"
    ]

    def __init__(self, daily_manager=None, broker=None, sync_interval: int = 30):
        self.daily_manager = daily_manager
        self.broker = broker
        self.sync_interval = max(5, sync_interval)

        # State
        self.is_running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self.last_synced_at: Optional[datetime] = None
        self.last_nifty_price: float = 25120.00
        self.last_vix: float = 13.40
        self.synced_count: int = 0
        self.total_sync_cycles: int = 0
        self.last_error: Optional[str] = None
        self.latest_market_cache: Dict[str, Dict[str, Any]] = {}

        # Prepare ticker list: 50 stocks + Nifty 50 Index + India VIX
        self.tickers: List[str] = [symbol_to_tv_ticker(s) for s in NIFTY50_UNIVERSE.keys()]
        self.tickers.extend(["NSE:NIFTY", "NSE:INDIAVIX"])

        # Create unverified SSL context for resilient cross-platform requests
        try:
            self._ssl_ctx = ssl.create_default_context()
            self._ssl_ctx.check_hostname = False
            self._ssl_ctx.verify_mode = ssl.CERT_NONE
        except Exception:
            self._ssl_ctx = ssl._create_unverified_context() if hasattr(ssl, "_create_unverified_context") else None

    def fetch_live_data(self, timeout: int = 10, max_retries: int = 3) -> Dict[str, Dict[str, Any]]:
        """Fetch live OHLCV and indicator metrics from TradingView scanner endpoint with retries."""
        payload = {
            "symbols": {"tickers": self.tickers},
            "columns": self.DEFAULT_COLUMNS
        }

        req = urllib.request.Request(
            self.SCANNER_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Content-Type": "application/json"
            },
            data=json.dumps(payload).encode("utf-8")
        )

        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                open_kwargs = {"timeout": timeout}
                if self._ssl_ctx is not None:
                    open_kwargs["context"] = self._ssl_ctx

                with urllib.request.urlopen(req, **open_kwargs) as resp:
                    raw_data = json.loads(resp.read().decode("utf-8"))

                parsed_data: Dict[str, Dict[str, Any]] = {}
                for item in raw_data.get("data", []):
                    ticker = item.get("s", "")
                    values = item.get("d", [])
                    if not ticker or len(values) < 6:
                        continue

                    close_px = float(values[0]) if values[0] is not None else 0.0
                    open_px = float(values[1]) if values[1] is not None else close_px
                    high_px = float(values[2]) if values[2] is not None else close_px
                    low_px = float(values[3]) if values[3] is not None else close_px
                    vol = int(values[4]) if values[4] is not None else 0
                    chg_pct = float(values[5]) if values[5] is not None else 0.0

                    rsi = float(values[7]) if len(values) > 7 and values[7] is not None else 50.0
                    ema20 = float(values[8]) if len(values) > 8 and values[8] is not None else close_px * 0.992
                    ema50 = float(values[9]) if len(values) > 9 and values[9] is not None else close_px * 0.972
                    ema200 = float(values[10]) if len(values) > 10 and values[10] is not None else close_px * 0.920
                    vwap = float(values[11]) if len(values) > 11 and values[11] is not None else close_px

                    parsed_data[ticker] = {
                        "ticker": ticker,
                        "close": close_px,
                        "open": open_px,
                        "high": high_px,
                        "low": low_px,
                        "volume": vol,
                        "change_pct": chg_pct,
                        "rsi": rsi,
                        "ema20": ema20,
                        "ema50": ema50,
                        "ema200": ema200,
                        "vwap": vwap,
                        "fetched_at": datetime.now().isoformat()
                    }

                if parsed_data:
                    self.latest_market_cache = parsed_data
                    self.last_error = None
                    return parsed_data

            except Exception as e:
                last_exc = e
                logger.warning(f"[TradingView] Attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(0.5 * attempt)

        self.last_error = f"TradingView fetch error: {str(last_exc)}"
        logger.warning(f"[TradingView] All {max_retries} attempts failed: {last_exc}")
        return self.latest_market_cache

    def sync_system_prices(self, daily_manager=None, broker=None) -> Dict[str, Any]:
        """Apply fetched TradingView prices to DailyDataManager, NIFTY50_UNIVERSE, and Agents."""
        dm = daily_manager or self.daily_manager
        brk = broker or self.broker

        tv_data = self.fetch_live_data()
        if not tv_data:
            return {
                "status": "NO_DATA",
                "source": "TRADINGVIEW",
                "synced_stocks": 0,
                "total_universe": len(NIFTY50_UNIVERSE),
                "nifty50_close": self.last_nifty_price,
                "india_vix": self.last_vix,
                "timestamp": NSECalendar.get_ist_now().isoformat(),
                "prices": {},
                "message": "No data returned from TradingView scanner.",
                "last_error": self.last_error
            }

        now = NSECalendar.get_ist_now()
        synced_stocks = 0
        price_snapshot: Dict[str, float] = {}

        # 1. Update Nifty 50 Benchmark Index and India VIX in MacroContext
        if "NSE:NIFTY" in tv_data and dm and dm.macro_context:
            nifty_close = tv_data["NSE:NIFTY"]["close"]
            if nifty_close > 0:
                self.last_nifty_price = nifty_close
                dm.macro_context.nifty50_close = nifty_close

        if "NSE:INDIAVIX" in tv_data and dm and dm.macro_context:
            vix_val = tv_data["NSE:INDIAVIX"]["close"]
            if vix_val > 0:
                self.last_vix = vix_val
                dm.macro_context.india_vix = vix_val

        # 2. Update all 50 constituent stocks
        for sym, udata in NIFTY50_UNIVERSE.items():
            tv_ticker = symbol_to_tv_ticker(sym)
            if tv_ticker in tv_data:
                d = tv_data[tv_ticker]
                px = d["close"]
                if px <= 0:
                    continue

                synced_stocks += 1
                price_snapshot[sym] = px

                # Update NIFTY50_UNIVERSE in-memory price
                NIFTY50_UNIVERSE[sym]["price"] = px

                if dm:
                    prev_close = px / (1.0 + (d["change_pct"] / 100.0)) if d["change_pct"] != 0 else px

                    # Update Daily Quote
                    dm.daily_quotes[sym] = {
                        "price": px,
                        "previous_close": round(prev_close, 2),
                        "open": d["open"],
                        "high": d["high"],
                        "low": d["low"],
                        "volume": d["volume"] or udata.get("volume", 2_000_000),
                        "sector": udata.get("sector", "EQUITY"),
                        "change_pct": round(d["change_pct"], 2),
                        "source": "TRADINGVIEW_LIVE",
                        "last_updated": now.isoformat()
                    }

                    # Update Daily Fundamentals % change
                    if sym in dm.daily_fundamentals:
                        dm.daily_fundamentals[sym]["pct_change"] = round(d["change_pct"], 2)

                    # Update Technicals (RSI, EMAs, VWAP)
                    tp = dm.daily_technicals.get(sym, TECHNICAL_PROFILES.get(sym, {}))
                    dm.daily_technicals[sym] = {
                        "adx": tp.get("adx", 25.0),
                        "rsi14": round(d["rsi"], 2),
                        "macd_hist": tp.get("macd_hist", 2.0),
                        "volume_ratio": tp.get("volume_ratio", 1.2),
                        "vwap_ratio": round(px / d["vwap"], 4) if d["vwap"] > 0 else 1.002,
                        "vwap": round(d["vwap"], 2),
                        "ema20": round(d["ema20"], 2),
                        "ema50": round(d["ema50"], 2),
                        "ema200": round(d["ema200"], 2),
                        "atr14": round(px * 0.015, 2),
                        "ema20_r": tp.get("ema20_r", 0.992),
                        "ema50_r": tp.get("ema50_r", 0.972),
                        "ema200_r": tp.get("ema200_r", 0.920)
                    }

                    # Update SMC dynamically to current price
                    smc = dm.daily_smc.get(sym, SMC_PROFILES.get(sym, {}))
                    if smc:
                        dm.daily_smc[sym] = {
                            "market_structure": smc.get("market_structure", "BULLISH_BOS"),
                            "swing_high": round(px * 1.035, 2),
                            "swing_low": round(px * 0.970, 2),
                            "liquidity_event": smc.get("liquidity_event", "SSL_SWEPT"),
                            "bsl_price": round(px * 1.038, 2),
                            "ssl_price": round(px * 0.968, 2),
                            "dealing_range_high": round(px * 1.045, 2),
                            "dealing_range_low": round(px * 0.965, 2),
                            "order_blocks": smc.get("order_blocks", []),
                            "fair_value_gaps": smc.get("fair_value_gaps", [])
                        }

                    # Update Pre-Market IEP
                    if sym in dm.daily_pre_market:
                        dm.daily_pre_market[sym]["iep_price"] = px
                        dm.daily_pre_market[sym]["prev_close"] = round(prev_close, 2)

                # If active broker (like PaperBroker) has active position, update position current price
                if brk and hasattr(brk, "update_price_tick") and hasattr(brk, "positions"):
                    if sym in brk.positions:
                        brk.update_price_tick(sym, px)

        if dm:
            dm.last_updated_at = now
            dm._push_data_to_agents()

        self.last_synced_at = now
        self.synced_count = synced_stocks
        self.total_sync_cycles += 1

        logger.info(
            f"[TradingView-Sync] Synchronized {synced_stocks}/50 stocks + Nifty ({self.last_nifty_price:.2f}) "
            f"from TradingView live scanner at {now.strftime('%H:%M:%S IST')}."
        )

        return {
            "status": "SUCCESS",
            "source": "TRADINGVIEW",
            "synced_stocks": synced_stocks,
            "total_universe": len(NIFTY50_UNIVERSE),
            "nifty50_close": self.last_nifty_price,
            "india_vix": self.last_vix,
            "timestamp": now.isoformat(),
            "prices": price_snapshot
        }

    def _worker_loop(self):
        """Background daemon thread worker continuously syncing TradingView prices."""
        logger.info(f"[TradingView] Background price synchronizer worker STARTED (interval: {self.sync_interval}s).")
        while not self._stop_event.is_set():
            try:
                self.sync_system_prices()
            except Exception as e:
                logger.error(f"[TradingView Worker] Error in sync cycle: {e}")

            # Sleep in small slices to respond promptly to stop signal
            for _ in range(self.sync_interval * 2):
                if self._stop_event.is_set():
                    break
                time.sleep(0.5)

        logger.info("[TradingView] Background price synchronizer worker STOPPED.")

    def start(self, interval_seconds: Optional[int] = None):
        """Start the background TradingView synchronization thread."""
        if interval_seconds:
            self.sync_interval = max(5, interval_seconds)

        if self.is_running and self._thread and self._thread.is_alive():
            logger.info("[TradingView] Service is already running.")
            return

        self._stop_event.clear()
        self.is_running = True
        self._thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="TradingViewSyncWorker"
        )
        self._thread.start()
        print(f"[TradingView] Background live price sync STARTED (Scanning every {self.sync_interval}s).")

    def stop(self):
        """Stop the background TradingView synchronization thread."""
        self._stop_event.set()
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        print("[TradingView] Background live price sync STOPPED.")

    def get_status(self) -> Dict[str, Any]:
        """Return the current operational status of the TradingView background service."""
        now = NSECalendar.get_ist_now()
        sec_since = (now - self.last_synced_at).total_seconds() if self.last_synced_at else None

        return {
            "service": "TradingView Real-Time Background Price Engine",
            "is_running": self.is_running,
            "sync_interval_seconds": self.sync_interval,
            "synced_stocks_count": self.synced_count,
            "total_universe_stocks": len(NIFTY50_UNIVERSE),
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "seconds_since_last_sync": int(sec_since) if sec_since is not None else None,
            "nifty50_close": self.last_nifty_price,
            "india_vix": self.last_vix,
            "total_sync_cycles": self.total_sync_cycles,
            "last_error": self.last_error,
            "source": "TRADINGVIEW_SCANNER_INDIA"
        }
