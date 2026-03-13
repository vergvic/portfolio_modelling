"""
Tab 1 — Portfolio Overview

Layout (top → bottom, inside a single outer QScrollArea):
  1. Row of 3 MetricCards: Portfolio Vol, Portfolio Beta, Avg Pairwise Correlation
  2. Two TickerListWidgets side-by-side: Longs | Shorts (each with Add button)
  3. Two HeatmapWidgets side-by-side: Correlation Matrix | Var-Covar Matrix
  4. Refresh Data button (bottom-right)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QPushButton, QLabel, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt

from config import VOL_TARGET, BETA_TARGET, CORR_TARGET
from ui.widgets.metric_card  import MetricCard
from ui.widgets.heatmap      import HeatmapWidget
from ui.widgets.ticker_list  import TickerListWidget
from ui.styles               import TEXT_SECONDARY, BORDER


class TabPortfolio(QWidget):
    add_position_requested    = Signal(str)   # 'long' or 'short'
    remove_position_requested = Signal(str)   # ticker
    refresh_data_requested    = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # Outer layout holds only the scroll area — no margins here
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

        # ── Row 1: Metric cards ───────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        self._vol_card  = MetricCard("Portfolio Volatility", unit="%", fmt=".1f")
        self._beta_card = MetricCard("Portfolio Beta",       unit="",  fmt=".2f")
        self._corr_card = MetricCard("Avg Pairwise Corr",   unit="",  fmt=".2f")

        for card in (self._vol_card, self._beta_card, self._corr_card):
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cards_row.addWidget(card)

        root.addLayout(cards_row)

        # ── Row 2: Ticker lists ───────────────────────────────────────
        lists_row = QHBoxLayout()
        lists_row.setSpacing(12)

        self._longs_list  = TickerListWidget("long")
        self._shorts_list = TickerListWidget("short")

        self._longs_list.add_requested.connect(self.add_position_requested)
        self._shorts_list.add_requested.connect(self.add_position_requested)
        self._longs_list.ticker_removed.connect(self.remove_position_requested)
        self._shorts_list.ticker_removed.connect(self.remove_position_requested)

        lists_row.addWidget(self._longs_list)
        lists_row.addWidget(self._shorts_list)
        root.addLayout(lists_row)

        # ── Row 3: Heatmaps ───────────────────────────────────────────
        heat_row = QHBoxLayout()
        heat_row.setSpacing(12)

        self._corr_heatmap  = HeatmapWidget("Correlation Matrix")
        self._covar_heatmap = HeatmapWidget("Var-Covar Matrix (annualised)")

        for hw in (self._corr_heatmap, self._covar_heatmap):
            hw.setMinimumHeight(460)
            hw.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            heat_row.addWidget(hw)

        root.addLayout(heat_row)

        # ── Row 4: Refresh button ─────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        refresh_btn = QPushButton("↻  Refresh Data")
        refresh_btn.setObjectName("RefreshButton")
        refresh_btn.clicked.connect(self.refresh_data_requested)
        btn_row.addWidget(refresh_btn)
        root.addLayout(btn_row)

        root.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    def refresh_display(self, portfolio: list[dict], metrics: dict) -> None:
        self._longs_list.set_positions(portfolio)
        self._shorts_list.set_positions(portfolio)

        vol  = metrics.get("portfolio_vol")
        beta = metrics.get("portfolio_beta")
        corr = metrics.get("avg_correlation")

        self._vol_card.set_value(vol,  target_range=VOL_TARGET,  scale=100.0)
        self._beta_card.set_value(beta, target_range=BETA_TARGET, scale=1.0)
        self._corr_card.set_value(corr, target_range=CORR_TARGET, scale=1.0)

        corr_matrix = metrics.get("corr_matrix")
        cov_matrix  = metrics.get("cov_matrix")

        if corr_matrix is not None and not corr_matrix.empty:
            self._corr_heatmap.set_matrix(corr_matrix, fmt=".2f")
        else:
            self._corr_heatmap.clear()

        if cov_matrix is not None and not cov_matrix.empty:
            self._covar_heatmap.set_matrix(cov_matrix, fmt=".4f")
        else:
            self._covar_heatmap.clear()
