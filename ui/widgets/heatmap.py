"""
HeatmapWidget — reusable matplotlib heatmap embedded in a Qt widget.

Used for both the correlation matrix and the variance-covariance matrix
in Tab 1.  Draws with a RdBu_r diverging colormap.
"""
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from ui.styles import BG_MAIN, BG_PANEL, TEXT_PRIMARY, TEXT_SECONDARY, BORDER


class HeatmapWidget(QWidget):
    """Matplotlib heatmap embedded in a Qt widget."""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._figure = Figure(facecolor=BG_PANEL, tight_layout=True)
        self._canvas = FigureCanvas(self._figure)
        self._canvas.setStyleSheet(f"background: {BG_PANEL};")

        self._placeholder = QLabel("Add 2+ tickers to display matrix")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 12px; background: {BG_PANEL};"
            f" border: 1px solid {BORDER}; border-radius: 4px; padding: 30px;"
        )

        layout.addWidget(self._placeholder)
        layout.addWidget(self._canvas)
        self._canvas.hide()

    # ------------------------------------------------------------------
    def set_matrix(self, df: pd.DataFrame, fmt: str = ".2f") -> None:
        """
        Render the DataFrame as a coloured heatmap.

        df   : square DataFrame (tickers as index and columns)
        fmt  : cell value format string
        """
        if df is None or df.empty or df.shape[0] < 2:
            self._show_placeholder()
            return

        self._placeholder.hide()
        self._canvas.show()

        self._figure.clear()
        ax = self._figure.add_subplot(111)

        n = df.shape[0]
        vals = df.values.astype(float)

        # Determine symmetric colour limits
        abs_max = max(abs(np.nanmin(vals)), abs(np.nanmax(vals)))
        if abs_max == 0:
            abs_max = 1.0
        vmin, vmax = -abs_max, abs_max

        im = ax.imshow(vals, cmap="RdBu_r", vmin=vmin, vmax=vmax, aspect="auto")

        # Axes labels
        tickers = list(df.columns)
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(tickers, rotation=45, ha="right",
                           fontsize=9, color=TEXT_PRIMARY)
        ax.set_yticklabels(tickers, fontsize=9, color=TEXT_PRIMARY)
        ax.tick_params(colors=TEXT_PRIMARY, length=0)

        # Value annotations inside cells
        for i in range(n):
            for j in range(n):
                v = vals[i, j]
                if not np.isnan(v):
                    text_color = "white" if abs(v) > abs_max * 0.5 else TEXT_PRIMARY
                    ax.text(
                        j, i,
                        f"{v:{fmt}}",
                        ha="center", va="center",
                        fontsize=8, color=text_color,
                    )

        # Title
        if self._title:
            ax.set_title(self._title, color=TEXT_SECONDARY, fontsize=10, pad=8)

        # Style
        ax.set_facecolor(BG_PANEL)
        self._figure.patch.set_facecolor(BG_PANEL)
        for spine in ax.spines.values():
            spine.set_edgecolor(BORDER)

        # Colorbar
        cbar = self._figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.ax.yaxis.set_tick_params(color=TEXT_SECONDARY, labelsize=8)
        plt_objs = cbar.ax.get_yticklabels()
        for lbl in plt_objs:
            lbl.set_color(TEXT_SECONDARY)
        cbar.outline.set_edgecolor(BORDER)

        self._canvas.draw()

    def clear(self) -> None:
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        self._canvas.hide()
        self._placeholder.show()
        self._figure.clear()
