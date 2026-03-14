"""
TickerInputDialog — dialog for adding a new position.

No network validation happens here.  The dialog accepts any non-empty
ticker string immediately.  The background fetch in MainWindow will detect
an invalid ticker (empty data returned) and clean it up with an error message.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDoubleSpinBox, QRadioButton, QButtonGroup, QPushButton,
    QFrame,
)
from PySide6.QtCore import Qt

import ui.styles as _s


class TickerInputDialog(QDialog):

    def __init__(self, parent=None, prefill_side: str = "long"):
        super().__init__(parent)
        self.setWindowTitle("Add Position")
        self.setModal(True)
        self.setMinimumWidth(360)
        self.result_data: dict | None = None
        self._build_ui(prefill_side)

    def set_validator(self, fn):
        pass  # intentionally no-op — validation is done post-accept

    # ------------------------------------------------------------------
    def _build_ui(self, prefill_side: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Add Position")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {_s.TEXT_PRIMARY};")
        layout.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        layout.addWidget(self._lbl("Ticker Symbol"))
        self._ticker_edit = QLineEdit()
        self._ticker_edit.setPlaceholderText("e.g. AAPL")
        self._ticker_edit.setMaxLength(10)
        self._ticker_edit.textChanged.connect(self._clear_error)
        layout.addWidget(self._ticker_edit)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet(f"color: {_s.RED}; font-size: 11px;")
        self._error_label.hide()
        layout.addWidget(self._error_label)

        layout.addWidget(self._lbl("Side"))
        side_row = QHBoxLayout()
        self._long_radio  = QRadioButton("Long")
        self._short_radio = QRadioButton("Short")
        grp = QButtonGroup(self)
        grp.addButton(self._long_radio,  0)
        grp.addButton(self._short_radio, 1)
        (self._short_radio if prefill_side == "short" else self._long_radio).setChecked(True)
        side_row.addWidget(self._long_radio)
        side_row.addWidget(self._short_radio)
        side_row.addStretch()
        layout.addLayout(side_row)

        layout.addWidget(self._lbl("Position Size (USD)"))
        self._amount_spin = QDoubleSpinBox()
        self._amount_spin.setRange(1.0, 999_999_999.0)
        self._amount_spin.setDecimals(0)
        self._amount_spin.setSingleStep(5_000)
        self._amount_spin.setValue(50_000)
        self._amount_spin.setGroupSeparatorShown(True)
        self._amount_spin.setPrefix("$ ")
        layout.addWidget(self._amount_spin)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        add_btn = QPushButton("Add Position")
        add_btn.setDefault(True)
        add_btn.setStyleSheet(
            f"background: {_s.ACCENT}; color: {_s.BG_MAIN}; border: none;"
            f" border-radius: {_s.BORDER_RADIUS}; padding: 6px 16px; font-weight: bold;"
        )
        add_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(add_btn)
        layout.addLayout(btn_row)

        self._ticker_edit.returnPressed.connect(self._on_accept)

    def _on_accept(self) -> None:
        ticker = self._ticker_edit.text().strip().upper()
        if not ticker:
            self._show_error("Please enter a ticker symbol.")
            return
        self.result_data = {
            "ticker": ticker,
            "side": "long" if self._long_radio.isChecked() else "short",
            "dollar_amount": self._amount_spin.value(),
        }
        self.accept()

    def _show_error(self, msg: str) -> None:
        self._error_label.setText(msg)
        self._error_label.show()

    def _clear_error(self) -> None:
        self._error_label.hide()

    @staticmethod
    def _lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {_s.TEXT_SECONDARY}; font-size: 11px; font-weight: bold;")
        return lbl
