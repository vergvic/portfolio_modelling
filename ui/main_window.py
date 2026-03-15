"""
MainWindow — QMainWindow hosting the 3-tab interface.

Responsibilities:
- Own the central in-memory state: portfolio, metrics, return series, DoR data
- Orchestrate the signal chain:
    portfolio change → _recompute_all() → _update_all_tabs()
- Launch background cache refresh on startup (QThread)
- Show status bar messages for cache staleness
- Handle the Add / Remove position flow (validate + cache + compute)
"""
import logging
from typing import Any

import pandas as pd
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QTabWidget, QVBoxLayout,
    QStatusBar, QLabel, QApplication, QToolButton, QMenu,
)
from PySide6.QtCore import Qt, QThread, Signal

import data.db    as db
import data.cache as cache
from compute.returns           import weekly_cc_returns, monthly_cc_returns, monthly_hl_returns
from compute.portfolio_metrics import compute_all_metrics
from compute.dor               import compute_dor
from compute.ticker_metrics    import with_without_impact

from ui.tab_portfolio import TabPortfolio
from ui.tab_ticker    import TabTicker
from ui.tab_dor       import TabDoR
from ui.widgets.ticker_input import TickerInputDialog
import ui.styles as styles
from ui.styles import ORANGE, TEXT_SECONDARY  # noqa: F401  (re-exported aliases)
from ui.widgets.theme_editor import ThemeEditorDialog, load_custom_theme
from config import APP_NAME, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, MARKET_PROXY

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background worker for network operations
# ---------------------------------------------------------------------------

class _AddTickerThread(QThread):
    """
    Fetches price data for a new ticker.

    Subclasses QThread and overrides run() directly — this is the correct
    pattern for blocking work.  Do NOT use moveToThread + worker.run as a
    slot: that calls run() via the Qt event loop which can deadlock when the
    work itself blocks waiting on a sub-thread (queue.get etc.).
    """
    result_ready = Signal(bool)   # True = data ok, False = empty / bad ticker
    error        = Signal(str)

    def __init__(self, ticker: str, parent=None):
        super().__init__(parent)
        self._ticker = ticker

    def run(self) -> None:          # called directly by the OS thread, not via event loop
        try:
            ok = cache.ensure_ticker_cached(self._ticker)
            self.result_ready.emit(ok)
        except Exception as exc:
            self.error.emit(str(exc))


