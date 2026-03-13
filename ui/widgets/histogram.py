"""
HistogramWidget — matplotlib histogram with cumulative probability overlay.

Used in Tab 3 (Distribution of Returns) for both C-C and H-L panels.
"""
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from ui.styles import (
    BG_PANEL, TEXT_PRIMARY, TEXT_SECONDARY, BORDER, ACCENT, GREEN, NEUTRAL
)


class _Canvas(FigureCanvas):
    """FigureCanvas that passes wheel events to the parent scroll area."""
    def wheelEvent(self, event):
        event.ignore()


class HistogramWidget(QWidget):
    """
    Histogram of return frequencies with a right-axis cumulative probability line.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._figure = Figure(figsize=(6, 3), facecolor=BG_PANEL, tight_layout=True)
        self._canvas = _Canvas(self._figure)
        self._canvas.setStyleSheet(f"background: {BG_PANEL};")

        self._placeholder = QLabel("Select a ticker to view distribution")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px; background: {BG_PANEL};"
            f" border: 1px solid {BORDER}; border-radius: 4px; padding: 20px;"
        )

        layout.addWidget(self._placeholder)
        layout.addWidget(self._canvas)
        self._canvas.hide()

    # ------------------------------------------------------------------
    def set_data(self, freq_df: pd.DataFrame, ticker: str = "") -> None:
        """
        Draw the histogram from a frequency_distribution DataFrame.

        freq_df columns: bin_label, lower, upper, count, probability, cumulative_pct
        """
        if freq_df is None or freq_df.empty:
            self._show_placeholder()
            return

        self._placeholder.hide()
        self._canvas.show()
        self._figure.clear()

        ax = self._figure.add_subplot(111)
        ax2 = ax.twinx()  # right axis for cumulative %

        # Bar positions: mid-point of each bin
        midpoints = (freq_df["lower"] + freq_df["upper"]) / 2
        widths = freq_df["upper"] - freq_df["lower"]
        probs = freq_df["probability"].values

        bar_colors = [ACCENT if p > 0 else BORDER for p in probs]

        ax.bar(
            midpoints, probs, width=widths * 0.9,
            color=bar_colors, alpha=0.85, linewidth=0,
        )

        # Cumulative probability line on right axis
        cum = freq_df["cumulative_pct"].values
        ax2.plot(midpoints, cum * 100, color=GREEN, linewidth=2, marker="o",
                 markersize=3, label="Cumulative %")
        ax2.set_ylim(0, 105)
        ax2.set_ylabel("Cumulative %", color=TEXT_SECONDARY, fontsize=9)
        ax2.tick_params(axis="y", colors=TEXT_SECONDARY, labelsize=8)

        # X axis: use % format
        x_ticks = midpoints.values[::max(1, len(midpoints) // 8)]
        ax.set_xticks(x_ticks)
        ax.set_xticklabels([f"{v*100:.0f}%" for v in x_ticks],
                           rotation=45, ha="right", fontsize=8, color=TEXT_PRIMARY)

        ax.set_ylabel("Frequency", color=TEXT_SECONDARY, fontsize=9)
        ax.tick_params(axis="y", colors=TEXT_SECONDARY, labelsize=8)
        ax.tick_params(axis="x", colors=TEXT_PRIMARY)

        title = f"{ticker} — Return Distribution" if ticker else "Return Distribution"
        ax.set_title(title, color=TEXT_SECONDARY, fontsize=10, pad=6)

        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)
        for spine in ax2.spines.values():
            spine.set_edgecolor(BORDER)

        ax.set_facecolor(BG_PANEL)
        self._figure.patch.set_facecolor(BG_PANEL)

        self._canvas.draw()

    def clear(self) -> None:
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        self._canvas.hide()
        self._placeholder.show()
        self._figure.clear()
