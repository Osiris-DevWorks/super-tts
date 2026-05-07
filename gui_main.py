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

    # Mirror .env contents into os.environ so the Settings tab and
    # Status tab can see DISCORD_TOKEN / DATABASE_URL on launch (otherwise
    # they'd only become visible after the bot thread imports main.py and
    # main.py runs its own load_dotenv).
    #
    # Order matches main.py's resolution exactly:
    #   1. %APPDATA%\Osiris DevWorks\Super TTS\.env  — installer-written
    #   2. Project-root .env via load_dotenv()'s default CWD search — the
    #      dev path used by `poetry run python gui_main.py` from the repo.
    try:
        from dotenv import load_dotenv
    except Exception:
        return

    appdata = os.environ.get("APPDATA")
    env_path: Path | None = None
    if appdata:
        env_path = Path(appdata) / "Osiris DevWorks" / "Super TTS" / ".env"

    if env_path and env_path.is_file():
        try:
            load_dotenv(env_path)
        except Exception:
            pass
    else:
        try:
            load_dotenv()
        except Exception:
            pass


def _set_windows_app_user_model_id() -> None:
    """Tell Windows we're a distinct app, not "Python".

    Without this, the Windows taskbar groups the running process under
    python.exe (or whatever started us) and shows that exe's icon
    regardless of QIcon assignments. Setting an explicit AppUserModelID
    *before* QApplication is constructed makes Windows pin the taskbar
    icon to whatever QApplication.setWindowIcon supplies. No-op on
    non-Windows platforms.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "OsirisDevWorks.SuperTTS"
        )
    except Exception:
        pass


def _resource_path(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel


def main() -> int:
    _bootstrap()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("super-tts.gui")

    # Must run BEFORE QApplication so the taskbar groups under our app
    # ID rather than python.exe's.
    _set_windows_app_user_model_id()

    # Defer Qt imports until after _bootstrap so the env var is set before
    # any code imports main (which the imports below transitively do).
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    from gui import settings as gui_settings
    from gui import theme as gui_theme
    from gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setOrganizationName(gui_settings.ORG_NAME)
    app.setApplicationName(gui_settings.APP_NAME)

    # App-wide icon — feeds the Windows taskbar, the Alt-Tab switcher, and
    # MainWindow's own setWindowIcon (the per-window call there is a
    # belt-and-suspenders fallback). Multi-resolution .ico means Windows
    # picks the right size for each surface.
    icon_path = _resource_path("assets/super-tts.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Register the bundled display font BEFORE building any widgets that
    # reference it. addApplicationFont needs a live QApplication, but the
    # family must be available when the title label's QFont is constructed.
    gui_theme.load_application_fonts()

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
