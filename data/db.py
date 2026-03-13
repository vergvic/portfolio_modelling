"""
SQLite persistence layer.

Responsibilities:
- Create/open the database file and initialise schema
- CRUD for the `portfolio` table (user positions)
- CRUD for `price_cache` and `cache_metadata` tables
"""
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

import pandas as pd

from config import DB_DIR, DB_PATH

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _ensure_dir() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    """Context-managed SQLite connection with WAL mode for concurrency."""
    _ensure_dir()
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS portfolio (
    ticker        TEXT PRIMARY KEY,
    side          TEXT NOT NULL CHECK(side IN ('long', 'short')),
    dollar_amount REAL NOT NULL CHECK(dollar_amount > 0)
);

CREATE TABLE IF NOT EXISTS price_cache (
    ticker    TEXT    NOT NULL,
    date      DATE    NOT NULL,
    open      REAL,
    high      REAL,
    low       REAL,
    close     REAL,
    adj_close REAL,
    frequency TEXT    NOT NULL CHECK(frequency IN ('weekly', 'monthly')),
    PRIMARY KEY (ticker, date, frequency)
);

CREATE TABLE IF NOT EXISTS cache_metadata (
    ticker       TEXT     NOT NULL,
    frequency    TEXT     NOT NULL CHECK(frequency IN ('weekly', 'monthly')),
    last_fetched DATETIME NOT NULL,
    data_start   DATE,
    data_end     DATE,
    PRIMARY KEY (ticker, frequency)
);
"""


def init_db() -> None:
    """Create schema if it does not exist.  Safe to call on every launch."""
    _ensure_dir()
    with get_connection() as conn:
        conn.executescript(_SCHEMA_SQL)
    log.info("Database initialised at %s", DB_PATH)


# ---------------------------------------------------------------------------
# Portfolio CRUD
# ---------------------------------------------------------------------------

def add_position(ticker: str, side: str, dollar_amount: float) -> None:
    """Insert or replace a position in the portfolio."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO portfolio (ticker, side, dollar_amount) VALUES (?, ?, ?)",
            (ticker, side, dollar_amount),
        )
    log.debug("Position added/updated: %s %s $%.0f", ticker, side, dollar_amount)


def remove_position(ticker: str) -> None:
    """Delete a position (and its cache data) from the portfolio."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        conn.execute("DELETE FROM portfolio WHERE ticker = ?", (ticker,))
    log.debug("Position removed: %s", ticker)


def get_portfolio() -> list[dict]:
    """Return all positions as a list of dicts with keys: ticker, side, dollar_amount."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT ticker, side, dollar_amount FROM portfolio ORDER BY dollar_amount DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_tickers() -> list[str]:
    """Return just the ticker symbols in the portfolio."""
    return [r["ticker"] for r in get_portfolio()]


# ---------------------------------------------------------------------------
# Price cache CRUD
# ---------------------------------------------------------------------------

def upsert_prices(ticker: str, frequency: str, df: pd.DataFrame) -> None:
    """
    Bulk insert/replace price rows.

    df must have columns: date, open, high, low, close, adj_close
    The `date` column should be a date string 'YYYY-MM-DD' or datetime.
    """
    if df.empty:
        return
    ticker = ticker.upper().strip()
    rows = []
    for _, row in df.iterrows():
        date_str = str(row["date"])[:10]
        rows.append((
            ticker,
            date_str,
            _f(row.get("open")),
            _f(row.get("high")),
            _f(row.get("low")),
            _f(row.get("close")),
            _f(row.get("adj_close")),
            frequency,
        ))
    with get_connection() as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO price_cache
               (ticker, date, open, high, low, close, adj_close, frequency)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
    log.debug("Upserted %d rows for %s/%s", len(rows), ticker, frequency)


def get_prices(ticker: str, frequency: str) -> pd.DataFrame:
    """
    Retrieve cached price data as a DataFrame.

    Returns columns: date (datetime64), open, high, low, close, adj_close
    Sorted ascending by date.
    """
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT date, open, high, low, close, adj_close
               FROM price_cache
               WHERE ticker = ? AND frequency = ?
               ORDER BY date ASC""",
            (ticker, frequency),
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "adj_close"])
    df = pd.DataFrame([dict(r) for r in rows])
    df["date"] = pd.to_datetime(df["date"])
    return df


# ---------------------------------------------------------------------------
# Cache metadata CRUD
# ---------------------------------------------------------------------------

def upsert_cache_metadata(
    ticker: str,
    frequency: str,
    last_fetched: datetime,
    data_start,
    data_end,
) -> None:
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO cache_metadata
               (ticker, frequency, last_fetched, data_start, data_end)
               VALUES (?, ?, ?, ?, ?)""",
            (
                ticker,
                frequency,
                last_fetched.isoformat(),
                str(data_start)[:10] if data_start is not None else None,
                str(data_end)[:10] if data_end is not None else None,
            ),
        )


def get_cache_metadata(ticker: str, frequency: str) -> dict | None:
    """Return cache metadata dict or None if not found."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM cache_metadata WHERE ticker = ? AND frequency = ?",
            (ticker, frequency),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def delete_ticker_cache(ticker: str) -> None:
    """Remove all cached price data and metadata for a ticker."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        conn.execute("DELETE FROM price_cache WHERE ticker = ?", (ticker,))
        conn.execute("DELETE FROM cache_metadata WHERE ticker = ?", (ticker,))
    log.debug("Cache deleted for %s", ticker)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _f(val) -> float | None:
    """Coerce a value to float, returning None for NaN/None."""
    try:
        v = float(val)
        import math
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None
