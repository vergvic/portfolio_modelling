"""
ThemeEditorDialog — custom theme editor based on 6 seed colours.

The user picks 6 colours that derive every other palette value
mathematically, so the whole app stays visually coherent.

Seed colours
------------
  Background  → BG_MAIN / BG_PANEL (+10) / BG_INPUT (+20)
  Text        → TEXT_PRIMARY / TEXT_SECONDARY (50% toward BG) /
                TEXT_DISABLED (75% toward BG) / NEUTRAL
  Accent      → BORDER / ACCENT / tab underline / header labels
  Positive    → GREEN
  Negative    → RED
  Warning     → ORANGE

Plus 3 style dropdowns: Font, Corners, Border width.

The result is saved to data/custom_theme.json and survives restarts.
"""
from __future__ import annotations
import json
import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QFrame,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QColorDialog

import ui.styles as _s

# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

_CUSTOM_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "custom_theme.json")
)

# Default seed colours for the Custom theme (start from Amber)
_DEFAULT_SEEDS = {
    "bg":     "#080808",
    "text":   "#FFA500",
    "accent": "#B86800",
    "green":  "#6BCF6B",
    "red":    "#FF5555",
    "orange": "#FFD700",
    "font":   '"Courier New", Consolas, monospace',
    "radius": "0px",
    "bw":     "2px",
}


def load_custom_seeds() -> dict:
    """Return saved seed dict, or defaults if no file exists."""
    if os.path.exists(_CUSTOM_PATH):
        try:
            with open(_CUSTOM_PATH, "r", encoding="utf-8") as fh:
                return {**_DEFAULT_SEEDS, **json.load(fh)}
        except Exception:
            pass
    return dict(_DEFAULT_SEEDS)


def save_custom_seeds(seeds: dict) -> None:
    os.makedirs(os.path.dirname(_CUSTOM_PATH), exist_ok=True)
    with open(_CUSTOM_PATH, "w", encoding="utf-8") as fh:
        json.dump(seeds, fh, indent=2)


def load_custom_theme() -> dict:
    """Build a full theme dict from the saved seeds (used at startup)."""
    seeds = load_custom_seeds()
    return _s.derive_full_theme(
        bg     = seeds["bg"],
        text   = seeds["text"],
        accent = seeds["accent"],
        green  = seeds["green"],
        red    = seeds["red"],
        orange = seeds["orange"],
        font   = seeds["font"],
        radius = seeds["radius"],
        bw     = seeds["bw"],
    )


# ---------------------------------------------------------------------------
# Style dropdown options
# ---------------------------------------------------------------------------

_FONT_OPTIONS: list[tuple[str, str]] = [
    ('"Courier New", Consolas, monospace', "Courier New  (monospace / retro)"),
    ("Consolas, monospace",                "Consolas  (monospace / clean)"),
    ('"Segoe UI", Arial, sans-serif',      "Segoe UI  (sans-serif / modern)"),
    ("Arial, sans-serif",                  "Arial  (sans-serif)"),
]

_RADIUS_OPTIONS: list[tuple[str, str]] = [
    ("0px",  "0 px  —  Sharp / Retro"),
    ("3px",  "3 px  —  Slightly rounded"),
    ("6px",  "6 px  —  Rounded / Modern"),
    ("10px", "10 px —  Very rounded"),
]

_BW_OPTIONS: list[tuple[str, str]] = [
    ("1px", "1 px  (thin)"),
    ("2px", "2 px  (standard)"),
    ("3px", "3 px  (thick)"),
]


# ---------------------------------------------------------------------------
# Colour-swatch button
# ---------------------------------------------------------------------------

