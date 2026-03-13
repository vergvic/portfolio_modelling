"""
Distribution of Returns (DoR) calculations.

Produces the full statistical profile displayed in Tab 3, for both
close-to-close (C-C) and high-to-low (H-L) monthly return series.

Validated against PTM_02 Video 18 and Excel descriptive statistics output.
All functions are pure.
"""
import logging
import math

import numpy as np
import pandas as pd
import scipy.stats as stats

from config import DOR_CC_BIN_WIDTH, DOR_HL_AUTO_BINS, NORMAL_SD_PCTS

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Frequency distribution
# ---------------------------------------------------------------------------

def frequency_distribution(
    returns: pd.Series,
    bin_width: float | None = None,
) -> pd.DataFrame:
    """
    Build a frequency table for a return series.

    bin_width: None → use config defaults (6% for C-C, auto for H-L).
               Pass a value to override.

    Returns a DataFrame with columns:
        bin_label    : "–6% to 0%"  style label
        lower        : lower bound (inclusive)
        upper        : upper bound (exclusive, except last bin)
        count        : observations in bin
        probability  : count / total
        cumulative_pct: running total of probability
    """
    clean = returns.dropna()
    if clean.empty:
        return pd.DataFrame(columns=[
            "bin_label", "lower", "upper", "count", "probability", "cumulative_pct"
        ])

    mn, mx = clean.min(), clean.max()

    if bin_width is None:
        bin_width = DOR_CC_BIN_WIDTH  # default — caller must pass explicit for H-L

    # Build bin edges starting from a round multiple below the minimum
    start = math.floor(mn / bin_width) * bin_width
    edges = []
    edge = start
    while edge <= mx + bin_width:
        edges.append(round(edge, 10))
        edge = round(edge + bin_width, 10)

    rows = []
    total = len(clean)
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        if i < len(edges) - 2:
            mask = (clean >= lo) & (clean < hi)
        else:
            mask = (clean >= lo) & (clean <= hi)  # include max in last bin
        cnt = int(mask.sum())
        prob = cnt / total if total > 0 else 0.0
        label = f"{lo*100:.1f}% to {hi*100:.1f}%"
        rows.append({
            "bin_label": label,
            "lower": lo,
            "upper": hi,
            "count": cnt,
            "probability": prob,
        })

    df = pd.DataFrame(rows)
    df["cumulative_pct"] = df["probability"].cumsum()
    return df


def hl_bin_width(returns: pd.Series) -> float:
    """Auto-calculate bin width for high-to-low returns."""
    clean = returns.dropna()
    if clean.empty:
        return DOR_CC_BIN_WIDTH
    return (clean.max() - clean.min()) / DOR_HL_AUTO_BINS


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

def descriptive_stats(returns: pd.Series) -> dict:
    """
    Compute Excel-style descriptive statistics for a return series.

    Matches the Excel 'Descriptive Statistics' tool output:
        mean, standard_error, median, mode, std_dev, variance,
        kurtosis, skewness, range, minimum, maximum, sum, count
    """
    clean = returns.dropna()
    n = len(clean)

    if n < 2:
        return {k: None for k in [
            "mean", "standard_error", "median", "mode", "std_dev",
            "variance", "kurtosis", "skewness", "range",
            "minimum", "maximum", "sum", "count",
        ]}

    mean = float(clean.mean())
    std = float(clean.std(ddof=1))
    var = float(clean.var(ddof=1))
    se = std / math.sqrt(n)
    median = float(clean.median())
    mn = float(clean.min())
    mx = float(clean.max())
    rng = mx - mn
    total = float(clean.sum())

    # scipy kurtosis: excess kurtosis (same as Excel KURT)
    # scipy skewness: same as Excel SKEW
    kurt = float(stats.kurtosis(clean, bias=False))
    skew = float(stats.skew(clean, bias=False))

    # Mode — round to 3dp to avoid float noise, use most frequent
    rounded = clean.round(3)
    mode_result = stats.mode(rounded, keepdims=True)
    mode_val = float(mode_result.mode[0]) if mode_result.count[0] > 1 else 0.0

    return {
        "mean": mean,
        "standard_error": se,
        "median": median,
        "mode": mode_val,
        "std_dev": std,
        "variance": var,
        "kurtosis": kurt,
        "skewness": skew,
        "range": rng,
        "minimum": mn,
        "maximum": mx,
        "sum": total,
        "count": n,
    }


# ---------------------------------------------------------------------------
# Positive / Negative / Zero split
# ---------------------------------------------------------------------------

def pos_neg_zero_split(returns: pd.Series) -> dict:
    """
    Split observations into positive, negative, and zero buckets.

    Returns a dict with keys: positive, negative, zero
    Each bucket is itself a dict:
        count, avg_return, freq_pct, freq_adj_return
    """
    clean = returns.dropna()
    n = len(clean)
    if n == 0:
        empty = {"count": 0, "avg_return": None, "freq_pct": 0.0, "freq_adj_return": None}
        return {"positive": empty, "negative": empty, "zero": empty}

    def _bucket(mask):
        sub = clean[mask]
        cnt = len(sub)
        freq = cnt / n
        avg = float(sub.mean()) if cnt > 0 else None
        freq_adj = avg * freq if avg is not None else None
        return {
            "count": cnt,
            "avg_return": avg,
            "freq_pct": freq,
            "freq_adj_return": freq_adj,
        }

    return {
        "positive": _bucket(clean > 0),
        "negative": _bucket(clean < 0),
        "zero":     _bucket(clean == 0),
    }


# ---------------------------------------------------------------------------
# Standard deviation bounds vs normal distribution
# ---------------------------------------------------------------------------

def sd_bounds(returns: pd.Series) -> list[dict]:
    """
    For 1σ, 2σ, 3σ bounds:
        lower = mean - n*std
        upper = mean + n*std
        actual_count = observations within [lower, upper]
        actual_pct   = actual_count / total
        normal_pct   = theoretical normal (68.27%, 95.45%, 99.73%)

    Returns a list of 3 dicts, one per σ level.
    """
    clean = returns.dropna()
    n = len(clean)
    if n < 2:
        return []

    mean = float(clean.mean())
    std = float(clean.std(ddof=1))

    result = []
    for sigma_n, normal_pct in NORMAL_SD_PCTS.items():
        lo = mean - sigma_n * std
        hi = mean + sigma_n * std
        count_in = int(((clean >= lo) & (clean <= hi)).sum())
        actual_pct = count_in / n
        result.append({
            "sigma": sigma_n,
            "lower": lo,
            "upper": hi,
            "actual_count": count_in,
            "actual_pct": actual_pct,
            "normal_pct": normal_pct,
        })

    return result


# ---------------------------------------------------------------------------
# Combined DoR computation
# ---------------------------------------------------------------------------

def compute_dor(
    cc_returns: pd.Series,
    hl_returns: pd.Series,
) -> dict:
    """
    Bundle all DoR computations for both C-C and H-L return series.

    Returns:
    {
        "cc": {freq_dist, stats, split, sd_bounds},
        "hl": {freq_dist, stats, split, sd_bounds},
    }
    """
    def _run(returns: pd.Series, bw: float | None) -> dict:
        return {
            "freq_dist": frequency_distribution(returns, bin_width=bw),
            "stats": descriptive_stats(returns),
            "split": pos_neg_zero_split(returns),
            "sd_bounds": sd_bounds(returns),
        }

    hl_bw = hl_bin_width(hl_returns)

    return {
        "cc": _run(cc_returns, DOR_CC_BIN_WIDTH),
        "hl": _run(hl_returns, hl_bw),
    }
