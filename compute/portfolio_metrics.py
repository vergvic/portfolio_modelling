"""
Portfolio-level metric calculations.

All functions are pure — no DB, no UI imports.

Formulas validated against PTM_02 (Videos 18, 19, 20, 21):
  Weights      : dollar_i / sum(abs(all_dollars)); longs +, shorts -
  Correlation  : Pearson on aligned weekly returns — DataFrame.corr()
  Covariance   : DataFrame.cov() × 52  (annualise weekly)
  Portfolio vol: sqrt(w^T Σ w)
  Portfolio β  : Σ(weight_i × beta_i)
  Avg corr     : mean of all off-diagonal elements of correlation matrix
"""
import logging
import warnings

import numpy as np
import pandas as pd

from compute.returns import align_returns
from compute.ticker_metrics import annualized_vol, beta_vs_spy

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

def compute_weights(portfolio_rows: list[dict]) -> dict[str, float]:
    """
    Compute signed weights for every position.

    Weight formula (architecture spec §Key Design Decisions #1):
        weight_i = dollar_amount_i / sum(abs(all_dollar_amounts))
        Longs  → positive weight
        Shorts → negative weight

    portfolio_rows: list of dicts with keys 'ticker', 'side', 'dollar_amount'
    Returns: {ticker: weight}  — weights sum to a net bias, not necessarily 0 or 1
    """
    if not portfolio_rows:
        return {}

    gross = sum(abs(r["dollar_amount"]) for r in portfolio_rows)
    if gross == 0:
        return {}

    weights = {}
    for r in portfolio_rows:
        sign = 1.0 if r["side"] == "long" else -1.0
        weights[r["ticker"]] = sign * abs(r["dollar_amount"]) / gross

    return weights


# ---------------------------------------------------------------------------
# Matrices
# ---------------------------------------------------------------------------

