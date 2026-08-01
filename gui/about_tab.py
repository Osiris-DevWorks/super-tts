"""About tab — version + project info, palette-aware."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget

from gui import theme as gui_theme


def _read_version() -> str:
    """Read VERSION.TXT, frozen-aware."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    p = base / "VERSION.TXT"
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


class AboutTab(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)

        self._title = QLabel("Super TTS")
        self._title.setStyleSheet(self._title_qss())
        title_font = self._title.font()
        title_font.setPointSize(28)
        title_font.setBold(True)
        self._title.setFont(title_font)
        layout.addWidget(self._title)

        self._tagline = QLabel("Ultra-fast Supertonic-based Discord TTS bot")
        self._tagline.setStyleSheet(self._tagline_qss())
        tagline_font = self._tagline.font()
        tagline_font.setPointSize(11)
        self._tagline.setFont(tagline_font)
        layout.addWidget(self._tagline)

        layout.addSpacing(16)

        self._version_label = QLabel(f"Version {_read_version()}")
        self._version_label.setProperty("role", "secondary")
        layout.addWidget(self._version_label)

        self._publisher_label = QLabel("Osiris DevWorks, LLC")
        self._publisher_label.setProperty("role", "secondary")
        layout.addWidget(self._publisher_label)

        layout.addSpacing(20)

        body = QLabel(
            "This installer connects to a shared Railway PostgreSQL database. "
            "Each user runs the bot under their own Discord application token, "
            "configured in the Settings tab.\n\n"
            "Logs from the running bot are visible in the Logs tab. To stop "
            "the bot, click Disconnect on the Status tab or close this window."
        )
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(body)

        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def on_theme_changed(self):
        self._title.setStyleSheet(self._title_qss())
        self._tagline.setStyleSheet(self._tagline_qss())

    def _title_qss(self) -> str:
        return f"color: {gui_theme.get_title_color()};"

    def _tagline_qss(self) -> str:
        return f"color: {gui_theme.get_tagline_color()};"
