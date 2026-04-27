#!/usr/bin/env python3
"""Super TTS GUI — Windows installer entry point.

This is the entry point that PyInstaller builds into Super-TTS-vX.X.X.exe.
Docker / Railway use main.py directly and never load this module.

Flow:
  1. Set SUPER_TTS_GUI_MODE=1 so main.py's import-time token guard skips
     its sys.exit(1).
  2. Pre-load .env from %APPDATA%\\Osiris DevWorks\\Super TTS\\.env into
     os.environ. main.py would do this anyway via load_dotenv(), but doing
     it here means the GUI's Status tab can read DISCORD_TOKEN before the
     bot has been imported.
  3. Set up logging.
  4. Build the QApplication, apply the persisted theme, show the window.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


def _bootstrap() -> None:
    """Pre-import wiring that has to happen before main.py is touched."""
    os.environ["SUPER_TTS_GUI_MODE"] = "1"

    # Mirror the .env file's contents into os.environ so other modules
    # (db.db, main, etc.) see DISCORD_TOKEN / DATABASE_URL on import.
    appdata = os.environ.get("APPDATA")
    env_path: Path | None = None
    if appdata:
        env_path = Path(appdata) / "Osiris DevWorks" / "Super TTS" / ".env"

    if env_path and env_path.is_file():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path)
        except Exception:
            # python-dotenv missing or parse error — continue, the GUI
            # will surface a missing-token state via the Settings tab.
            pass


def main() -> int:
    _bootstrap()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("super-tts.gui")

    # Defer Qt imports until after _bootstrap so the env var is set before
    # any code imports main (which the imports below transitively do).
    from PyQt6.QtWidgets import QApplication

    from gui import settings as gui_settings
    from gui import theme as gui_theme
    from gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setOrganizationName(gui_settings.ORG_NAME)
    app.setApplicationName(gui_settings.APP_NAME)

    gui_theme.apply_theme(app, gui_settings.get_theme())

    win = MainWindow()
    win.show()

    logger.info(
        "GUI ready — token configured: %s, db url configured: %s",
        bool(os.getenv("DISCORD_TOKEN")),
        bool(os.getenv("DATABASE_URL")),
    )

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