class _ColorSwatch(QPushButton):
    """Solid-colour button; click opens the system QColorDialog."""

    color_changed = Signal(str)   # hex string

    def __init__(self, hex_color: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hex = hex_color.upper()
        self._refresh()
        self.clicked.connect(self._pick)

    def hex_color(self) -> str:
        return self._hex

    def set_color(self, hex_color: str) -> None:
        self._hex = hex_color.upper()
        self._refresh()

    def _pick(self) -> None:
        col = QColorDialog.getColor(QColor(self._hex), self, "Pick colour")
        if col.isValid():
            self._hex = col.name().upper()
            self._refresh()
            self.color_changed.emit(self._hex)

    def _refresh(self) -> None:
        h = self._hex.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        lum = 0.2126 * r / 255 + 0.7152 * g / 255 + 0.0722 * b / 255
        fg  = "#000000" if lum > 0.40 else "#FFFFFF"
        self.setStyleSheet(
            f"background-color: {self._hex}; color: {fg};"
            f" border: 2px solid #666; font-size: 11px;"
            f' font-family: "Courier New", Consolas, monospace;'
        )
        self.setText(self._hex)


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

_SEED_FIELDS: list[tuple[str, str, str]] = [
    # (seed key,  display label,            tooltip)
    ("bg",     "Background",
     "Deepest background. Panels and inputs are auto-derived slightly lighter."),
    ("text",   "Text",
     "Primary text colour. Secondary text and disabled text are auto-derived."),
    ("accent", "Accent",
     "Signature colour: borders, tab underlines, button outlines, header labels."),
    ("green",  "Positive  (green)",
     "Used for gains, positive deltas and in-range metric values."),
    ("red",    "Negative  (red)",
     "Used for losses, negative deltas and out-of-range metric values."),
    ("orange", "Warning   (orange)",
     "Used for borderline metric values and status-bar warnings."),
]


class ThemeEditorDialog(QDialog):
    """
    Lets the user set 6 seed colours + font/corner/border-width.
    All other palette values are derived automatically.
    Emits theme_applied after saving and registering the Custom theme.
    """

    theme_applied = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Custom Theme Editor")
        self.setModal(True)
        self.setMinimumWidth(480)
        self._seeds: dict = load_custom_seeds()
        self._swatches: dict[str, _ColorSwatch] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(22, 20, 22, 20)

        # Title
        title = QLabel("Custom Theme Editor")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        root.addWidget(title)

        hint = QLabel(
            "Pick 6 colours — all other shades are derived automatically."
        )
        hint.setStyleSheet("font-size: 11px; color: #888;")
        root.addWidget(hint)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # Colour pickers
        clr_hdr = QLabel("COLOURS")
        clr_hdr.setStyleSheet(
            "font-size: 11px; font-weight: bold; letter-spacing: 1px; color: #888;"
        )
        root.addWidget(clr_hdr)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnStretch(0, 1)
        for row, (key, label, tooltip) in enumerate(_SEED_FIELDS):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 12px;")
            lbl.setToolTip(tooltip)
            swatch = _ColorSwatch(self._seeds.get(key, "#888888"))
            swatch.setToolTip(tooltip)
            swatch.color_changed.connect(
                lambda h, k=key: self._seeds.update({k: h})
            )
            self._swatches[key] = swatch
            grid.addWidget(lbl,    row, 0)
            grid.addWidget(swatch, row, 1, Qt.AlignmentFlag.AlignRight)
        root.addLayout(grid)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep2)

        # Style dropdowns
        sty_hdr = QLabel("STYLE")
        sty_hdr.setStyleSheet(
            "font-size: 11px; font-weight: bold; letter-spacing: 1px; color: #888;"
        )
        root.addWidget(sty_hdr)

        sty = QGridLayout()
        sty.setSpacing(8)
        sty.setColumnStretch(1, 1)

        sty.addWidget(QLabel("Font:"),         0, 0)
        self._font_cb = self._make_combo(_FONT_OPTIONS,   self._seeds.get("font",   ""))
        sty.addWidget(self._font_cb, 0, 1)

        sty.addWidget(QLabel("Corners:"),      1, 0)
        self._rad_cb  = self._make_combo(_RADIUS_OPTIONS, self._seeds.get("radius", "0px"))
        sty.addWidget(self._rad_cb, 1, 1)

        sty.addWidget(QLabel("Border width:"), 2, 0)
        self._bw_cb   = self._make_combo(_BW_OPTIONS,     self._seeds.get("bw",     "2px"))
        sty.addWidget(self._bw_cb, 2, 1)

        root.addLayout(sty)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep3)

        # Buttons
        btn_row = QHBoxLayout()
        reset_btn = QPushButton("Reset to Amber")
        reset_btn.clicked.connect(self._reset_to_amber)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        apply_btn  = QPushButton("Apply Custom Theme")
        apply_btn.setDefault(True)
        apply_btn.setStyleSheet("font-weight: bold; padding: 6px 18px;")
        apply_btn.clicked.connect(self._apply)

        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(apply_btn)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    def _make_combo(self, options: list[tuple[str, str]], current_val: str) -> QComboBox:
        cb = QComboBox()
        for val, label in options:
            cb.addItem(label, val)
        for i, (val, _) in enumerate(options):
            if val == current_val:
                cb.setCurrentIndex(i)
                break
        return cb

    def _reset_to_amber(self) -> None:
        for key, _ , _ in _SEED_FIELDS:
            val = _DEFAULT_SEEDS[key]
            self._seeds[key] = val
            self._swatches[key].set_color(val)
        self._font_cb.setCurrentIndex(0)
        self._rad_cb.setCurrentIndex(0)
        self._bw_cb.setCurrentIndex(1)

    def _collect_seeds(self) -> dict:
        s = dict(self._seeds)
        for key, swatch in self._swatches.items():
            s[key] = swatch.hex_color()
        s["font"]   = self._font_cb.currentData()
        s["radius"] = self._rad_cb.currentData()
        s["bw"]     = self._bw_cb.currentData()
        return s

    def _apply(self) -> None:
        seeds = self._collect_seeds()
        save_custom_seeds(seeds)
        theme = _s.derive_full_theme(
            bg     = seeds["bg"],
            text   = seeds["text"],
            accent = seeds["accent"],
            green  = seeds["green"],
            red    = seeds["red"],
            orange = seeds["orange"],
            font   = seeds["font"],
            radius = seeds["radius"],
            bw     = seeds["bw"],
        )
        _s.THEMES["Custom"] = theme
        if "Custom" not in _s.THEME_ORDER:
            _s.THEME_ORDER.append("Custom")
        self.theme_applied.emit()
        self.accept()
