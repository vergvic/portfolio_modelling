"""
Tab 3 — Distribution of Returns

Two stacked panels, each with:
  - HistogramWidget (frequency bars + cumulative probability overlay)
  - Two-column stats area:
      Left:  Descriptive stats table
      Right: Positive/Negative/Zero split + SD bounds vs normal

Uses monthly data (full history) for both C-C and H-L return series.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QScrollArea, QFrame, QSizePolicy, QAbstractScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from ui.widgets.histogram import HistogramWidget
from ui.styles import TEXT_SECONDARY, TEXT_PRIMARY, GREEN, RED, ORANGE, NEUTRAL


class TabDoR(QWidget):
    """Tab 3: Distribution of Returns."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dor_data: dict = {}   # {ticker: compute_dor() output}
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Ticker selector
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

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        # Two panels
        self._cc_panel = _DorPanel("Close-to-Close Returns")
        self._hl_panel = _DorPanel("High-to-Low Returns")
        content_layout.addWidget(self._cc_panel)
        content_layout.addWidget(self._hl_panel)
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    # ------------------------------------------------------------------
    def refresh_display(self, portfolio: list[dict], dor_data: dict) -> None:
        """
        Called by MainWindow when portfolio or data changes.

        dor_data: {ticker: compute_dor() result}
        """
        self._dor_data = dor_data
        current = self._combo.currentText()

        self._combo.blockSignals(True)
        self._combo.clear()
        tickers = [p["ticker"] for p in portfolio]
        self._combo.addItems(tickers)
        if current in tickers:
            self._combo.setCurrentText(current)
        self._combo.blockSignals(False)

        self._on_ticker_changed(self._combo.currentText())

    def _on_ticker_changed(self, ticker: str) -> None:
        if not ticker or ticker not in self._dor_data:
            self._cc_panel.clear()
            self._hl_panel.clear()
            return

        dor = self._dor_data[ticker]
        self._cc_panel.set_data(dor.get("cc", {}), ticker)
        self._hl_panel.set_data(dor.get("hl", {}), ticker)


# ---------------------------------------------------------------------------
# Internal panel widget
# ---------------------------------------------------------------------------

