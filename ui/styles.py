"""
Qt stylesheet and colour constants.

Dark theme designed for a financial data app — high contrast,
clear data hierarchy, no distracting decoration.
"""

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
BG_MAIN       = "#1E1E2E"   # main background
BG_PANEL      = "#2A2A3E"   # panels / cards
BG_INPUT      = "#313145"   # input fields
BORDER        = "#3E3E5E"   # subtle borders

TEXT_PRIMARY   = "#E0E0F0"  # primary text
TEXT_SECONDARY = "#9090B0"  # labels, captions
TEXT_DISABLED  = "#555570"

GREEN   = "#4CAF50"   # in-target / positive
RED     = "#F44336"   # out-of-target / negative
ORANGE  = "#FF9800"   # warning / borderline
NEUTRAL = "#9090B0"   # neutral / not enough data

ACCENT  = "#7C6AF5"   # tab highlight, hover accent

# ---------------------------------------------------------------------------
# Traffic-light helper
# ---------------------------------------------------------------------------

def traffic_light(value: float | None, target_range: tuple[float, float]) -> str:
    """
    Return a colour string based on whether *value* is inside target_range.

    target_range = (low, high) — both bounds inclusive.
    Returns NEUTRAL for None, GREEN for in-range, RED for out-of-range.
    """
    if value is None:
        return NEUTRAL
    lo, hi = target_range
    if lo <= value <= hi:
        return GREEN
    # Orange for just outside (within 20 % of the bound width)
    width = abs(hi - lo)
    margin = 0.20 * width
    if (lo - margin) <= value <= (hi + margin):
        return ORANGE
    return RED


# ---------------------------------------------------------------------------
# Global Qt stylesheet
# ---------------------------------------------------------------------------

STYLESHEET = f"""
/* ── Base ── */
QWidget {{
    background-color: {BG_MAIN};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

/* ── Tabs ── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {BG_MAIN};
}}
QTabBar::tab {{
    background: {BG_PANEL};
    color: {TEXT_SECONDARY};
    padding: 8px 20px;
    border: 1px solid {BORDER};
    border-bottom: none;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {BG_MAIN};
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
    background: {BG_INPUT};
}}

/* ── Frames / panels ── */
QFrame#MetricCard {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QFrame#Panel {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}

/* ── GroupBox ── */
QGroupBox {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 18px;
    padding-top: 8px;
    font-weight: bold;
    color: {TEXT_SECONDARY};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    top: -2px;
    padding: 0 4px;
    color: {TEXT_SECONDARY};
}}

/* ── Buttons ── */
QPushButton {{
    background: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 6px 14px;
    min-width: 80px;
}}
QPushButton:hover {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QPushButton:pressed {{
    background: #5A4FD4;
}}
QPushButton#AddButton {{
    background: transparent;
    color: {ACCENT};
    border: 1px solid {ACCENT};
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 12px;
    min-width: 0;
}}
QPushButton#AddButton:hover {{
    background: {ACCENT};
    color: white;
}}
QPushButton#RefreshButton {{
    background: {BG_INPUT};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 12px;
    font-size: 12px;
    min-width: 0;
}}
QPushButton#RefreshButton:hover {{
    color: {TEXT_PRIMARY};
    border-color: {ACCENT};
}}

/* ── LineEdit / SpinBox ── */
QLineEdit, QDoubleSpinBox, QSpinBox {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 8px;
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT};
}}

/* ── ComboBox ── */
QComboBox {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 10px;
    color: {TEXT_PRIMARY};
    min-width: 120px;
}}
QComboBox:hover {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
    color: {TEXT_PRIMARY};
}}

/* ── Tables ── */
QTableWidget {{
    background: {BG_PANEL};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 4px;
    alternate-background-color: {BG_INPUT};
}}
QTableWidget::item {{
    padding: 4px 8px;
}}
QTableWidget::item:selected {{
    background: {ACCENT};
    color: white;
}}
QHeaderView::section {{
    background: {BG_INPUT};
    color: {TEXT_SECONDARY};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    padding: 5px 8px;
    font-weight: bold;
    font-size: 12px;
}}

/* ── ListWidget ── */
QListWidget {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 4px;
    alternate-background-color: {BG_INPUT};
    outline: none;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {BORDER};
}}
QListWidget::item:selected {{
    background: {ACCENT};
    color: white;
}}
QListWidget::item:hover {{
    background: {BG_INPUT};
}}

/* ── ScrollBar ── */
QScrollBar:vertical {{
    background: {BG_PANEL};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Labels ── */
QLabel#SectionHeader {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QLabel#WarningBanner {{
    background: #3D2B0F;
    color: {ORANGE};
    border: 1px solid {ORANGE};
    border-radius: 4px;
    padding: 6px 12px;
}}
QLabel#ErrorLabel {{
    color: {RED};
    font-size: 11px;
}}

/* ── Dialog ── */
QDialog {{
    background: {BG_MAIN};
}}

/* ── StatusBar ── */
QStatusBar {{
    background: {BG_PANEL};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER};
    font-size: 12px;
    padding: 2px 8px;
}}
QStatusBar::item {{ border: none; }}

/* ── RadioButton ── */
QRadioButton {{
    color: {TEXT_PRIMARY};
    spacing: 6px;
}}
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 2px solid {BORDER};
    border-radius: 7px;
    background: {BG_INPUT};
}}
QRadioButton::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

/* ── Separator ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {BORDER};
}}

/* ── ToolTip ── */
QToolTip {{
    background: {BG_INPUT};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    padding: 4px 8px;
    border-radius: 3px;
}}
"""
