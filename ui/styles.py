"""
Qt stylesheet and colour constants with multi-theme support.

Themes (cycle with the Theme button):
  Amber    — CRT amber-on-black terminal (default)
  Phosphor — classic green phosphor monitor
  DOS      — retro DOS blue
  Modern   — current dark purple (original)

All module-level colour globals (BG_MAIN, TEXT_PRIMARY, etc.) are updated
by apply_theme() so any code that accesses them as  _s.BG_MAIN  will always
see the live value after a theme change.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Theme palettes
# ---------------------------------------------------------------------------

THEMES: dict[str, dict] = {
    "Amber": {
        "BG_MAIN":        "#080808",
        "BG_PANEL":       "#111111",
        "BG_INPUT":       "#1A1A1A",
        "BORDER":         "#B86800",
        "TEXT_PRIMARY":   "#FFA500",
        "TEXT_SECONDARY": "#7A4A00",
        "TEXT_DISABLED":  "#3D2500",
        "GREEN":          "#6BCF6B",
        "RED":            "#FF5555",
        "ORANGE":         "#FFD700",
        "NEUTRAL":        "#7A4A00",
        "ACCENT":         "#FFC200",
        "FONT_FAMILY":    '"Courier New", Consolas, monospace',
        "BORDER_RADIUS":  "0px",
        "BORDER_WIDTH":   "2px",
        "SCROLLBAR_W":    "10px",
    },
    "Phosphor": {
        "BG_MAIN":        "#020C02",
        "BG_PANEL":       "#050F05",
        "BG_INPUT":       "#091409",
        "BORDER":         "#009900",
        "TEXT_PRIMARY":   "#00FF41",
        "TEXT_SECONDARY": "#007520",
        "TEXT_DISABLED":  "#003A10",
        "GREEN":          "#00FF41",
        "RED":            "#FF4040",
        "ORANGE":         "#BBFF00",
        "NEUTRAL":        "#007520",
        "ACCENT":         "#00CC33",
        "FONT_FAMILY":    '"Courier New", Consolas, monospace',
        "BORDER_RADIUS":  "0px",
        "BORDER_WIDTH":   "2px",
        "SCROLLBAR_W":    "10px",
    },
    "DOS": {
        "BG_MAIN":        "#000080",
        "BG_PANEL":       "#0000A8",
        "BG_INPUT":       "#000055",
        "BORDER":         "#AAAAAA",
        "TEXT_PRIMARY":   "#FFFFFF",
        "TEXT_SECONDARY": "#AAAAAA",
        "TEXT_DISABLED":  "#555577",
        "GREEN":          "#55FF55",
        "RED":            "#FF5555",
        "ORANGE":         "#FFAA00",
        "NEUTRAL":        "#AAAAAA",
        "ACCENT":         "#FFFF55",
        "FONT_FAMILY":    '"Courier New", Consolas, monospace',
        "BORDER_RADIUS":  "0px",
        "BORDER_WIDTH":   "2px",
        "SCROLLBAR_W":    "12px",
    },
    "Modern": {
        "BG_MAIN":        "#1E1E2E",
        "BG_PANEL":       "#2A2A3E",
        "BG_INPUT":       "#313145",
        "BORDER":         "#3E3E5E",
        "TEXT_PRIMARY":   "#E0E0F0",
        "TEXT_SECONDARY": "#9090B0",
        "TEXT_DISABLED":  "#555570",
        "GREEN":          "#4CAF50",
        "RED":            "#F44336",
        "ORANGE":         "#FF9800",
        "NEUTRAL":        "#9090B0",
        "ACCENT":         "#7C6AF5",
        "FONT_FAMILY":    '"Segoe UI", Arial, sans-serif',
        "BORDER_RADIUS":  "6px",
        "BORDER_WIDTH":   "1px",
        "SCROLLBAR_W":    "8px",
    },
}

THEME_ORDER: list[str] = ["Amber", "Phosphor", "DOS", "Modern"]

# "Custom" is populated at startup (load_custom_theme) and by the editor dialog.
# It's only added to THEME_ORDER once the user saves a custom theme.

_current_name: str = "Amber"

# ---------------------------------------------------------------------------
# Module-level colour globals — updated by apply_theme()
# ---------------------------------------------------------------------------
BG_MAIN        = ""
BG_PANEL       = ""
BG_INPUT       = ""
BORDER         = ""
TEXT_PRIMARY   = ""
TEXT_SECONDARY = ""
TEXT_DISABLED  = ""
GREEN          = ""
RED            = ""
ORANGE         = ""
NEUTRAL        = ""
ACCENT         = ""
FONT_FAMILY    = ""
BORDER_RADIUS  = ""
BORDER_WIDTH   = ""
SCROLLBAR_W    = ""
STYLESHEET     = ""


# ---------------------------------------------------------------------------
# Seed-colour derivation
# ---------------------------------------------------------------------------

def _parse(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _add_lightness(h: str, n: int) -> str:
    """Add n to every RGB channel (clamp at 255), preserving hue."""
    r, g, b = _parse(h)
    return _rgb(min(r + n, 255), min(g + n, 255), min(b + n, 255))


def _blend(a: str, b: str, t: float) -> str:
    """Linear blend: t=0 → a, t=1 → b."""
    ar, ag, ab = _parse(a)
    br, bg, bb = _parse(b)
    return _rgb(
        int(ar + (br - ar) * t),
        int(ag + (bg - ag) * t),
        int(ab + (bb - ab) * t),
    )


def derive_full_theme(
    bg:     str,
    text:   str,
    accent: str,
    green:  str,
    red:    str,
    orange: str,
    font:   str  = '"Courier New", Consolas, monospace',
    radius: str  = "0px",
    bw:     str  = "2px",
) -> dict:
    """
    Build a complete theme dict from 6 seed colours + 3 style choices.

    bg     — deepest background colour (BG_MAIN)
    text   — primary text / foreground colour
    accent — signature colour used for borders, highlights, headers
    green  — positive / gain colour
    red    — negative / loss colour
    orange — warning colour
    """
    return {
        "BG_MAIN":        bg,
        "BG_PANEL":       _add_lightness(bg, 10),
        "BG_INPUT":       _add_lightness(bg, 20),
        "BORDER":         accent,
        "TEXT_PRIMARY":   text,
        "TEXT_SECONDARY": _blend(text, bg, 0.50),
        "TEXT_DISABLED":  _blend(text, bg, 0.75),
        "NEUTRAL":        _blend(text, bg, 0.50),
        "ACCENT":         accent,
        "GREEN":          green,
        "RED":            red,
        "ORANGE":         orange,
        "FONT_FAMILY":    font,
        "BORDER_RADIUS":  radius,
        "BORDER_WIDTH":   bw,
        "SCROLLBAR_W":    "10px" if bw in ("2px", "3px") else "8px",
    }


# ---------------------------------------------------------------------------
# QPalette builder — lets Fusion use our theme colours for all native drawing
# (separator lines, focus rings, etc.) so they match the stylesheet exactly.
# ---------------------------------------------------------------------------

def build_palette():
    """Return a QPalette whose Mid role = BORDER, so Fusion's native 1px
    header/section separator lines are drawn in our theme border colour."""
    from PySide6.QtGui import QPalette, QColor  # imported lazily to keep module lightweight

    t = THEMES[_current_name]
    bg    = QColor(t["BG_MAIN"])
    panel = QColor(t["BG_PANEL"])
    inp   = QColor(t["BG_INPUT"])
    brd   = QColor(t["BORDER"])
    pri   = QColor(t["TEXT_PRIMARY"])
    sec   = QColor(t["TEXT_SECONDARY"])
    acc   = QColor(t["ACCENT"])

    pal = QPalette()
    # Backgrounds
    pal.setColor(QPalette.ColorRole.Window,         bg)
    pal.setColor(QPalette.ColorRole.Base,           panel)
    pal.setColor(QPalette.ColorRole.AlternateBase,  inp)
    pal.setColor(QPalette.ColorRole.Button,         inp)
    pal.setColor(QPalette.ColorRole.ToolTipBase,    inp)
    # Text
    pal.setColor(QPalette.ColorRole.WindowText,     pri)
    pal.setColor(QPalette.ColorRole.Text,           pri)
    pal.setColor(QPalette.ColorRole.BrightText,     pri)
    pal.setColor(QPalette.ColorRole.ButtonText,     pri)
    pal.setColor(QPalette.ColorRole.ToolTipText,    pri)
    pal.setColor(QPalette.ColorRole.PlaceholderText, sec)
    # Selection
    pal.setColor(QPalette.ColorRole.Highlight,      acc)
    pal.setColor(QPalette.ColorRole.HighlightedText, bg)
    pal.setColor(QPalette.ColorRole.Link,           acc)
    pal.setColor(QPalette.ColorRole.LinkVisited,    acc)
    # Border / separator roles — Fusion uses Mid for its native 1px lines
    pal.setColor(QPalette.ColorRole.Mid,            brd)
    pal.setColor(QPalette.ColorRole.Midlight,       inp)
    pal.setColor(QPalette.ColorRole.Dark,           brd)
    pal.setColor(QPalette.ColorRole.Light,          inp)
    pal.setColor(QPalette.ColorRole.Shadow,         bg)
    return pal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def current_theme_name() -> str:
    return _current_name


def next_theme_name() -> str:
    idx = THEME_ORDER.index(_current_name)
    return THEME_ORDER[(idx + 1) % len(THEME_ORDER)]


def traffic_light(value: float | None, target_range: tuple[float, float]) -> str:
    """Return a colour string based on whether value is inside target_range."""
    if value is None:
        return NEUTRAL
    lo, hi = target_range
    if lo <= value <= hi:
        return GREEN
    width = abs(hi - lo)
    margin = 0.20 * width
    if (lo - margin) <= value <= (hi + margin):
        return ORANGE
    return RED


def _darken(hex_color: str, factor: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{int(r * factor):02X}{int(g * factor):02X}{int(b * factor):02X}"


# ---------------------------------------------------------------------------
# Stylesheet builder
# ---------------------------------------------------------------------------

def build_stylesheet() -> str:
    t   = THEMES[_current_name]
    br  = t["BORDER_RADIUS"]
    bw  = t["BORDER_WIDTH"]
    ff  = t["FONT_FAMILY"]
    sw  = t["SCROLLBAR_W"]
    bg  = t["BG_MAIN"]
    panel = t["BG_PANEL"]
    inp = t["BG_INPUT"]
    brd = t["BORDER"]
    pri = t["TEXT_PRIMARY"]
    sec = t["TEXT_SECONDARY"]
    acc = t["ACCENT"]
    red = t["RED"]
    org = t["ORANGE"]
    pressed = _darken(acc, 0.65)

    return f"""