class _DorPanel(QGroupBox):
    """One DoR analysis panel (C-C or H-L)."""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 16, 10, 10)
        root.setSpacing(10)

        # Histogram
        self._histogram = HistogramWidget()
        self._histogram.setMinimumHeight(280)
        root.addWidget(self._histogram)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        # Left: descriptive stats
        self._stats_table = _make_two_col_table(["Statistic", "Value"])
        stats_row.addWidget(self._stats_table, stretch=1)

        # Right: pos/neg/zero + SD bounds
        right = QVBoxLayout()
        right.setSpacing(8)

        self._pnz_table  = _make_two_col_table(["", "Positive", "Negative", "Zero"],
                                                cols=4)
        self._sd_table   = _make_two_col_table(["Bound", "Actual %", "Normal %"],
                                               cols=3)
        right.addWidget(QLabel("Pos / Neg / Zero Split"))
        right.addWidget(self._pnz_table)
        right.addWidget(QLabel("SD Bounds vs Normal"))
        right.addWidget(self._sd_table)

        for lbl in self.findChildren(QLabel):
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: bold;")

        stats_row.addLayout(right, stretch=1)
        root.addLayout(stats_row)

    # ------------------------------------------------------------------
    def set_data(self, dor_section: dict, ticker: str) -> None:
        if not dor_section:
            self.clear()
            return

        freq_df = dor_section.get("freq_dist")
        stats   = dor_section.get("stats", {})
        split   = dor_section.get("split", {})
        bounds  = dor_section.get("sd_bounds", [])

        # Histogram
        self._histogram.set_data(freq_df, ticker)

        # Descriptive stats table
        stat_rows = [
            ("Mean",           stats.get("mean"),           "{:+.4f}"),
            ("Std Error",      stats.get("standard_error"), "{:.4f}"),
            ("Median",         stats.get("median"),         "{:+.4f}"),
            ("Mode",           stats.get("mode"),           "{:+.4f}"),
            ("Std Dev",        stats.get("std_dev"),        "{:.4f}"),
            ("Variance",       stats.get("variance"),       "{:.6f}"),
            ("Kurtosis",       stats.get("kurtosis"),       "{:.4f}"),
            ("Skewness",       stats.get("skewness"),       "{:+.4f}"),
            ("Range",          stats.get("range"),          "{:.4f}"),
            ("Minimum",        stats.get("minimum"),        "{:+.4f}"),
            ("Maximum",        stats.get("maximum"),        "{:+.4f}"),
            ("Sum",            stats.get("sum"),            "{:+.4f}"),
            ("Count",          stats.get("count"),          "{:.0f}"),
        ]
        self._stats_table.setRowCount(len(stat_rows))
        for row, (name, val, fmt) in enumerate(stat_rows):
            name_item = QTableWidgetItem(name)
            name_item.setForeground(QColor(TEXT_SECONDARY))
            self._stats_table.setItem(row, 0, name_item)
            val_str = fmt.format(val) if val is not None else "—"
            val_item = QTableWidgetItem(val_str)
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_item.setForeground(QColor(TEXT_PRIMARY))
            self._stats_table.setItem(row, 1, val_item)
        _fit_table(self._stats_table)

        # Pos/Neg/Zero table
        self._pnz_table.setRowCount(3)
        pnz_rows = [
            ("Count",        "count",          "{:.0f}"),
            ("Avg Return",   "avg_return",     "{:+.4f}"),
            ("Freq %",       "freq_pct",       "{:.1%}"),
            ("Freq-Adj Ret", "freq_adj_return","{:+.4f}"),
        ]
        self._pnz_table.setColumnCount(4)
        self._pnz_table.setHorizontalHeaderLabels(["", "Positive", "Negative", "Zero"])
        self._pnz_table.setRowCount(len(pnz_rows))
        for row, (label, key, fmt) in enumerate(pnz_rows):
            lbl_item = QTableWidgetItem(label)
            lbl_item.setForeground(QColor(TEXT_SECONDARY))
            self._pnz_table.setItem(row, 0, lbl_item)
            for col, bucket in enumerate(("positive", "negative", "zero"), start=1):
                bdata = split.get(bucket, {})
                raw = bdata.get(key)
                text = fmt.format(raw) if raw is not None else "—"
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                color = GREEN if bucket == "positive" else (RED if bucket == "negative" else TEXT_SECONDARY)
                item.setForeground(QColor(color))
                self._pnz_table.setItem(row, col, item)
        _fit_table(self._pnz_table)

        # SD bounds table
        self._sd_table.setRowCount(len(bounds))
        for row, bound in enumerate(bounds):
            sig = bound.get("sigma")
            act = bound.get("actual_pct")
            nrm = bound.get("normal_pct")
            self._sd_table.setItem(row, 0, _plain(f"{sig}σ  ({bound['lower']:.3f} – {bound['upper']:.3f})"))
            self._sd_table.setItem(row, 1, _pct_item(act))
            self._sd_table.setItem(row, 2, _pct_item(nrm, secondary=True))
        _fit_table(self._sd_table)

    def clear(self) -> None:
        self._histogram.clear()
        self._stats_table.setRowCount(0)
        self._pnz_table.setRowCount(0)
        self._sd_table.setRowCount(0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _PassThroughTable(QTableWidget):
    """QTableWidget that passes wheel events up to the parent scroll area."""
    def wheelEvent(self, event):
        event.ignore()


def _fit_table(t: QTableWidget) -> None:
    """Set minimum height so every row is visible — no internal scrolling."""
    h = t.horizontalHeader().height() + 2
    for i in range(t.rowCount()):
        h += t.rowHeight(i)
    t.setMinimumHeight(h)


def _make_two_col_table(headers: list[str], cols: int = 2) -> QTableWidget:
    t = _PassThroughTable(0, cols)
    t.setHorizontalHeaderLabels(headers)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    t.verticalHeader().hide()
    t.setAlternatingRowColors(True)
    t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    t.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
    t.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
    t.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return t


def _plain(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setForeground(QColor(TEXT_SECONDARY))
    return item


def _pct_item(val: float | None, secondary: bool = False) -> QTableWidgetItem:
    text = f"{val:.1%}" if val is not None else "—"
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    item.setForeground(QColor(TEXT_SECONDARY if secondary else TEXT_PRIMARY))
    return item
