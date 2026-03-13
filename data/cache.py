"""
Cache orchestration layer.

Rules (from architecture spec):
1. On ticker add → fetch full history (both weekly and monthly), write to DB
2. On app launch → for each portfolio ticker, check last_fetched; if stale, fetch delta
3. On tab switch / compute → read from DB, never hit Yahoo (unless cache miss)
4. SPY is always cached alongside portfolio tickers
"""
import logging
from datetime import datetime, timedelta, timezone, date

import pandas as pd

from config import MARKET_PROXY, CACHE_TTL_HOURS
import data.db as db
import data.yahoo as yahoo

log = logging.getLogger(__name__)

_FREQUENCIES = ("weekly", "monthly")


# ---------------------------------------------------------------------------
# On ticker add
# ---------------------------------------------------------------------------

def ensure_ticker_cached(ticker: str) -> bool:
    """
    Fetch full price history for a ticker (both weekly and monthly) and
    persist it.  Also ensures SPY is cached (skipped if already fresh).

    Returns True if useful data was obtained, False if all fetches returned
    empty (likely an invalid ticker — caller should remove the position).
    """
    ticker = ticker.upper().strip()
    _fetch_and_store_full(ticker)

    # Only re-fetch SPY if it isn't already fresh
    if ticker != MARKET_PROXY and _needs_refresh(MARKET_PROXY):
        _fetch_and_store_full(MARKET_PROXY)

    # Check that we actually got data for the ticker
    meta = db.get_cache_metadata(ticker, "weekly")
    return meta is not None


def _fetch_and_store_full(ticker: str) -> None:
    for freq in _FREQUENCIES:
        log.info("Fetching full %s history for %s…", freq, ticker)
        df = yahoo.fetch_full_history(ticker, freq)
        if df.empty:
            log.warning("No %s data returned for %s", freq, ticker)
            continue
        db.upsert_prices(ticker, freq, df)
        _update_metadata(ticker, freq, df)
        log.info("Cached %d %s rows for %s", len(df), freq, ticker)


# ---------------------------------------------------------------------------
# On app launch — stale check and delta fetch
# ---------------------------------------------------------------------------

def refresh_stale_tickers(tickers: list[str]) -> dict[str, str]:
    """
    For each ticker in *tickers* (plus SPY), check cache freshness.
    Fetch delta data for any stale entries.

    Returns a dict {ticker: status} where status is 'ok', 'refreshed', or 'error'.
    """
    all_tickers = list(dict.fromkeys(tickers + [MARKET_PROXY]))
    results: dict[str, str] = {}

    for ticker in all_tickers:
        try:
            status = _refresh_ticker_if_stale(ticker)
            results[ticker] = status
        except Exception as exc:
            log.error("Error refreshing %s: %s", ticker, exc)
            results[ticker] = "error"

    return results


def _refresh_ticker_if_stale(ticker: str) -> str:
    for freq in _FREQUENCIES:
        meta = db.get_cache_metadata(ticker, freq)

        if meta is None:
            # No cache at all — do a full fetch
            log.info("No cache found for %s/%s, fetching full history", ticker, freq)
            df = yahoo.fetch_full_history(ticker, freq)
            if not df.empty:
                db.upsert_prices(ticker, freq, df)
                _update_metadata(ticker, freq, df)
            continue

        last_fetched = datetime.fromisoformat(meta["last_fetched"])
        if last_fetched.tzinfo is None:
            last_fetched = last_fetched.replace(tzinfo=timezone.utc)

        age_hours = (datetime.now(tz=timezone.utc) - last_fetched).total_seconds() / 3600

        if age_hours <= _effective_ttl():
            log.debug("%s/%s cache is fresh (%.1fh old)", ticker, freq, age_hours)
            continue

        # Stale — fetch delta from data_end
        data_end = meta.get("data_end")
        if data_end:
            log.info("Delta-fetching %s/%s from %s", ticker, freq, data_end)
            df = yahoo.fetch_delta(ticker, freq, data_end)
        else:
            log.info("Full re-fetch for %s/%s", ticker, freq)
            df = yahoo.fetch_full_history(ticker, freq)

        if not df.empty:
            db.upsert_prices(ticker, freq, df)
            _update_metadata(ticker, freq, df)

    return "refreshed"


def _needs_refresh(ticker: str) -> bool:
    """Return True if either frequency for this ticker is missing or stale."""
    for freq in _FREQUENCIES:
        meta = db.get_cache_metadata(ticker, freq)
        if meta is None:
            return True
        last_fetched = datetime.fromisoformat(meta["last_fetched"])
        if last_fetched.tzinfo is None:
            last_fetched = last_fetched.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(tz=timezone.utc) - last_fetched).total_seconds() / 3600
        if age_hours > _effective_ttl():
            return True
    return False


def _effective_ttl() -> float:
    """
    Extend the TTL over weekends — markets are closed, no new data expected.
    Friday 4pm → Monday 9am is ~65 hours.  Return 72h TTL on weekends.
    """
    today = date.today()
    if today.weekday() in (5, 6):   # Saturday or Sunday
        return 72.0
    return float(CACHE_TTL_HOURS)


# ---------------------------------------------------------------------------
# Read from cache (called by compute layer)
# ---------------------------------------------------------------------------

def get_prices(ticker: str, frequency: str) -> pd.DataFrame:
    """
    Return cached price DataFrame for a ticker.
    Never hits Yahoo Finance — fails gracefully with an empty DataFrame.

    Columns: date (datetime64), open, high, low, close, adj_close
    """
    return db.get_prices(ticker, frequency)


# ---------------------------------------------------------------------------
# Manual refresh (triggered by UI refresh button)
# ---------------------------------------------------------------------------

def force_refresh_all(tickers: list[str]) -> dict[str, str]:
    """
    Force a full re-fetch of all tickers regardless of cache age.
    Returns status dict.
    """
    all_tickers = list(dict.fromkeys(tickers + [MARKET_PROXY]))
    results: dict[str, str] = {}

    for ticker in all_tickers:
        try:
            _fetch_and_store_full(ticker)
            results[ticker] = "refreshed"
        except Exception as exc:
            log.error("force_refresh %s: %s", ticker, exc)
            results[ticker] = "error"

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _update_metadata(ticker: str, freq: str, df: pd.DataFrame) -> None:
    dates = pd.to_datetime(df["date"])
    db.upsert_cache_metadata(
        ticker=ticker,
        frequency=freq,
        last_fetched=datetime.now(tz=timezone.utc),
        data_start=dates.min().date() if not dates.empty else None,
        data_end=dates.max().date() if not dates.empty else None,
    )
