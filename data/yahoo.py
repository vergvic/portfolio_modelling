"""
yfinance wrapper.

Key constraints discovered:
- yfinance ≥ 0.2.x requires its own curl_cffi session.  Do NOT pass a
  requests.Session — yfinance will reject it and return empty data.
- Let yfinance manage its own session entirely (no session= argument).
- Wrap each call in a daemon thread + queue.Queue for a hard timeout.
  This only works correctly when called from a QThread that overrides
  run() directly — do NOT call from a slot dispatched via the Qt event
  loop (moveToThread pattern), which would deadlock on queue.get().
"""
import logging
import threading
import queue
from datetime import date, datetime, timedelta

import pandas as pd
import yfinance as yf

from config import WEEKLY_WINDOW_YEARS, FETCH_TIMEOUT_SECONDS

log = logging.getLogger(__name__)

_INTERVAL = {"weekly": "1wk", "monthly": "1mo"}


# ---------------------------------------------------------------------------
# Hard-timeout wrapper
# ---------------------------------------------------------------------------

def _download(timeout: int = FETCH_TIMEOUT_SECONDS, **kwargs) -> pd.DataFrame:
    """
    Run yf.download(**kwargs) in a daemon thread with a hard timeout.

    - No session= argument: yfinance manages its own curl_cffi session.
    - daemon=True: hung threads are killed on process exit.
    - queue.get(timeout=N): genuine hard cutoff independent of Qt.

    Safe to call from QThread.run() when QThread is subclassed directly.
    NOT safe to call when run() is invoked as a Qt slot (moveToThread pattern).
    """
    result_q: queue.Queue = queue.Queue()

    def _worker():
        try:
            df = yf.download(**kwargs)
            result_q.put(df)
        except Exception as exc:
            result_q.put(exc)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    try:
        result = result_q.get(timeout=timeout)
    except queue.Empty:
        log.warning("yf.download timed out after %ds  kwargs=%s", timeout,
                    {k: v for k, v in kwargs.items() if k in ("tickers", "period", "interval")})
        return pd.DataFrame()

    if isinstance(result, Exception):
        log.error("yf.download raised: %s", result)
        return pd.DataFrame()

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_ticker(ticker: str) -> bool:
    """Quick sanity-check — download 5 days; True if non-empty."""
    ticker = ticker.upper().strip()
    raw = _download(
        timeout=20,
        tickers=ticker,
        period="5d",
        interval="1d",
        auto_adjust=False,
        progress=False,
    )
    return not raw.empty


def fetch_full_history(ticker: str, frequency: str) -> pd.DataFrame:
    """
    Fetch the full price history for a given frequency.

    weekly  → last WEEKLY_WINDOW_YEARS years
    monthly → max available history

    Returns empty DataFrame on any failure or timeout.
    """
    ticker = ticker.upper().strip()
    interval = _INTERVAL[frequency]

    if frequency == "weekly":
        start = _years_ago(WEEKLY_WINDOW_YEARS)
        raw = _download(
            tickers=ticker,
            start=start.strftime("%Y-%m-%d"),
            interval=interval,
            auto_adjust=False,
            progress=False,
        )
    else:
        raw = _download(
            tickers=ticker,
            period="max",
            interval=interval,
            auto_adjust=False,
            progress=False,
        )

    return _normalise(raw, ticker)


def fetch_delta(ticker: str, frequency: str, from_date) -> pd.DataFrame:
    """Fetch only rows newer than from_date."""
    ticker = ticker.upper().strip()
    interval = _INTERVAL[frequency]

    if isinstance(from_date, str):
        from_date = date.fromisoformat(from_date[:10])
    elif isinstance(from_date, datetime):
        from_date = from_date.date()

    start_str = (from_date - timedelta(days=1)).strftime("%Y-%m-%d")
    end_str   = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    raw = _download(
        tickers=ticker,
        start=start_str,
        end=end_str,
        interval=interval,
        auto_adjust=False,
        progress=False,
    )
    return _normalise(raw, ticker)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _years_ago(n: int) -> date:
    today = date.today()
    return today.replace(year=today.year - n)


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "open", "high", "low", "close", "adj_close"])


def _normalise(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if raw is None or raw.empty:
        return _empty_df()

    df = raw.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [str(c).lower().strip().replace(" ", "_") for c in df.columns]

    for col in list(df.columns):
        if col != "adj_close" and "adj" in col and "close" in col:
            df = df.rename(columns={col: "adj_close"})
            break

    if "adj_close" not in df.columns and "close" in df.columns:
        df["adj_close"] = df["close"]

    if "date" not in df.columns:
        df = df.reset_index()
        first = df.columns[0]
        if first != "date":
            df = df.rename(columns={first: "date"})

    needed = ["date", "open", "high", "low", "close", "adj_close"]
    df = df[[c for c in needed if c in df.columns]].copy()

    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)

    if "adj_close" in df.columns:
        df = df.dropna(subset=["adj_close"])

    df = df.sort_values("date").reset_index(drop=True)
    log.debug("_normalise(%s): %d rows", ticker, len(df))
    return df
