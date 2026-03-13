"""
Per-ticker metric calculations.

All functions are pure — no DB, no UI imports.

Validated against PTM_02:
  Annualised vol : STDEV.S(weekly_returns) × √52
  Beta vs SPY    : SLOPE(stock_returns, spy_returns) — i.e. linear regression gradient
                   using 2–3 years of weekly data
"""
import logging

import numpy as np
import pandas as pd

from compute.returns import align_returns

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-ticker metrics
# ---------------------------------------------------------------------------

def annualized_vol(weekly_returns: pd.Series) -> float | None:
    """
    Annualised volatility = STDEV.S(weekly_returns) × √52.

    Uses ddof=1 (sample standard deviation) to match Excel STDEV.S.
    Returns None if the series has fewer than 2 observations.
    """
    clean = weekly_returns.dropna()
    if len(clean) < 2:
        return None
    return float(clean.std(ddof=1) * np.sqrt(52))


def beta_vs_spy(
    stock_weekly: pd.Series,
    spy_weekly: pd.Series,
) -> float | None:
    """
    Beta = gradient of OLS regression of stock returns (Y) on SPY returns (X).

    Equivalent to Excel SLOPE(stock_array, spy_array).
    Uses np.polyfit(..., deg=1)[0] per the architecture spec.

    Both series are date-aligned (inner join) before regression.
    Returns None if fewer than 4 overlapping observations remain.
    """
    if stock_weekly is None or spy_weekly is None:
        return None
    if stock_weekly.empty or spy_weekly.empty:
        return None

    aligned = align_returns(stock_weekly.rename("stock"), spy_weekly.rename("spy"))
    if aligned.empty or len(aligned) < 4:
        return None

    x = aligned["spy"].values
    y = aligned["stock"].values

    try:
        slope = float(np.polyfit(x, y, 1)[0])
        return slope
    except (np.linalg.LinAlgError, ValueError) as exc:
        log.warning("beta_vs_spy regression failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Pairwise correlations
# ---------------------------------------------------------------------------

def pairwise_correlations(
    ticker: str,
    all_weekly_returns: dict[str, pd.Series],
) -> dict[str, float]:
    """
    Compute Pearson correlation between *ticker* and each other ticker.

    Returns {other_ticker: correlation} for every other ticker that has
    sufficient aligned data (≥ 4 overlapping observations).
    """
    if ticker not in all_weekly_returns:
        return {}

    base = all_weekly_returns[ticker].rename(ticker)
    result: dict[str, float] = {}

    for other, series in all_weekly_returns.items():
        if other == ticker:
            continue
        aligned = align_returns(base, series.rename(other))
        if aligned.empty or len(aligned) < 4:
            continue
        corr_val = aligned[ticker].corr(aligned[other])
        if not np.isnan(corr_val):
            result[other] = float(corr_val)

    return result


# ---------------------------------------------------------------------------
# With / without impact
# ---------------------------------------------------------------------------

def with_without_impact(
    ticker: str,
    portfolio_rows: list[dict],
    weekly_returns: dict[str, pd.Series],
    spy_weekly: pd.Series,
) -> tuple[dict, dict]:
    """
    Compute portfolio-level metrics (vol, beta, avg_correlation) with and
    without the selected ticker.

    Returns
    -------
    (with_metrics, without_metrics)
    Each is a dict: {portfolio_vol, portfolio_beta, avg_correlation}
    """
    from compute.portfolio_metrics import (
        compute_weights,
        correlation_matrix,
        covariance_matrix,
        portfolio_volatility,
        portfolio_beta,
        avg_pairwise_correlation,
    )

    def _compute(rows: list[dict]) -> dict:
        if len(rows) < 2:
            return {"portfolio_vol": None, "portfolio_beta": None, "avg_correlation": None}

        tickers = [r["ticker"] for r in rows]
        series_list = []
        for t in tickers:
            if t in weekly_returns and not weekly_returns[t].empty:
                s = weekly_returns[t].copy()
                s.name = t
                series_list.append(s)

        if len(series_list) < 2:
            return {"portfolio_vol": None, "portfolio_beta": None, "avg_correlation": None}

        aligned = align_returns(*series_list)
        if aligned.empty:
            return {"portfolio_vol": None, "portfolio_beta": None, "avg_correlation": None}

        weights = compute_weights(rows)
        aligned_tickers = list(aligned.columns)
        weights_filtered = {t: weights[t] for t in aligned_tickers if t in weights}

        betas = {
            t: beta_vs_spy(weekly_returns[t], spy_weekly)
            for t in tickers
            if t in weekly_returns
        }
        betas = {t: v for t, v in betas.items() if v is not None}

        corr = correlation_matrix(aligned)
        cov = covariance_matrix(aligned)

        return {
            "portfolio_vol": portfolio_volatility(weights_filtered, cov),
            "portfolio_beta": portfolio_beta(weights, betas),
            "avg_correlation": avg_pairwise_correlation(corr),
        }

    rows_with = portfolio_rows
    rows_without = [r for r in portfolio_rows if r["ticker"] != ticker]

    return _compute(rows_with), _compute(rows_without)
