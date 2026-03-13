"""
Tab 2 — Ticker vs Rest

Layout:
  1. Ticker selector (QComboBox)
  2. Two MetricCards: Annualised Vol | Beta vs SPY
  3. Pairwise Correlations table (this ticker vs each other)
  4. Portfolio Impact table (metrics with vs without this ticker)

Recomputes on ticker selection change.
"""
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from ui.widgets.metric_card import MetricCard
from ui.styles import (
    TEXT_SECONDARY, TEXT_PRIMARY, GREEN, RED, ORANGE, NEUTRAL, BG_PANEL
)


def _corr_color(v: float) -> str:
    """Traffic-light colour for a correlation value."""
    if v is None:
        return NEUTRAL
    av = abs(v)
    if av <= 0.3:
        return GREEN
    if av <= 0.5:
        return ORANGE
    return RED


class TabTicker(QWidget):
    """Tab 2: Ticker vs Rest."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._portfolio: list[dict] = []
        self._weekly_returns: dict = {}
        self._spy_weekly = None
        self._compute_fn = None   # injected: (ticker, portfolio, weekly_ret, spy) -> (with, without)
        self._per_ticker_vol: dict = {}
        self._per_ticker_beta: dict = {}
        self._build_ui()

    def set_compute_fn(self, fn) -> None:
        """Inject the with_without_impact compute function."""
        self._compute_fn = fn

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # ── Ticker selector ───────────────────────────────────────────
        sel_row = QHBoxLayout()
        sel_lbl = QLabel("Select ticker:")
        sel_lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: bold;")
        self._combo = QComboBox()
        self._combo.setMinimumWidth(140)
        self._combo.currentTextChanged.connect(self._on_ticker_changed)
        sel_row.addWidget(sel_lbl)
        sel_row.addWidget(self._combo)
        sel_row.addStretch()
        root.addLayout(sel_row)

        # ── Metric cards ──────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self._vol_card  = MetricCard("Annualised Volatility", unit="%", fmt=".1f")
        self._beta_card = MetricCard("Beta vs SPY",           unit="",  fmt=".2f")
        for card in (self._vol_card, self._beta_card):
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cards_row.addWidget(card)
        cards_row.addStretch()
        root.addLayout(cards_row)

        # ── Pairwise correlations ─────────────────────────────────────
        corr_box = QGroupBox("Pairwise Correlations (this ticker vs each other)")
        corr_layout = QVBoxLayout(corr_box)
        corr_layout.setContentsMargins(8, 8, 8, 8)

        self._corr_table = QTableWidget(0, 2)
        self._corr_table.setHorizontalHeaderLabels(["Pair", "Correlation"])
        self._corr_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._corr_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._corr_table.verticalHeader().hide()
        self._corr_table.setAlternatingRowColors(True)
        self._corr_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._corr_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        corr_layout.addWidget(self._corr_table)
        root.addWidget(corr_box)

        # ── Portfolio impact ──────────────────────────────────────────
        impact_box = QGroupBox("Portfolio Impact (with vs without this ticker)")
        impact_layout = QVBoxLayout(impact_box)
        impact_layout.setContentsMargins(8, 8, 8, 8)

        self._impact_table = QTableWidget(3, 3)
        self._impact_table.setHorizontalHeaderLabels(["Metric", "With", "Without"])
        self._impact_table.setVerticalHeaderLabels(["Port Beta", "Port Vol (%)", "Avg Corr"])
        self._impact_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._impact_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._impact_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._impact_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._impact_table.setAlternatingRowColors(True)

        # Pre-fill metric names
        for i, label in enumerate(["Portfolio Beta", "Portfolio Vol (%)", "Avg Corr"]):
            item = QTableWidgetItem(label)
            item.setForeground(QColor(TEXT_SECONDARY))
            self._impact_table.setItem(i, 0, item)

        impact_layout.addWidget(self._impact_table)
        root.addWidget(impact_box)

        root.addStretch()

    # ------------------------------------------------------------------
    def refresh_display(
        self,
        portfolio: list[dict],
        metrics: dict,
        weekly_returns: dict,
        spy_weekly,
    ) -> None:
        """
        Called by MainWindow whenever portfolio state changes.
        Repopulates the combo box and refreshes the currently selected ticker.
        """
        self._portfolio = portfolio
        self._weekly_returns = weekly_returns
        self._spy_weekly = spy_weekly
        self._per_ticker_vol  = metrics.get("per_ticker_vol", {})
        self._per_ticker_beta = metrics.get("per_ticker_beta", {})

        current = self._combo.currentText()
        self._combo.blockSignals(True)
        self._combo.clear()
        tickers = [p["ticker"] for p in portfolio]
        self._combo.addItems(tickers)
        if current in tickers:
            self._combo.setCurrentText(current)
        self._combo.blockSignals(False)

        self._on_ticker_changed(self._combo.currentText())

    # ------------------------------------------------------------------
    def _on_ticker_changed(self, ticker: str) -> None:
        if not ticker:
            self._clear()
            return

        # Metric cards
        vol  = self._per_ticker_vol.get(ticker)
        beta = self._per_ticker_beta.get(ticker)
        self._vol_card.set_value(vol, scale=100.0)
        self._beta_card.set_value(beta)

        # Pairwise correlations
        from compute.ticker_metrics import pairwise_correlations
        if ticker in self._weekly_returns:
            corr_dict = pairwise_correlations(ticker, self._weekly_returns)
            self._fill_corr_table(ticker, corr_dict)
        else:
            self._corr_table.setRowCount(0)

        # With / without impact
        if self._compute_fn and self._portfolio:
            try:
                with_m, without_m = self._compute_fn(
                    ticker, self._portfolio, self._weekly_returns, self._spy_weekly
                )
                self._fill_impact_table(ticker, with_m, without_m)
            except Exception:
                self._clear_impact_table()

    def _fill_corr_table(self, ticker: str, corr_dict: dict) -> None:
        sorted_items = sorted(corr_dict.items(), key=lambda x: x[0])
        self._corr_table.setRowCount(len(sorted_items))
        for row, (other, val) in enumerate(sorted_items):
            pair_item = QTableWidgetItem(f"{ticker} vs {other}")
            pair_item.setForeground(QColor(TEXT_PRIMARY))
            val_item = QTableWidgetItem(f"{val:+.3f}")
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_item.setForeground(QColor(_corr_color(val)))
            self._corr_table.setItem(row, 0, pair_item)
            self._corr_table.setItem(row, 1, val_item)

    def _fill_impact_table(self, ticker: str, with_m: dict, without_m: dict) -> None:
        self._impact_table.setHorizontalHeaderLabels(
            ["Metric", f"With {ticker}", f"Without {ticker}"]
        )
        rows = [
            ("Portfolio Beta",    "portfolio_beta", 1.0,   "{:+.3f}"),
            ("Portfolio Vol (%)", "portfolio_vol",  100.0, "{:.1f}%"),
            ("Avg Corr",          "avg_correlation",1.0,   "{:+.3f}"),
        ]
        for i, (label, key, scale, fmt) in enumerate(rows):
            # Label column
            lbl_item = QTableWidgetItem(label)
            lbl_item.setForeground(QColor(TEXT_SECONDARY))
            self._impact_table.setItem(i, 0, lbl_item)

            # With column
            v_with = with_m.get(key)
            with_item = QTableWidgetItem(
                fmt.format(v_with * scale) if v_with is not None else "—"
            )
            with_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            with_item.setForeground(QColor(TEXT_PRIMARY))
            self._impact_table.setItem(i, 1, with_item)

            # Without column
            v_without = without_m.get(key)
            without_item = QTableWidgetItem(
                fmt.format(v_without * scale) if v_without is not None else "—"
            )
            without_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            without_item.setForeground(QColor(TEXT_SECONDARY))
            self._impact_table.setItem(i, 2, without_item)

    def _clear_impact_table(self) -> None:
        for i in range(3):
            for j in (1, 2):
                item = QTableWidgetItem("—")
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item.setForeground(QColor(TEXT_SECONDARY))
                self._impact_table.setItem(i, j, item)

    def _clear(self) -> None:
        self._vol_card.set_value(None)
        self._beta_card.set_value(None)
        self._corr_table.setRowCount(0)
        self._clear_impact_table()
