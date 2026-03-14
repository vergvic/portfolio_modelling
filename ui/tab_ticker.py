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
    QSizePolicy, QScrollArea, QAbstractScrollArea, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ui.widgets.metric_card import MetricCard
import ui.styles as _s


class _PassThroughTable(QTableWidget):
    """QTableWidget that passes wheel events up to the parent scroll area."""
    def wheelEvent(self, event):
        event.ignore()


def _corr_color(v: float) -> str:
    """Traffic-light colour for a correlation value."""
    if v is None:
        return _s.NEUTRAL
    av = abs(v)
    if av <= 0.3:
        return _s.GREEN
    if av <= 0.5:
        return _s.ORANGE
    return _s.RED


def _fit_table(t: QTableWidget) -> None:
    """Set minimum height so every row is visible — no internal scrolling."""
    h = t.horizontalHeader().height() + 2
    for i in range(t.rowCount()):
        h += t.rowHeight(i)
    t.setMinimumHeight(h)


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _delta_color(value: float, max_scale: float) -> str:
    """
    Blend from the current theme's NEUTRAL toward GREEN (positive) or RED
    (negative) with intensity proportional to abs(value) / max_scale.
    """
    t      = min(abs(value) / max_scale, 1.0)
    n      = _hex_to_rgb(_s.NEUTRAL)
    target = _hex_to_rgb(_s.GREEN if value >= 0 else _s.RED)
    r = int(n[0] + t * (target[0] - n[0]))
    g = int(n[1] + t * (target[1] - n[1]))
    b = int(n[2] + t * (target[2] - n[2]))
    return f"#{r:02X}{g:02X}{b:02X}"


class TabTicker(QWidget):
    """Tab 2: Ticker vs Rest."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._portfolio: list[dict] = []
        self._weekly_returns: dict = {}
        self._spy_weekly = None
        self._compute_fn = None
        self._per_ticker_vol: dict  = {}
        self._per_ticker_beta: dict = {}
        self._build_ui()

    def set_compute_fn(self, fn) -> None:
        """Inject the with_without_impact compute function."""
        self._compute_fn = fn

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # ── Ticker selector ───────────────────────────────────────────
        sel_row = QHBoxLayout()
        self._sel_lbl = QLabel("Select ticker:")
        self._sel_lbl.setStyleSheet(f"color: {_s.TEXT_SECONDARY}; font-weight: bold;")
        self._combo = QComboBox()
        self._combo.setMinimumWidth(140)
        self._combo.currentTextChanged.connect(self._on_ticker_changed)
        sel_row.addWidget(self._sel_lbl)
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

        self._corr_table = _PassThroughTable(0, 2)
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
        self._corr_table.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents
        )
        self._corr_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._corr_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        corr_layout.addWidget(self._corr_table)

        # ── Portfolio impact ──────────────────────────────────────────
        impact_box = QGroupBox("Portfolio Impact (with vs without this ticker)")
        impact_layout = QVBoxLayout(impact_box)
        impact_layout.setContentsMargins(8, 8, 8, 8)

        self._impact_table = _PassThroughTable(3, 3)
        self._impact_table.setHorizontalHeaderLabels(["With", "Without", "Net Change"])
        self._impact_table.setVerticalHeaderLabels(["Portfolio Beta", "Portfolio Vol (%)", "Avg Corr"])
        self._impact_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._impact_table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._impact_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._impact_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._impact_table.setAlternatingRowColors(True)
        self._impact_table.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents
        )
        self._impact_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._impact_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        _fit_table(self._impact_table)

        impact_layout.addWidget(self._impact_table)

        # ── Correlations + Impact side by side ────────────────────────
        tables_row = QHBoxLayout()
        tables_row.setSpacing(12)
        tables_row.addWidget(corr_box, stretch=1)
        tables_row.addWidget(impact_box, stretch=1)
        root.addLayout(tables_row)

        root.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    def refresh_display(
        self,
        portfolio: list[dict],
        metrics: dict,
        weekly_returns: dict,
        spy_weekly,
    ) -> None:
        self._portfolio      = portfolio
        self._weekly_returns = weekly_returns
        self._spy_weekly     = spy_weekly
        self._per_ticker_vol  = metrics.get("per_ticker_vol", {})
        self._per_ticker_beta = metrics.get("per_ticker_beta", {})

        # Refresh label colour to pick up current theme
        self._sel_lbl.setStyleSheet(f"color: {_s.TEXT_SECONDARY}; font-weight: bold;")

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

        vol  = self._per_ticker_vol.get(ticker)
        beta = self._per_ticker_beta.get(ticker)
        self._vol_card.set_value(vol, scale=100.0)
        self._beta_card.set_value(beta)

        from compute.ticker_metrics import pairwise_correlations
        if ticker in self._weekly_returns:
            corr_dict = pairwise_correlations(ticker, self._weekly_returns)
            self._fill_corr_table(ticker, corr_dict)
        else:
            self._corr_table.setRowCount(0)

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
            pair_item.setForeground(QColor(_s.TEXT_PRIMARY))
            val_item = QTableWidgetItem(f"{val:+.3f}")
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_item.setForeground(QColor(_corr_color(val)))
            self._corr_table.setItem(row, 0, pair_item)
            self._corr_table.setItem(row, 1, val_item)
        _fit_table(self._corr_table)

    def _fill_impact_table(self, ticker: str, with_m: dict, without_m: dict) -> None:
        self._impact_table.setHorizontalHeaderLabels(
            [f"With {ticker}", f"Without {ticker}", "Net Change"]
        )
        rows = [
            ("portfolio_beta",  1.0,   "{:+.3f}", 0.5),
            ("portfolio_vol",   100.0, "{:.1f}%", 10.0),
            ("avg_correlation", 1.0,   "{:+.3f}", 0.3),
        ]
        for i, (key, scale, fmt, max_intensity) in enumerate(rows):
            v_with    = with_m.get(key)
            v_without = without_m.get(key)

            with_item = QTableWidgetItem(
                fmt.format(v_with * scale) if v_with is not None else "—"
            )
            with_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            with_item.setForeground(QColor(_s.TEXT_PRIMARY))
            self._impact_table.setItem(i, 0, with_item)

            without_item = QTableWidgetItem(
                fmt.format(v_without * scale) if v_without is not None else "—"
            )
            without_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            without_item.setForeground(QColor(_s.TEXT_SECONDARY))
            self._impact_table.setItem(i, 1, without_item)

            if v_with is not None and v_without is not None:
                delta = (v_with - v_without) * scale
                delta_item = QTableWidgetItem(fmt.format(delta))
                delta_item.setForeground(QColor(_delta_color(delta, max_intensity)))
            else:
                delta_item = QTableWidgetItem("—")
                delta_item.setForeground(QColor(_s.TEXT_SECONDARY))
            delta_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._impact_table.setItem(i, 2, delta_item)

        _fit_table(self._impact_table)

    def _clear_impact_table(self) -> None:
        for i in range(3):
            for j in range(3):
                item = QTableWidgetItem("—")
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item.setForeground(QColor(_s.TEXT_SECONDARY))
                self._impact_table.setItem(i, j, item)

    def _clear(self) -> None:
        self._vol_card.set_value(None)
        self._beta_card.set_value(None)
        self._corr_table.setRowCount(0)
        self._clear_impact_table()
