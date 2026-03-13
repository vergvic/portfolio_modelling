"""
Central configuration constants.  No magic numbers elsewhere.
"""
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_appdata = os.environ.get("APPDATA", str(Path.home()))
DB_DIR = Path(_appdata) / "PortfolioModeller"
DB_PATH = DB_DIR / "portfolio.db"

# ---------------------------------------------------------------------------
# Data / caching
# ---------------------------------------------------------------------------
MARKET_PROXY = "SPY"

# How many hours before a cache entry is considered stale
CACHE_TTL_HOURS = 24

# How many years of weekly data to fetch for portfolio metrics
WEEKLY_WINDOW_YEARS = 3

# Annualisation factor for weekly returns
ANNUALIZE_WEEKLY = 52

# ---------------------------------------------------------------------------
# Portfolio parameter target ranges  (for traffic-light colouring)
# ---------------------------------------------------------------------------
# Annualised portfolio volatility: 15 – 30 %
VOL_TARGET: tuple[float, float] = (0.15, 0.30)

# Average pairwise correlation: –0.3 to +0.3
CORR_TARGET: tuple[float, float] = (-0.3, 0.3)

# Portfolio beta: –0.3 to +0.3
BETA_TARGET: tuple[float, float] = (-0.3, 0.3)

# ---------------------------------------------------------------------------
# Network / fetching
# ---------------------------------------------------------------------------
# Hard timeout (seconds) for any single yfinance download call.
# If Yahoo doesn't respond within this window the call returns an empty frame.
FETCH_TIMEOUT_SECONDS = 45

# ---------------------------------------------------------------------------
# Distribution of Returns
# ---------------------------------------------------------------------------
# Fixed bin width (as decimal) for close-to-close monthly returns
DOR_CC_BIN_WIDTH = 0.06      # 6 %

# Number of auto bins for high-to-low returns
DOR_HL_AUTO_BINS = 20

# Normal-distribution reference percentages for σ-bound analysis
NORMAL_SD_PCTS = {1: 0.6827, 2: 0.9545, 3: 0.9973}

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
APP_NAME = "Portfolio Modeller"
WINDOW_MIN_WIDTH = 1100
WINDOW_MIN_HEIGHT = 750
