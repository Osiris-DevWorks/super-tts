"""Main window — QTabWidget hosting Status / Settings / Logs / About tabs."""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QCloseEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gui import theme as gui_theme
from gui.about_tab import AboutTab
from gui.footer import Footer
from gui.help_tab import HelpTab
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
        # Settings tab packs Token + DB URL + Owner ID + HF Token + TTS
        # Device + Theme plus inline help text — at <760px the Show
        # buttons and helper labels get scrunched. Lock the floor at 760
        # and open a hair taller so users land on a comfortable layout.
        self.setMinimumHeight(760)
        self.resize(900, 780)

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
        self._help_tab = HelpTab()
        self._about_tab = AboutTab()

        self._tabs.addTab(self._status_tab, "Status")
        self._tabs.addTab(self._settings_tab, "Settings")
        self._tabs.addTab(self._help_tab, "Help")
        self._tabs.addTab(self._about_tab, "About")

        self._settings_tab.theme_changed.connect(self._on_theme_changed)

        outer.addWidget(self._tabs, 1)

        # Branded footer (Osiris logo + Discord on the left, donation cluster
        # on the right). The Osiris logo's Eye of Horus glyph pulses while
        # the bot is connected — Status tab fires bot_ready / bot_idle for
        # the footer to listen on.
        self._footer = Footer()
        outer.addWidget(self._footer)
        self._status_tab.bot_ready.connect(self._footer.start_pulse)
        self._status_tab.bot_idle.connect(self._footer.stop_pulse)

        self.setCentralWidget(central)

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        # Title + tagline stack vertically on the left (smart-citizen style:
        # bold branded title, smaller letter-spaced tagline beneath).
        title_stack = QVBoxLayout()
        title_stack.setSpacing(0)
        title_stack.setContentsMargins(0, 0, 0, 0)

        self._title_label = QLabel("SUPER TTS")
        title_font = QFont(gui_theme.BRAND_FONT_FAMILY)
        title_font.setPointSize(22)
        self._title_label.setFont(title_font)
        self._title_label.setStyleSheet(f"color: {gui_theme.get_title_color()};")
        title_stack.addWidget(self._title_label)

        self._tagline_label = QLabel("YOUR VOICE ON DISCORD")
        self._tagline_label.setStyleSheet(self._tagline_qss())
        title_stack.addWidget(self._tagline_label)

        row.addLayout(title_stack)
        row.addStretch()

        # Logo in the top-right corner. Drawn inside a theme-colored
        # rounded border so it reads as a UI element rather than a stray
        # graphic. Border re-renders on theme swap (see _on_theme_changed).
        self._logo_label = self._build_logo()
        if self._logo_label is not None:
            row.addWidget(self._logo_label, 0, Qt.AlignmentFlag.AlignVCenter)

        return row

    def _build_logo(self) -> QLabel | None:
        """Load assets/super-tts.png, scale it for the header, wrap it in a
        rounded border. Returns None if the asset is missing — header just
        shows title + tagline in that case."""
        path = _resource_path("assets/super-tts.png")
        if not path.exists():
            return None
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return None
        # Logo target height. The header text side is ~36px; oversize the
        # logo so the framed mark anchors the top of the window.
        if pixmap.height() > 72:
            pixmap = pixmap.scaledToHeight(
                72, Qt.TransformationMode.SmoothTransformation
            )
        label = QLabel()
        label.setPixmap(pixmap)
        label.setStyleSheet(self._logo_qss())
        return label

    def _logo_qss(self) -> str:
        color = gui_theme.get_title_color()
        return (
            "QLabel {"
            f" border: 2px solid {color};"
            " border-radius: 8px;"
            " padding: 4px;"
            " background: transparent;"
            "}"
        )

    def _tagline_qss(self) -> str:
        return (
            "font-size: 11px; "
            "letter-spacing: 2px; "
            f"color: {gui_theme.get_tagline_color()};"
        )

    # ── Slots ────────────────────────────────────────────────────────────

    def _on_theme_changed(self, theme: str):
        app = QApplication.instance()
        if app is not None:
            gui_theme.apply_theme(app, theme)
        # Re-render any theme-dependent ad-hoc styles
        self._title_label.setStyleSheet(f"color: {gui_theme.get_title_color()};")
        self._tagline_label.setStyleSheet(self._tagline_qss())
        if self._logo_label is not None:
            self._logo_label.setStyleSheet(self._logo_qss())
        self._status_tab.on_theme_changed()
        self._about_tab.on_theme_changed()

    # ── Lifecycle ────────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent):  # type: ignore[override]
        logger.info("MainWindow.closeEvent: shutting down")
        # StatusTab.shutdown() also detaches the embedded LogView's logging
        # handler — no separate cleanup call needed since the merge.
        try:
            self._status_tab.shutdown()
        except Exception as e:
            logger.warning(f"shutdown error: {e}")
        super().closeEvent(event)
