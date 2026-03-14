"""
TickerListWidget — grouped list of positions (longs or shorts).

Features:
- Displays TICKER  $XX,XXX sorted by position size (largest first)
- Right-click or Delete key removes a position
- Emits ticker_removed(str) signal
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMenu, QAbstractItemView,
    QAbstractScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QAction

import ui.styles as _s


class TickerListWidget(QWidget):
    """
    Displays a group of positions (all longs or all shorts).

    Signals
    -------
    ticker_removed(str)  : emitted when a position is removed by the user
    add_requested(str)   : emitted when the '+ Add' button is clicked
                           (the str argument is the side: 'long' or 'short')
    """

    ticker_removed = Signal(str)
    add_requested  = Signal(str)

    def __init__(self, side: str, parent=None):
        """
        side: 'long' or 'short'
        """
        super().__init__(parent)
        self._side = side
        self._positions: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header row
        hdr = QHBoxLayout()
        label_text = "LONGS" if side == "long" else "SHORTS"
        self._hdr_label = QLabel(label_text)
        self._hdr_label.setStyleSheet(
            f"color: {_s.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        add_btn = QPushButton(f"+ Add {side.title()}")
        add_btn.setObjectName("AddButton")
        add_btn.clicked.connect(lambda: self.add_requested.emit(self._side))

        hdr.addWidget(self._hdr_label)
        hdr.addStretch()
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)

        # List
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.installEventFilter(self)
        self._list.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents
        )
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setMinimumHeight(80)
        layout.addWidget(self._list)

    # ------------------------------------------------------------------
    def set_positions(self, positions: list[dict]) -> None:
        """
        Refresh the list with new position data.

        positions: list of {ticker, side, dollar_amount}
                   (only those matching self._side are shown)
        """
        self._positions = [p for p in positions if p["side"] == self._side]
        self._positions.sort(key=lambda p: p["dollar_amount"], reverse=True)
        self._rebuild_list()

    def get_tickers(self) -> list[str]:
        return [p["ticker"] for p in self._positions]

    # ------------------------------------------------------------------
    def _rebuild_list(self) -> None:
        self._hdr_label.setStyleSheet(
            f"color: {_s.TEXT_SECONDARY}; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
        )
        self._list.clear()
        for pos in self._positions:
            item = QListWidgetItem(
                f"  {pos['ticker']:<8}  ${pos['dollar_amount']:>12,.0f}"
            )
            item.setData(Qt.ItemDataRole.UserRole, pos["ticker"])
            item.setFont(self._monospace_font())
            self._list.addItem(item)
        # Expand to show every row — outer scroll area handles overflow
        n     = self._list.count()
        row_h = self._list.sizeHintForRow(0) if n > 0 else 28
        self._list.setMinimumHeight(max(80, n * row_h + 4))

    def _current_ticker(self) -> str | None:
        item = self._list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _remove_selected(self) -> None:
        ticker = self._current_ticker()
        if ticker:
            self.ticker_removed.emit(ticker)

    def _show_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        ticker = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        remove_action = QAction(f"Remove {ticker}", self)
        remove_action.triggered.connect(lambda: self.ticker_removed.emit(ticker))
        menu.addAction(remove_action)
        menu.exec(self._list.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    def eventFilter(self, obj, event) -> bool:
        from PySide6.QtCore import QEvent
        if obj is self._list and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                self._remove_selected()
                return True
        return super().eventFilter(obj, event)

    @staticmethod
    def _monospace_font():
        from PySide6.QtGui import QFont
        font = QFont("Consolas", 11)
        return font