/* ── Base ── */
QWidget {{
    background-color: {bg};
    color: {pri};
    font-family: {ff};
    font-size: 13px;
}}

/* ── Tabs ── */
QTabWidget::pane {{
    border: {bw} solid {brd};
    background: {bg};
}}
QTabBar::tab {{
    background: {panel};
    color: {sec};
    padding: 8px 20px;
    border: {bw} solid {brd};
    border-bottom: none;
    margin-right: 2px;
    border-radius: 0px;
}}
QTabBar::tab:selected {{
    background: {bg};
    color: {pri};
    border-bottom: 3px solid {acc};
}}
QTabBar::tab:hover {{
    color: {pri};
    background: {inp};
}}

/* ── Frames / panels ── */
QFrame#MetricCard {{
    background: {panel};
    border: {bw} solid {brd};
    border-radius: {br};
}}
QFrame#Panel {{
    background: {panel};
    border: {bw} solid {brd};
    border-radius: {br};
}}

/* ── GroupBox ── */
QGroupBox {{
    background: {panel};
    border: {bw} solid {brd};
    border-radius: {br};
    margin-top: 18px;
    padding-top: 8px;
    font-weight: bold;
    color: {sec};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    top: -2px;
    padding: 0 4px;
    color: {acc};
    font-weight: bold;
}}

