"""
HeatmapWidget — reusable matplotlib heatmap embedded in a Qt widget.

Used for both the correlation matrix and the variance-covariance matrix
in Tab 1.  Draws with a RdBu_r diverging colormap.
"""
import numpy as np
import pandas as pd
import matplotlib.cm as _mcm
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

import ui.styles as _s


class _Canvas(FigureCanvas):
    """FigureCanvas that passes wheel events to the parent scroll area."""
    def wheelEvent(self, event):
        event.ignore()


class HeatmapWidget(QWidget):
    """
    Renders a square DataFrame as a coloured heatmap using matplotlib.

    Call set_matrix(df) to update the display.
    """

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self._title = title

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._figure = Figure(figsize=(5, 4), facecolor=_s.BG_PANEL, tight_layout=True)
        self._canvas = _Canvas(self._figure)
        self._canvas.setStyleSheet(f"background: {_s.BG_PANEL};")

        self._placeholder = QLabel("Not enough data")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            f"color: {_s.TEXT_SECONDARY}; font-size: 12px; background: {_s.BG_PANEL};"
            f" border: 1px solid {_s.BORDER}; padding: 20px;"
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

        ax.imshow(vals, cmap="RdBu_r", vmin=vmin, vmax=vmax, aspect="auto")

        # Axes labels
        tickers = list(df.columns)
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(tickers, rotation=45, ha="right",
                           fontsize=9, color=_s.TEXT_PRIMARY)
        ax.set_yticklabels(tickers, fontsize=9, color=_s.TEXT_PRIMARY)
        ax.tick_params(colors=_s.TEXT_PRIMARY, length=0)

        # Value annotations — choose text colour by cell luminance
        cmap = _mcm.get_cmap("RdBu_r")
        for i in range(n):
            for j in range(n):
                v = vals[i, j]
                if not np.isnan(v):
                    norm_v = (v - vmin) / (vmax - vmin) if vmax != vmin else 0.5
                    r, g, b, _ = cmap(float(np.clip(norm_v, 0, 1)))
                    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
                    text_color = "#1A1A2E" if luminance > 0.35 else "white"
                    ax.text(
                        j, i,
                        f"{v:{fmt}}",
                        ha="center", va="center",
                        fontsize=8, color=text_color,
                        fontweight="bold",
                    )

        # Title
        if self._title:
            ax.set_title(self._title, color=_s.TEXT_SECONDARY, fontsize=10, pad=6)

        for spine in ax.spines.values():
            spine.set_edgecolor(_s.BORDER)

        ax.set_facecolor(_s.BG_PANEL)
        self._figure.patch.set_facecolor(_s.BG_PANEL)

        self._canvas.draw()

    def clear(self) -> None:
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        self._canvas.hide()
        self._placeholder.show()
        self._figure.clear()
