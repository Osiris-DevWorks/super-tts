"""Main window — QTabWidget hosting Status / Settings / Logs / About tabs."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui import settings as gui_settings
from gui import theme as gui_theme
from gui.about_tab import AboutTab
from gui.log_tab import LogTab
from gui.settings_tab import SettingsTab
from gui.status_tab import StatusTab

logger = logging.getLogger(__name__)


def _resource_path(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / rel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Super TTS")
        self.resize(900, 620)

        # Optional icon — if assets/super-tts.ico is bundled, use it
        icon_path = _resource_path("assets/super-tts.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()

        # First-run UX: if there's no token yet, open on the Settings tab so
        # users land directly on the form they need to fill in. Otherwise
        # default to the Status tab and auto-connect.
        if not os.getenv("DISCORD_TOKEN"):
            self._tabs.setCurrentWidget(self._settings_tab)
        else:
            # Auto-connect on launch if a token is configured. Done in a
            # single-shot timer so the window is visible by the time the bot
            # starts — otherwise the user sees a blank app for ~1s while
            # migrations run.
            QTimer.singleShot(150, self._status_tab.auto_connect_if_ready)

    # ── UI assembly ──────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(8)

        outer.addLayout(self._build_header())

        self._tabs = QTabWidget()
        self._status_tab = StatusTab()
        self._settings_tab = SettingsTab()
        self._log_tab = LogTab()
        self._about_tab = AboutTab()

        self._tabs.addTab(self._status_tab, "Status")
        self._tabs.addTab(self._settings_tab, "Settings")
        self._tabs.addTab(self._log_tab, "Logs")
        self._tabs.addTab(self._about_tab, "About")

        self._settings_tab.theme_changed.connect(self._on_theme_changed)

        outer.addWidget(self._tabs, 1)
        self.setCentralWidget(central)

        sb = QStatusBar()
        sb.showMessage(f"Ready — config: {gui_settings.env_file_path()}")
        self.setStatusBar(sb)

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        self._title_label = QLabel("Super TTS")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        self._title_label.setStyleSheet(f"color: {gui_theme.get_title_color()};")
        row.addWidget(self._title_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self._tagline_label = QLabel("· Discord TTS bot · Osiris DevWorks")
        tagline_font = QFont()
        tagline_font.setPointSize(10)
        self._tagline_label.setFont(tagline_font)
        self._tagline_label.setStyleSheet(f"color: {gui_theme.get_tagline_color()};")
        row.addWidget(self._tagline_label, 0, Qt.AlignmentFlag.AlignVCenter)

        row.addStretch()
        return row

    # ── Slots ────────────────────────────────────────────────────────────

    def _on_theme_changed(self, theme: str):
        app = QApplication.instance()
        if app is not None:
            gui_theme.apply_theme(app, theme)
        # Re-render any theme-dependent ad-hoc styles
        self._title_label.setStyleSheet(f"color: {gui_theme.get_title_color()};")
        self._tagline_label.setStyleSheet(f"color: {gui_theme.get_tagline_color()};")
        self._status_tab.on_theme_changed()
        self._about_tab.on_theme_changed()

    # ── Lifecycle ────────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent):  # type: ignore[override]
        logger.info("MainWindow.closeEvent: shutting down")
        try:
            self._status_tab.shutdown()
        except Exception as e:
            logger.warning(f"shutdown error: {e}")
        try:
            self._log_tab.remove_handler()
        except Exception:
            pass
        super().closeEvent(event)