/* ── Buttons ── */
QPushButton {{
    background: {inp};
    color: {pri};
    border: {bw} solid {brd};
    border-radius: {br};
    padding: 6px 14px;
    min-width: 80px;
}}
QPushButton:hover {{
    background: {acc};
    color: {bg};
    border-color: {acc};
}}
QPushButton:pressed {{
    background: {pressed};
}}
QPushButton#AddButton {{
    background: transparent;
    color: {acc};
    border: {bw} solid {acc};
    border-radius: {br};
    padding: 4px 10px;
    font-size: 12px;
    min-width: 0;
}}
QPushButton#AddButton:hover {{
    background: {acc};
    color: {bg};
}}
QPushButton#RefreshButton {{
    background: {inp};
    color: {sec};
    border: {bw} solid {brd};
    border-radius: {br};
    padding: 5px 12px;
    font-size: 12px;
    min-width: 0;
}}
QPushButton#RefreshButton:hover {{
    color: {pri};
    border-color: {acc};
}}
QPushButton#ThemeButton, QToolButton#ThemeButton {{
    background: transparent;
    color: {acc};
    border: {bw} solid {acc};
    border-radius: {br};
    padding: 4px 14px;
    font-size: 11px;
    min-width: 0;
}}
QPushButton#ThemeButton:hover, QToolButton#ThemeButton:hover {{
    background: {acc};
    color: {bg};
}}
QToolButton#ThemeButton::menu-indicator {{ width: 0; }}

