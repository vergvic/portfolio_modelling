"""
Tab 3 — Distribution of Returns

Two stacked panels, each with:
  - HistogramWidget (frequency bars + cumulative probability overlay)
  - Three-column stats area:
      Left:   Descriptive stats table
      Middle: Positive/Negative/Zero split + SD bounds vs normal
      Right:  Percentile distribution

Uses monthly data (full history) for both C-C and H-L return series.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QScrollArea, QFrame, QSizePolicy, QAbstractScrollArea,
    QDoubleSpinBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ui.widgets.histogram import HistogramWidget
import ui.styles as _s


class TabDoR(QWidget):
    """Tab 3: Distribution of Returns."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dor_data: dict = {}
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Ticker selector
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

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        # Stops & Targets block (ticker-level, not per-panel)
        self._stops_widget = _StopsTargetsWidget()
        content_layout.addWidget(self._stops_widget)

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
        self._dor_data = dor_data
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

    def _on_ticker_changed(self, ticker: str) -> None:
        self._stops_widget.reset()
        if not ticker or ticker not in self._dor_data:
            self._cc_panel.clear()
            self._hl_panel.clear()
            return

        dor = self._dor_data[ticker]
        self._cc_panel.set_data(dor.get("cc", {}), ticker)
        self._hl_panel.set_data(dor.get("hl", {}), ticker)


# ---------------------------------------------------------------------------
# Stops & Targets widget
# ---------------------------------------------------------------------------