def correlation_matrix(aligned_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pearson correlation matrix from aligned weekly return columns.
    Returns an n×n DataFrame with tickers as both index and columns.
    """
    if aligned_df.empty or aligned_df.shape[1] < 2:
        return pd.DataFrame()
    return aligned_df.corr()


def covariance_matrix(aligned_df: pd.DataFrame) -> pd.DataFrame:
    """
    Annualised variance-covariance matrix.
    = DataFrame.cov() × 52   (weekly → annual)
    """
    if aligned_df.empty or aligned_df.shape[1] < 2:
        return pd.DataFrame()
    return aligned_df.cov() * 52


# ---------------------------------------------------------------------------
# Portfolio volatility
# ---------------------------------------------------------------------------

def portfolio_volatility(
    weights: dict[str, float],
    cov_matrix: pd.DataFrame,
) -> float | None:
    """
    Portfolio volatility = sqrt(w^T Σ w).

    weights   : {ticker: signed_weight}
    cov_matrix: annualised covariance matrix (tickers as index/columns)

    Returns annualised portfolio volatility as a decimal (e.g. 0.184 = 18.4%).
    Returns None if the matrix is singular or inputs are insufficient.
    """
    if not weights or cov_matrix.empty:
        return None

    tickers = [t for t in weights if t in cov_matrix.index]
    if len(tickers) < 2:
        return None

    w = np.array([weights[t] for t in tickers])
    sigma = cov_matrix.loc[tickers, tickers].values

    try:
        var = float(w @ sigma @ w)
        if var < 0:
            log.warning("Negative portfolio variance (%.6f) — returning None", var)
            return None
        return float(np.sqrt(var))
    except np.linalg.LinAlgError as exc:
        log.warning("Singular covariance matrix: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Portfolio beta
# ---------------------------------------------------------------------------

def portfolio_beta(
    weights: dict[str, float],
    betas: dict[str, float],
) -> float | None:
    """
    Portfolio beta = Σ(weight_i × beta_i).
    Short positions carry negative weight, so they reduce beta naturally.

    Returns None if there are no overlapping tickers between weights and betas.
    """
    common = {t for t in weights if t in betas}
    if not common:
        return None
    return sum(weights[t] * betas[t] for t in common)


# ---------------------------------------------------------------------------
# Average pairwise correlation
# ---------------------------------------------------------------------------

def avg_pairwise_correlation(corr_matrix: pd.DataFrame) -> float | None:
    """
    Mean of all off-diagonal elements in the correlation matrix.

    For a portfolio with n tickers, there are n*(n-1) off-diagonal values
    (symmetric, so each pair counted twice — mean is the same either way).
    """
    if corr_matrix.empty or corr_matrix.shape[0] < 2:
        return None

    arr = corr_matrix.values.copy().astype(float)
    np.fill_diagonal(arr, np.nan)
    off_diag = arr[~np.isnan(arr)]
    if len(off_diag) == 0:
        return None
    return float(np.mean(off_diag))


# ---------------------------------------------------------------------------
# Compute all metrics at once (convenience wrapper)
# ---------------------------------------------------------------------------

def compute_all_metrics(
    portfolio_rows: list[dict],
    weekly_returns: dict[str, pd.Series],
    spy_weekly: pd.Series,
) -> dict:
    """
    Compute every portfolio-level metric and return them in a single dict.

    Parameters
    ----------
    portfolio_rows : list of {ticker, side, dollar_amount}
    weekly_returns : {ticker: pd.Series of weekly CC returns, indexed by date}
    spy_weekly     : pd.Series of SPY weekly returns

    Returns
    -------
    dict with keys:
        weights, corr_matrix, cov_matrix, portfolio_vol, portfolio_beta,
        avg_correlation, per_ticker_vol, per_ticker_beta, warnings
    """
    from compute.ticker_metrics import annualized_vol, beta_vs_spy

    result: dict = {
        "weights": {},
        "corr_matrix": pd.DataFrame(),
        "cov_matrix": pd.DataFrame(),
        "portfolio_vol": None,
        "portfolio_beta": None,
        "avg_correlation": None,
        "per_ticker_vol": {},
        "per_ticker_beta": {},
        "warnings": [],
    }

    if len(portfolio_rows) < 2:
        result["warnings"].append("At least 2 tickers required for portfolio metrics.")
        return result

    tickers = [r["ticker"] for r in portfolio_rows]

    # Build aligned weekly returns DataFrame (tickers only, not SPY)
    series_list = []
    available_tickers = []
    for ticker in tickers:
        if ticker in weekly_returns and not weekly_returns[ticker].empty:
            s = weekly_returns[ticker].copy()
            s.name = ticker
            series_list.append(s)
            available_tickers.append(ticker)
        else:
            result["warnings"].append(f"{ticker}: no weekly return data available.")

    if len(series_list) < 2:
        result["warnings"].append("Fewer than 2 tickers have usable data.")
        return result

    aligned = align_returns(*series_list)
    if aligned.empty or aligned.shape[1] < 2:
        result["warnings"].append("Could not align return series.")
        return result

    # Per-ticker metrics
    vol_map: dict[str, float] = {}
    beta_map: dict[str, float] = {}
    for ticker in available_tickers:
        ret = weekly_returns[ticker]
        if len(ret) < 52:
            result["warnings"].append(f"{ticker}: fewer than 52 weeks of data (using available).")
        v = annualized_vol(ret)
        if v is not None:
            vol_map[ticker] = v
        b = beta_vs_spy(ret, spy_weekly)
        if b is not None:
            beta_map[ticker] = b

    result["per_ticker_vol"] = vol_map
    result["per_ticker_beta"] = beta_map

    # Weights (use all portfolio rows, even if some had no data)
    weights = compute_weights(portfolio_rows)
    result["weights"] = weights

    # Filter weights to tickers that actually appear in aligned DataFrame
    aligned_tickers = list(aligned.columns)
    weights_filtered = {t: weights[t] for t in aligned_tickers if t in weights}

    # Matrices
    corr = correlation_matrix(aligned)
    cov = covariance_matrix(aligned)
    result["corr_matrix"] = corr
    result["cov_matrix"] = cov

    # Portfolio-level scalars
    result["portfolio_vol"] = portfolio_volatility(weights_filtered, cov)
    result["portfolio_beta"] = portfolio_beta(weights, beta_map)
    result["avg_correlation"] = avg_pairwise_correlation(corr)

    if result["portfolio_vol"] is None:
        result["warnings"].append("Portfolio volatility could not be computed (singular matrix?).")

    return result