/* ── LineEdit / SpinBox ── */
QLineEdit, QDoubleSpinBox, QSpinBox {{
    background: {inp};
    border: {bw} solid {brd};
    border-radius: {br};
    padding: 5px 8px;
    color: {pri};
    selection-background-color: {acc};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
    border-color: {acc};
}}

/* Spin-box buttons — flat, flush inside the border, no native chrome */
QDoubleSpinBox::up-button, QSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 18px;
    border-left: {bw} solid {brd};
    border-bottom: 1px solid {brd};
    border-top: none;
    border-right: none;
    background: {inp};
}}
QDoubleSpinBox::down-button, QSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 18px;
    border-left: {bw} solid {brd};
    border-top: none;
    border-bottom: none;
    border-right: none;
    background: {inp};
}}
QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {{
    background: {brd};
}}
QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {{
    width: 7px; height: 7px;
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {pri};
}}
QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {{
    width: 7px; height: 7px;
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {pri};
}}

/* ── ComboBox ── */
QComboBox {{
    background: {inp};
    border: {bw} solid {brd};
    border-radius: {br};
    padding: 5px 10px;
    color: {pri};
    min-width: 120px;
}}
QComboBox:hover {{ border-color: {acc}; }}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {inp};
    border: {bw} solid {brd};
    selection-background-color: {acc};
    color: {pri};
}}

/* ── Tables ──
   Border strategy — every line comes from exactly one source (no double-draw):
   • Each item draws its OWN top + left border  → provides all interior
     separators AND the top/left edges of the table (first row / first col).
   • The table widget draws only border-right + border-bottom  → closes the
     outer right and bottom edges without any overlap with item borders.
   • showGrid is disabled (setShowGrid(False)) so Qt never draws its own
     gridlines on top of these CSS borders.
*/
QTableWidget {{
    background: {panel};
    gridline-color: transparent;
    border-top: none;
    border-left: none;
    border-right: 1px solid {brd};
    border-bottom: 1px solid {brd};
    alternate-background-color: {inp};
}}
QTableWidget::item {{
    padding: 4px 8px;
    border-top: 1px solid {brd};
    border-left: 1px solid {brd};
}}
QTableWidget::item:selected {{
    background: {acc};
    color: {bg};
}}
QHeaderView::section {{
    background: {inp};
    color: {acc};
    border: none;
    border-top: 1px solid {brd};
    border-left: 1px solid {brd};
    padding: 5px 8px;
    font-weight: bold;
    font-size: 12px;
}}
QHeaderView {{
    border: none;
    background: {inp};
}}
/* Corner button (top-left cell where horizontal + vertical headers intersect).
   QHeaderView::section does NOT cover this widget, so it must be styled
   separately with the same border-top + border-left as all other sections. */