class _StopsTargetsWidget(QGroupBox):
    """
    Interactive R:R estimator.
    User enters Stop %, Target %, and Current Price.
    Stop Price and Target Price are computed and displayed instantly.
    Values are not persisted — reset when the widget is hidden/cleared.
    """

    def __init__(self, parent=None):
        super().__init__("Stops & Targets", parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 16, 10, 10)
        root.setSpacing(10)

        # ── Row 1: inputs ────────────────────────────────────────────
        inputs_row = QHBoxLayout()
        inputs_row.setSpacing(24)

        def _lbl(text):
            l = QLabel(text)
            l.setStyleSheet(f"color: {_s.TEXT_SECONDARY}; font-size: 11px;")
            return l

        stop_col = QVBoxLayout()
        stop_col.addWidget(_lbl("Stop %"))
        self._stop_spin = QDoubleSpinBox()
        self._stop_spin.setRange(0.0, 100.0)
        self._stop_spin.setDecimals(1)
        self._stop_spin.setSuffix(" %")
        self._stop_spin.setMinimumWidth(110)
        stop_col.addWidget(self._stop_spin)
        inputs_row.addLayout(stop_col)

        target_col = QVBoxLayout()
        target_col.addWidget(_lbl("Target %"))
        self._target_spin = QDoubleSpinBox()
        self._target_spin.setRange(0.0, 1000.0)
        self._target_spin.setDecimals(1)
        self._target_spin.setSuffix(" %")
        self._target_spin.setMinimumWidth(110)
        target_col.addWidget(self._target_spin)
        inputs_row.addLayout(target_col)

        price_col = QVBoxLayout()
        price_col.addWidget(_lbl("Current Price"))
        self._price_spin = QDoubleSpinBox()
        self._price_spin.setRange(0.0, 9_999_999.0)
        self._price_spin.setDecimals(2)
        self._price_spin.setMinimumWidth(130)
        price_col.addWidget(self._price_spin)
        inputs_row.addLayout(price_col)

        inputs_row.addStretch()
        root.addLayout(inputs_row)

        # ── Row 2: computed outputs ───────────────────────────────────
        outputs_row = QHBoxLayout()
        outputs_row.setSpacing(32)

        def _result_pair(caption):
            col = QVBoxLayout()
            cap = QLabel(caption)
            cap.setStyleSheet(f"color: {_s.TEXT_SECONDARY}; font-size: 11px;")
            val = QLabel("—")
            val.setStyleSheet(
                f"color: {_s.TEXT_PRIMARY}; font-size: 15px; font-weight: bold;"
            )
            col.addWidget(cap)
            col.addWidget(val)
            return col, val

        stop_out_col,   self._stop_price_lbl   = _result_pair("Stop Price")
        target_out_col, self._target_price_lbl = _result_pair("Target Price")
        outputs_row.addLayout(stop_out_col)
        outputs_row.addLayout(target_out_col)
        outputs_row.addStretch()
        root.addLayout(outputs_row)

        self._stop_spin.valueChanged.connect(self._recompute)
        self._target_spin.valueChanged.connect(self._recompute)
        self._price_spin.valueChanged.connect(self._recompute)

    # ------------------------------------------------------------------
    def _recompute(self) -> None:
        price  = self._price_spin.value()
        stop_p = self._stop_spin.value() / 100.0
        tgt_p  = self._target_spin.value() / 100.0

        if price > 0:
            self._stop_price_lbl.setText(f"{price * (1.0 - stop_p):,.2f}")
            self._target_price_lbl.setText(f"{price * (1.0 + tgt_p):,.2f}")
        else:
            self._stop_price_lbl.setText("—")
            self._target_price_lbl.setText("—")

    def reset(self) -> None:
        for spin in (self._stop_spin, self._target_spin, self._price_spin):
            spin.blockSignals(True)
            spin.setValue(0.0)
            spin.blockSignals(False)
        self._stop_price_lbl.setText("—")
        self._target_price_lbl.setText("—")


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

        # Stats row — three panels side by side
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        # Left: descriptive stats
        self._stats_table = _make_two_col_table(["Statistic", "Value"])
        stats_row.addWidget(self._stats_table, stretch=1)

        # Middle: pos/neg/zero + SD bounds
        middle = QVBoxLayout()
        middle.setSpacing(8)

        self._pnz_table = _make_two_col_table(["", "Positive", "Negative", "Zero"], cols=4)
        self._sd_table  = _make_two_col_table(["Bound", "Actual %", "Normal %"], cols=3)
        lbl_pnz = QLabel("Pos / Neg / Zero Split")
        lbl_pnz.setStyleSheet(f"color: {_s.TEXT_SECONDARY}; font-size: 11px; font-weight: bold;")
        lbl_sd = QLabel("SD Bounds vs Normal")
        lbl_sd.setStyleSheet(f"color: {_s.TEXT_SECONDARY}; font-size: 11px; font-weight: bold;")
        middle.addWidget(lbl_pnz)
        middle.addWidget(self._pnz_table)
        middle.addWidget(lbl_sd)
        middle.addWidget(self._sd_table)
        middle.addStretch()
        stats_row.addLayout(middle, stretch=1)

        # Right: percentile distribution
        pct_col = QVBoxLayout()
        pct_col.setSpacing(8)
        lbl_pct = QLabel("Percentile Distribution")
        lbl_pct.setStyleSheet(f"color: {_s.TEXT_SECONDARY}; font-size: 11px; font-weight: bold;")
        self._pct_table = _make_two_col_table(["Percentile", "Return"])
        pct_col.addWidget(lbl_pct)
        pct_col.addWidget(self._pct_table)
        pct_col.addStretch()
        stats_row.addLayout(pct_col, stretch=1)

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
            name_item.setForeground(QColor(_s.TEXT_SECONDARY))
            self._stats_table.setItem(row, 0, name_item)
            val_str  = fmt.format(val) if val is not None else "—"
            val_item = QTableWidgetItem(val_str)
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_item.setForeground(QColor(_s.TEXT_PRIMARY))
            self._stats_table.setItem(row, 1, val_item)
        _fit_table(self._stats_table)

        # Pos/Neg/Zero table
        pnz_rows = [
            ("Count",        "count",           "{:.0f}"),
            ("Avg Return",   "avg_return",      "{:+.4f}"),
            ("Freq %",       "freq_pct",        "{:.1%}"),
            ("Freq-Adj Ret", "freq_adj_return", "{:+.4f}"),
        ]
        self._pnz_table.setColumnCount(4)
        self._pnz_table.setHorizontalHeaderLabels(["", "Positive", "Negative", "Zero"])
        self._pnz_table.setRowCount(len(pnz_rows))
        for row, (label, key, fmt) in enumerate(pnz_rows):
            lbl_item = QTableWidgetItem(label)
            lbl_item.setForeground(QColor(_s.TEXT_SECONDARY))
            self._pnz_table.setItem(row, 0, lbl_item)
            for col, bucket in enumerate(("positive", "negative", "zero"), start=1):
                bdata = split.get(bucket, {})
                raw   = bdata.get(key)
                text  = fmt.format(raw) if raw is not None else "—"
                item  = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                color = _s.GREEN if bucket == "positive" else (_s.RED if bucket == "negative" else _s.TEXT_SECONDARY)
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

        # Percentile table
        pcts = dor_section.get("percentiles", [])
        self._pct_table.setRowCount(len(pcts))
        for row, p in enumerate(pcts):
            level_item = _plain(f"{p['level']:.0%}")
            self._pct_table.setItem(row, 0, level_item)
            val      = p["value"]
            val_item = QTableWidgetItem(f"{val:+.4f}")
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_item.setForeground(QColor(_s.GREEN if val > 0 else _s.RED))
            self._pct_table.setItem(row, 1, val_item)
        _fit_table(self._pct_table)

    def clear(self) -> None:
        self._histogram.clear()
        self._stats_table.setRowCount(0)
        self._pnz_table.setRowCount(0)
        self._sd_table.setRowCount(0)
        self._pct_table.setRowCount(0)


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
    item.setForeground(QColor(_s.TEXT_SECONDARY))
    return item


def _pct_item(val: float | None, secondary: bool = False) -> QTableWidgetItem:
    text = f"{val:.1%}" if val is not None else "—"
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    item.setForeground(QColor(_s.TEXT_SECONDARY if secondary else _s.TEXT_PRIMARY))
    return item
