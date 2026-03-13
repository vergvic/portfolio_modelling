"""
Return series calculations.

All functions are pure — they take a price DataFrame and return a pd.Series
or pd.DataFrame indexed by date.  No DB or UI imports.

Return formulas (from architecture spec):
  Close-to-close : (adj_close_t / adj_close_t-1) - 1
  High-to-Low    : (high_t - low_t) / low_t          (intra-period, no shift)
"""
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Per-ticker return series
# ---------------------------------------------------------------------------

def weekly_cc_returns(price_df: pd.DataFrame) -> pd.Series:
    """
    Weekly close-to-close returns from a weekly price DataFrame.

    price_df must have columns: date (datetime64 or string), adj_close
    Returns a pd.Series indexed by date, named 'returns', first row dropped.
    """
    df = _prep(price_df)
    r = (df["adj_close"] / df["adj_close"].shift(1)) - 1
    r = r.dropna()
    r.name = "returns"
    return r


def monthly_cc_returns(price_df: pd.DataFrame) -> pd.Series:
    """Monthly close-to-close returns.  Same formula as weekly."""
    df = _prep(price_df)
    r = (df["adj_close"] / df["adj_close"].shift(1)) - 1
    r = r.dropna()
    r.name = "returns"
    return r


def monthly_hl_returns(price_df: pd.DataFrame) -> pd.Series:
    """
    Monthly high-to-low returns: (high - low) / low.
    Intra-period — no shift.  Measures the within-period range.
    """
    df = _prep(price_df)
    if "high" not in df.columns or "low" not in df.columns:
        raise KeyError("price_df must contain 'high' and 'low' columns")
    r = (df["high"] - df["low"]) / df["low"]
    r = r.dropna()
    r.name = "returns"
    return r


# ---------------------------------------------------------------------------
# Alignment utility
# ---------------------------------------------------------------------------

def align_returns(*series: pd.Series) -> pd.DataFrame:
    """
    Inner-join multiple return Series on their date index.

    Each series should be indexed by datetime64 date values.
    Returns a DataFrame where each column is one ticker's aligned returns.
    Only dates present in ALL series are retained.

    Usage:
        df = align_returns(spy_ret, aapl_ret, msft_ret)
        # df.columns == ['SPY', 'AAPL', 'MSFT']
    """
    if not series:
        return pd.DataFrame()

    frames = []
    for s in series:
        s = s.copy()
        s.index = pd.to_datetime(s.index)
        frames.append(s)

    df = pd.concat(frames, axis=1, join="inner")
    df = df.dropna()
    return df


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _prep(price_df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the DataFrame is sorted by date with a datetime index."""
    df = price_df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    df = df.sort_index()
    return df