QTableCornerButton::section {{
    background: {inp};
    border: none;
    border-top: 1px solid {brd};
    border-left: 1px solid {brd};
}}

/* ── ListWidget ── */
QListWidget {{
    background: {panel};
    border: {bw} solid {brd};
    border-radius: {br};
    alternate-background-color: {inp};
    outline: none;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {brd};
}}
QListWidget::item:selected {{
    background: {acc};
    color: {bg};
}}
QListWidget::item:hover {{
    background: {inp};
}}

/* ── ScrollBar ── */
QScrollBar:vertical {{
    background: {panel};
    width: {sw};
    border-radius: 0px;
    border: 1px solid {brd};
}}
QScrollBar::handle:vertical {{
    background: {brd};
    border-radius: 0px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Labels ── */
QLabel#SectionHeader {{
    color: {acc};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}}
QLabel#WarningBanner {{
    background: {inp};
    color: {org};
    border: {bw} solid {org};
    border-radius: {br};
    padding: 6px 12px;
}}
QLabel#ErrorLabel {{
    color: {red};
    font-size: 11px;
}}

/* ── Dialog ── */
QDialog {{
    background: {bg};
}}

/* ── StatusBar ── */
QStatusBar {{
    background: {panel};
    color: {sec};
    border-top: {bw} solid {brd};
    font-size: 12px;
    padding: 2px 8px;
}}
QStatusBar::item {{ border: none; }}

/* ── RadioButton ── */
QRadioButton {{
    color: {pri};
    spacing: 6px;
}}
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: {bw} solid {brd};
    border-radius: 0px;
    background: {inp};
}}
QRadioButton::indicator:checked {{
    background: {acc};
    border-color: {acc};
}}

/* ── Separator ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {brd};
}}

/* ── ToolTip ── */
QToolTip {{
    background: {inp};
    color: {pri};
    border: {bw} solid {brd};
    padding: 4px 8px;
    border-radius: {br};
}}
"""


# ---------------------------------------------------------------------------
# Theme applier — updates all module globals + rebuilds STYLESHEET
# ---------------------------------------------------------------------------

def apply_theme(name: str) -> str:
    """
    Switch to the named theme.  Updates every module-level colour global and
    regenerates STYLESHEET.  Returns the new stylesheet string.
    """
    global _current_name
    global BG_MAIN, BG_PANEL, BG_INPUT, BORDER
    global TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DISABLED
    global GREEN, RED, ORANGE, NEUTRAL, ACCENT
    global FONT_FAMILY, BORDER_RADIUS, BORDER_WIDTH, SCROLLBAR_W
    global STYLESHEET

    _current_name  = name
    t              = THEMES[name]
    BG_MAIN        = t["BG_MAIN"]
    BG_PANEL       = t["BG_PANEL"]
    BG_INPUT       = t["BG_INPUT"]
    BORDER         = t["BORDER"]
    TEXT_PRIMARY   = t["TEXT_PRIMARY"]
    TEXT_SECONDARY = t["TEXT_SECONDARY"]
    TEXT_DISABLED  = t["TEXT_DISABLED"]
    GREEN          = t["GREEN"]
    RED            = t["RED"]
    ORANGE         = t["ORANGE"]
    NEUTRAL        = t["NEUTRAL"]
    ACCENT         = t["ACCENT"]
    FONT_FAMILY    = t["FONT_FAMILY"]
    BORDER_RADIUS  = t["BORDER_RADIUS"]
    BORDER_WIDTH   = t["BORDER_WIDTH"]
    SCROLLBAR_W    = t["SCROLLBAR_W"]
    STYLESHEET     = build_stylesheet()
    return STYLESHEET


# Apply default theme on module import
apply_theme("Amber")