class _CacheRefreshThread(QThread):
    """Refreshes stale cache entries for all portfolio tickers."""

    result_ready = Signal(dict)
    error        = Signal(str)

    def __init__(self, tickers: list[str], force: bool = False, parent=None):
        super().__init__(parent)
        self._tickers = tickers
        self._force   = force

    def run(self) -> None:
        try:
            if self._force:
                result = cache.force_refresh_all(self._tickers)
            else:
                result = cache.refresh_stale_tickers(self._tickers)
            self.result_ready.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):

    _ORANGE = ORANGE   # colour alias for error status messages

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        # Stylesheet is applied at the QApplication level in main.py so that
        # QApplication.setStyleSheet() calls made during theme switching are
        # not shadowed by a widget-level override here.

        # In-memory state
        self._portfolio: list[dict] = []
        self._metrics:   dict       = {}
        self._weekly_returns: dict[str, pd.Series] = {}
        self._monthly_returns_cc: dict[str, pd.Series] = {}
        self._monthly_returns_hl: dict[str, pd.Series] = {}
        self._spy_weekly: pd.Series | None = None
        self._dor_data:  dict[str, dict]   = {}

        self._active_threads: list[QThread] = []

        self._build_ui()
        self._load_initial_state()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._tab_portfolio = TabPortfolio()
        self._tab_ticker    = TabTicker()
        self._tab_dor       = TabDoR()

        self._tabs.addTab(self._tab_portfolio, "Portfolio")
        self._tabs.addTab(self._tab_ticker,    "Ticker vs Rest")
        self._tabs.addTab(self._tab_dor,       "Distribution of Returns")

        # Theme dropdown — placed in the top-right corner of the tab bar
        self._theme_btn = QToolButton()
        self._theme_btn.setObjectName("ThemeButton")
        self._theme_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._theme_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._theme_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._theme_menu = QMenu(self._theme_btn)
        self._theme_btn.setMenu(self._theme_menu)
        self._refresh_theme_menu()
        self._tabs.setCornerWidget(self._theme_btn, Qt.Corner.TopRightCorner)

        # Load any previously saved Custom theme on startup
        self._load_saved_custom_theme()

        layout.addWidget(self._tabs)

        # Wire up Tab 1 signals
        self._tab_portfolio.add_position_requested.connect(self._on_add_position)
        self._tab_portfolio.remove_position_requested.connect(self._on_remove_position)
        self._tab_portfolio.refresh_data_requested.connect(self._on_force_refresh)

        # Wire up Tab 2 compute function
        self._tab_ticker.set_compute_fn(with_without_impact)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._status_bar.addWidget(self._status_label)

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def _load_initial_state(self) -> None:
        """Load portfolio from DB, then refresh stale caches in background."""
        self._portfolio = db.get_portfolio()
        self._set_status("Loading cached data…")

        if not self._portfolio:
            self._set_status("No positions yet.  Use '+ Add Long / Short' to begin.")
            self._recompute_all()
            self._update_all_tabs()
            return

        tickers = [p["ticker"] for p in self._portfolio]
        self._start_cache_refresh(tickers, force=False)

    # ------------------------------------------------------------------
    # Portfolio mutations
    # ------------------------------------------------------------------

    def _on_add_position(self, side: str) -> None:
        dlg = TickerInputDialog(self, prefill_side=side)
        if dlg.exec() != TickerInputDialog.DialogCode.Accepted:
            return

        data = dlg.result_data
        ticker = data["ticker"]

        # Write to DB immediately so ticker appears in list while fetching
        db.add_position(ticker, data["side"], data["dollar_amount"])
        self._portfolio = db.get_portfolio()
        self._update_all_tabs()   # show ticker in list straight away
        self._set_status(f"Fetching data for {ticker}…")

        thread = _AddTickerThread(ticker)
        thread.result_ready.connect(lambda ok: self._on_add_ticker_done(ticker, ok))
        thread.error.connect(lambda e: self._on_add_ticker_error(ticker, e))
        thread.finished.connect(lambda: self._cleanup_thread(thread))
        self._active_threads.append(thread)
        thread.start()

    def _on_add_ticker_done(self, ticker: str, data_ok: bool) -> None:
        if not data_ok:
            # Yahoo returned nothing — almost certainly an invalid ticker
            log.warning("No data returned for %s — removing from portfolio", ticker)
            db.remove_position(ticker)
            self._portfolio = db.get_portfolio()
            self._set_status(
                f"'{ticker}' not recognised by Yahoo Finance — position removed.",
                color=self._ORANGE,
            )
            self._recompute_all()
            self._update_all_tabs()
            return

        self._set_status(f"{ticker} cached.  Computing metrics…")
        self._recompute_all()
        self._update_all_tabs()
        self._set_status("Ready.")

    def _on_add_ticker_error(self, ticker: str, error: str) -> None:
        log.error("Failed to fetch data for %s: %s", ticker, error)
        self._set_status(
            f"Could not fetch data for {ticker} — check your connection.",
            color=self._ORANGE,
        )
        self._recompute_all()
        self._update_all_tabs()

    def _on_remove_position(self, ticker: str) -> None:
        db.remove_position(ticker)
        self._portfolio = db.get_portfolio()
        self._set_status(f"{ticker} removed.")
        self._recompute_all()
        self._update_all_tabs()

    # ------------------------------------------------------------------
    # Cache refresh
    # ------------------------------------------------------------------

    def _on_force_refresh(self) -> None:
        tickers = [p["ticker"] for p in self._portfolio]
        if not tickers:
            return
        self._set_status("Refreshing data from Yahoo Finance…")
        self._start_cache_refresh(tickers, force=True)

    def _start_cache_refresh(self, tickers: list[str], force: bool) -> None:
        thread = _CacheRefreshThread(tickers, force=force)
        thread.result_ready.connect(self._on_refresh_done)
        thread.error.connect(self._on_refresh_error)
        thread.finished.connect(lambda: self._cleanup_thread(thread))
        self._active_threads.append(thread)
        thread.start()

    def _on_refresh_done(self, result: dict) -> None:
        errors = [t for t, s in result.items() if s == "error"]
        if errors:
            self._set_status(
                f"Data may be stale for: {', '.join(errors)}",
                color=ORANGE,
            )
        else:
            self._set_status("Data refreshed.")
        self._recompute_all()
        self._update_all_tabs()

    def _on_refresh_error(self, error: str) -> None:
        log.error("Cache refresh error: %s", error)
        self._set_status("Could not refresh — using cached data.", color=ORANGE)
        self._recompute_all()
        self._update_all_tabs()

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------

    def _recompute_all(self) -> None:
        """
        Rebuild all return series from the DB cache and recompute every metric.
        Called after any portfolio mutation or data refresh.
        """
        if not self._portfolio:
            self._metrics = {}
            self._weekly_returns = {}
            self._spy_weekly = None
            self._dor_data = {}
            return

        tickers = [p["ticker"] for p in self._portfolio]
        all_tickers = list(dict.fromkeys(tickers + [MARKET_PROXY]))

        # Load price data from cache and build return series
        weekly_ret: dict[str, pd.Series] = {}
        monthly_cc: dict[str, pd.Series] = {}
        monthly_hl: dict[str, pd.Series] = {}

        for ticker in all_tickers:
            w_prices = cache.get_prices(ticker, "weekly")
            m_prices = cache.get_prices(ticker, "monthly")

            if not w_prices.empty:
                try:
                    weekly_ret[ticker] = weekly_cc_returns(w_prices)
                    weekly_ret[ticker].name = ticker
                except Exception as exc:
                    log.warning("weekly_cc_returns(%s): %s", ticker, exc)

            if not m_prices.empty:
                try:
                    monthly_cc[ticker] = monthly_cc_returns(m_prices)
                    monthly_cc[ticker].name = ticker
                except Exception as exc:
                    log.warning("monthly_cc_returns(%s): %s", ticker, exc)
                try:
                    monthly_hl[ticker] = monthly_hl_returns(m_prices)
                    monthly_hl[ticker].name = ticker
                except Exception as exc:
                    log.warning("monthly_hl_returns(%s): %s", ticker, exc)

        self._weekly_returns      = {t: weekly_ret[t] for t in tickers if t in weekly_ret}
        self._monthly_returns_cc  = {t: monthly_cc[t] for t in tickers if t in monthly_cc}
        self._monthly_returns_hl  = {t: monthly_hl[t] for t in tickers if t in monthly_hl}
        self._spy_weekly          = weekly_ret.get(MARKET_PROXY)

        # Portfolio-level metrics
        self._metrics = compute_all_metrics(
            self._portfolio,
            weekly_ret,
            self._spy_weekly,
        )

        # DoR data per ticker
        dor: dict[str, dict] = {}
        for ticker in tickers:
            cc = self._monthly_returns_cc.get(ticker)
            hl = self._monthly_returns_hl.get(ticker)
            if cc is not None and not cc.empty and hl is not None and not hl.empty:
                try:
                    dor[ticker] = compute_dor(cc, hl)
                except Exception as exc:
                    log.warning("compute_dor(%s): %s", ticker, exc)
        self._dor_data = dor

        # Surface any compute warnings in status bar
        warnings = self._metrics.get("warnings", [])
        if warnings:
            self._set_status(" | ".join(warnings[:2]), color=ORANGE)

    # ------------------------------------------------------------------
    # Update all tabs
    # ------------------------------------------------------------------

    def _update_all_tabs(self) -> None:
        self._tab_portfolio.refresh_display(self._portfolio, self._metrics)
        self._tab_ticker.refresh_display(
            self._portfolio,
            self._metrics,
            self._weekly_returns,
            self._spy_weekly,
        )
        self._tab_dor.refresh_display(self._portfolio, self._dor_data)

    # ------------------------------------------------------------------
    # Theme management
    # ------------------------------------------------------------------

    def _refresh_theme_menu(self) -> None:
        """Rebuild the theme dropdown to reflect current THEME_ORDER."""
        self._theme_menu.clear()
        current = styles.current_theme_name()

        for name in styles.THEME_ORDER:
            action = self._theme_menu.addAction(
                f"✓  {name}" if name == current else f"    {name}"
            )
            action.triggered.connect(lambda checked=False, n=name: self._on_theme_select(n))

        self._theme_menu.addSeparator()
        edit_action = self._theme_menu.addAction("✎  Edit Custom Theme…")
        edit_action.triggered.connect(self._on_edit_custom_theme)

        self._theme_btn.setText(f"THEME: {current}  ▾")

    def _on_theme_select(self, name: str) -> None:
        new_ss = styles.apply_theme(name)
        QApplication.instance().setStyleSheet(new_ss)
        self._refresh_theme_menu()
        self._update_all_tabs()

    def _on_edit_custom_theme(self) -> None:
        dlg = ThemeEditorDialog(self)
        dlg.theme_applied.connect(self._on_custom_theme_applied)
        dlg.exec()

    def _on_custom_theme_applied(self) -> None:
        """Called when user saves a new custom theme in the editor."""
        new_ss = styles.apply_theme("Custom")
        QApplication.instance().setStyleSheet(new_ss)
        self._refresh_theme_menu()
        self._update_all_tabs()

    def _load_saved_custom_theme(self) -> None:
        """On startup: if a custom_theme.json exists, register it (don't auto-apply)."""
        import os
        from ui.widgets.theme_editor import _CUSTOM_PATH
        if os.path.exists(_CUSTOM_PATH):
            theme = load_custom_theme()
            styles.THEMES["Custom"] = theme
            if "Custom" not in styles.THEME_ORDER:
                styles.THEME_ORDER.append("Custom")
            self._refresh_theme_menu()

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _set_status(self, msg: str, color: str = "") -> None:
        style = f"color: {color};" if color else f"color: {TEXT_SECONDARY};"
        self._status_label.setStyleSheet(style)
        self._status_label.setText(msg)

    # ------------------------------------------------------------------
    # Thread cleanup
    # ------------------------------------------------------------------

    def _cleanup_thread(self, thread: QThread) -> None:
        if thread in self._active_threads:
            self._active_threads.remove(thread)
        thread.deleteLater()

    def closeEvent(self, event) -> None:
        for thread in self._active_threads:
            thread.quit()
            thread.wait(2000)
        super().closeEvent(event)
