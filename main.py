"""
Portfolio Modeller — entry point.

Initialises the database, applies the Qt stylesheet, and launches the window.
"""
import sys
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging setup (before any other imports so we catch startup errors)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Make sure project root is on sys.path when run as a script or via PyInstaller
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Qt imports
# ---------------------------------------------------------------------------
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

import data.db as db
from config import APP_NAME, DB_PATH
from ui.main_window import MainWindow


def main() -> None:
    log.info("Starting %s", APP_NAME)
    log.info("Database path: %s", DB_PATH)

    # Enable High-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("PortfolioModeller")

    # App icon (if present)
    icon_path = _ROOT / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Initialise database schema (safe to call on every launch)
    try:
        db.init_db()
    except Exception as exc:
        log.critical("Database initialisation failed: %s", exc)
        sys.exit(1)

    # Apply stylesheet at the application level — this is the single source of
    # truth for all Qt styling.  Widget-level setStyleSheet() calls override
    # the app-level one, so main_window.py must NOT call self.setStyleSheet().
    from ui.styles import STYLESHEET
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
