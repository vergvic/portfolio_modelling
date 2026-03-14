"""
MetricCard — a self-contained widget that displays a single big KPI number.

Usage:
    card = MetricCard("Portfolio Volatility", unit="%", fmt=".1f")
    card.set_value(18.4, target_range=(15.0, 30.0))   # colour = GREEN
    card.set_value(None)                                # colour = NEUTRAL / "—"
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

import ui.styles as _s


class MetricCard(QFrame):
    """Single big-number KPI display with traffic-light colouring."""

    def __init__(
        self,
        label: str,
        unit: str = "",
        fmt: str = ".3f",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self._unit  = unit
        self._fmt   = fmt

        self.setMinimumWidth(180)
        self.setMinimumHeight(90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._label.setStyleSheet(
            f"color: {_s.TEXT_SECONDARY}; font-size: 11px; font-weight: bold;"
        )

        self._value_label = QLabel("—")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._value_label.setStyleSheet(
            f"color: {_s.NEUTRAL}; font-size: 28px; font-weight: bold;"
        )

        layout.addWidget(self._label)
        layout.addWidget(self._value_label)
        layout.addStretch()

    # ------------------------------------------------------------------
    def set_value(
        self,
        value: float | None,
        target_range: tuple[float, float] | None = None,
        scale: float = 1.0,
    ) -> None:
        """
        Update the displayed number.

        value        : raw float (e.g. 0.184 for 18.4%)
        target_range : (low, high) in the same scale as *value*
        scale        : multiply before display (e.g. 100 to convert 0.184 → 18.4)
        """
        # Refresh label colours to pick up current theme
        self._label.setStyleSheet(
            f"color: {_s.TEXT_SECONDARY}; font-size: 11px; font-weight: bold;"
        )

        if value is None:
            self._value_label.setText("—")
            self._value_label.setStyleSheet(
                f"color: {_s.NEUTRAL}; font-size: 28px; font-weight: bold;"
            )
            return

        display = value * scale
        text    = f"{display:{self._fmt}}{self._unit}"
        self._value_label.setText(text)

        if target_range is not None:
            lo, hi = target_range[0] * scale, target_range[1] * scale
            colour = _s.traffic_light(display, (lo, hi))
        else:
            colour = _s.TEXT_PRIMARY

        self._value_label.setStyleSheet(
            f"color: {colour}; font-size: 28px; font-weight: bold;"
        )

    def set_label(self, text: str) -> None:
        self._label.setText(text)
